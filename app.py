"""
MediGuide AI — Flask application.
Routes only; prompts, services, and file utils live in dedicated modules.
"""

import base64
import os
import traceback
from urllib.parse import quote

from flask import Flask, request, jsonify, render_template, redirect, session, url_for
from openai import AzureOpenAI

from config import Config
from prompts import get_system_prompt, DEFAULT_LANGUAGE
from services.translator import translate
from services.content_safety import analyze_safety
from services.cosmos_store import store_session_record, get_recent_sessions
from utils.files import get_file_extension, extract_pdf_text

# ---------------------------------------------------------------------------
# App and OpenAI client
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_FILE_SIZE_MB * 1024 * 1024
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-in-production")

client = AzureOpenAI(
    azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
    api_key=Config.AZURE_OPENAI_KEY,
    api_version=Config.AZURE_OPENAI_API_VERSION,
)
DEPLOYMENT = Config.AZURE_OPENAI_DEPLOYMENT

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

EASY_AUTH_HEADER = "X-MS-CLIENT-PRINCIPAL-NAME"


def is_authenticated():
    """True if user is logged in via Easy Auth (header) or guest session (local dev)."""
    if session.get("guest"):
        return True
    principal = request.headers.get(EASY_AUTH_HEADER)
    return bool(principal and str(principal).strip())


@app.route("/")
def index():
    """Landing / login: if authenticated redirect to dashboard, else show sign-in page."""
    if is_authenticated():
        return redirect("/chat")
    return render_template("landing.html")


@app.route("/logout")
def logout():
    """Clear guest session and redirect to landing (for Easy Auth, use /.auth/logout in the browser)."""
    session.pop("guest", None)
    return redirect("/")


@app.route("/chat")
def chat_page():
    """Serve the main chat dashboard (single-page app). Redirect to landing if not authenticated."""
    if not is_authenticated():
        return redirect("/")
    principal = request.headers.get(EASY_AUTH_HEADER)
    is_guest = session.get("guest", False)
    if is_guest:
        user_display_name = "Guest"
        logout_url = url_for("logout")
    else:
        user_display_name = (principal or "").strip() or "User"
        base = request.url_root.rstrip("/")
        logout_url = f"{base}/.auth/logout?post_logout_redirect_uri={quote(base + '/')}"
    return render_template(
        "index.html",
        user_display_name=user_display_name,
        is_guest=is_guest,
        logout_url=logout_url,
    )


@app.route("/guest")
def continue_as_guest():
    """Local dev: set guest session and redirect to chat (no Easy Auth)."""
    session["guest"] = True
    return redirect("/chat")


@app.route("/chat", methods=["POST"])
def chat():
    """Feature 1 & 5: Symptom checker + triage agent (multi-turn)."""
    try:
        data = request.get_json() or {}
        user_message = (data.get("message") or "").strip()
        if not user_message:
            return jsonify({"error": "Please enter a message."}), 400

        language = (data.get("language") or DEFAULT_LANGUAGE).lower()
        history = data.get("history") or []
        user_id = (data.get("userId") or "").strip()

        system_prompt = get_system_prompt("symptom-checker", language)
        messages = [{"role": "system", "content": system_prompt}]
        for item in history:
            role = item.get("role")
            content = (item.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
        )
        raw_reply = response.choices[0].message.content
        safety = analyze_safety(raw_reply)
        reply = translate(raw_reply, language)

        store_session_record(
            user_id,
            "symptom-checker",
            {
                "language": language,
                "history": history,
                "latestUserMessage": user_message,
                "assistantReply": raw_reply,
                "safety": safety,
            },
        )

        return jsonify({
            "reply": reply,
            "meta": {
                "feature": "symptom-checker",
                "model": DEPLOYMENT,
                "language": language,
                "safety": safety,
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/analyze-report", methods=["POST"])
def analyze_report():
    """Feature 2: Medical report explainer (PDF upload)."""
    try:
        language = (request.form.get("language") or DEFAULT_LANGUAGE).lower()
        user_id = (request.form.get("userId") or "").strip()

        if "file" not in request.files:
            return jsonify({"error": "No file uploaded."}), 400
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "No file selected."}), 400

        ext = get_file_extension(file.filename)
        if ext not in Config.ALLOWED_PDF_EXTENSIONS:
            return jsonify({"error": "Only PDF files are supported."}), 400

        file_bytes = file.read()
        pdf_text = extract_pdf_text(file_bytes)
        if not pdf_text.strip():
            return jsonify({
                "error": "Could not extract text from the PDF. It may be scanned/image-based.",
            }), 400

        user_message = (
            "Please explain this medical report in plain language. "
            "For each value, say if it is normal or abnormal and why it matters.\n\n"
            f"{pdf_text[:8000]}"
        )
        system_prompt = get_system_prompt("report-explainer", language)

        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        raw_reply = response.choices[0].message.content
        safety = analyze_safety(raw_reply)
        reply = translate(raw_reply, language)

        store_session_record(
            user_id,
            "report-explainer",
            {
                "language": language,
                "assistantReply": raw_reply,
                "safety": safety,
            },
        )

        return jsonify({
            "reply": reply,
            "meta": {
                "feature": "report-explainer",
                "model": DEPLOYMENT,
                "language": language,
                "safety": safety,
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/medication-info", methods=["POST"])
def medication_info():
    """Feature 6: Medication safety checker."""
    try:
        data = request.get_json() or {}
        raw_value = (data.get("medication") or "").strip()
        if not raw_value:
            return jsonify({"error": "Please enter one or more medication names."}), 400

        language = (data.get("language") or DEFAULT_LANGUAGE).lower()
        user_id = (data.get("userId") or "").strip()

        user_message = (
            "The user provided the following list of medications (one or more, possibly separated by commas or new lines):\n"
            f"{raw_value}\n\n"
            "Please:\n"
            "1) Briefly explain what each medication is used for.\n"
            "2) List common and serious side effects.\n"
            "3) Check for important drug–drug interactions between medications in this list, "
            "classifying each pair as Safe, Use with caution, or Dangerous.\n"
            "4) Explain your reasoning in simple language.\n"
            "5) End with a clear safety reminder to always speak to a doctor or pharmacist before changing medications."
        )
        system_prompt = get_system_prompt("medication-safety", language)

        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        raw_reply = response.choices[0].message.content
        safety = analyze_safety(raw_reply)
        reply = translate(raw_reply, language)

        store_session_record(
            user_id,
            "medication-safety",
            {
                "language": language,
                "medicationInput": raw_value,
                "assistantReply": raw_reply,
                "safety": safety,
            },
        )

        return jsonify({
            "reply": reply,
            "meta": {
                "feature": "medication-safety",
                "model": DEPLOYMENT,
                "language": language,
                "safety": safety,
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/analyze-image", methods=["POST"])
def analyze_image():
    """Feature 4: Medical image description (GPT-4o vision)."""
    try:
        language = (request.form.get("language") or DEFAULT_LANGUAGE).lower()
        user_id = (request.form.get("userId") or "").strip()

        if "file" not in request.files:
            return jsonify({"error": "No image uploaded."}), 400
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "No file selected."}), 400

        ext = get_file_extension(file.filename)
        if ext not in Config.ALLOWED_IMAGE_EXTENSIONS:
            return jsonify({"error": "Supported formats: PNG, JPG, JPEG, WEBP, GIF."}), 400

        file_bytes = file.read()
        base64_image = base64.b64encode(file_bytes).decode("utf-8")
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        mime_type = mime_map.get(ext, "image/png")
        system_prompt = get_system_prompt("image-analysis", language)

        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Please describe this medical image in plain, simple language. "
                                "Do NOT diagnose. Always recommend that a qualified radiologist or physician reviews the scan."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}},
                    ],
                },
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        raw_reply = response.choices[0].message.content
        safety = analyze_safety(raw_reply)
        reply = translate(raw_reply, language)

        store_session_record(
            user_id,
            "image-analysis",
            {
                "language": language,
                "assistantReply": raw_reply,
                "safety": safety,
            },
        )

        return jsonify({
            "reply": reply,
            "meta": {
                "feature": "image-analysis",
                "model": DEPLOYMENT,
                "language": language,
                "safety": safety,
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/report-answer", methods=["POST"])
def report_answer():
    """Feature 8: Report a problematic AI answer (stored in Cosmos)."""
    try:
        data = request.get_json() or {}
        user_id = (data.get("userId") or "").strip()
        feature = (data.get("feature") or "").strip()
        original_question = (data.get("question") or "").strip()
        ai_reply = (data.get("reply") or "").strip()
        language = (data.get("language") or DEFAULT_LANGUAGE).lower()
        safety = data.get("safety") or {}

        if not ai_reply:
            return jsonify({"error": "Missing AI reply to report."}), 400

        store_session_record(
            user_id or "anonymous",
            "reported-answer",
            {
                "feature": feature,
                "language": language,
                "question": original_question,
                "reply": ai_reply,
                "safety": safety,
            },
        )
        return jsonify({"status": "ok"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/history", methods=["GET"])
def history():
    """Return a lightweight recent-history list for the sidebar."""
    try:
        user_id = (request.args.get("userId") or "").strip()
        if not user_id:
            return jsonify({"items": []})

        raw_items = get_recent_sessions(user_id=user_id, limit=24)
        items = []
        seen_features = set()
        for item in raw_items:
            feature = item.get("feature", "")
            payload = item.get("payload") or {}
            created_at = item.get("createdAt")
            title = ""
            messages = []
            if feature == "symptom-checker":
                msg = (payload.get("latestUserMessage") or "").strip()
                title = msg or "Symptom check"
                history = payload.get("history") or []
                for h in history:
                    role = h.get("role")
                    content = (h.get("content") or "").strip()
                    if role in ("user", "assistant") and content:
                        messages.append({"role": role, "content": content, "meta": None})
                latest_user = (payload.get("latestUserMessage") or "").strip()
                assistant_reply = (payload.get("assistantReply") or "").strip()
                if latest_user:
                    messages.append({"role": "user", "content": latest_user, "meta": None})
                if assistant_reply:
                    messages.append({"role": "assistant", "content": assistant_reply, "meta": {"feature": "symptom-checker"}})
            elif feature == "report-explainer":
                title = "Blood test / report"
                assistant_reply = (payload.get("assistantReply") or "").strip()
                if assistant_reply:
                    messages.append({"role": "assistant", "content": assistant_reply, "meta": {"feature": "report-explainer"}})
            elif feature == "medication-safety":
                meds = (payload.get("medicationInput") or "").strip()
                title = f"Medication safety — {meds}" if meds else "Medication safety"
                if meds:
                    messages.append({"role": "user", "content": meds, "meta": None})
                assistant_reply = (payload.get("assistantReply") or "").strip()
                if assistant_reply:
                    messages.append({"role": "assistant", "content": assistant_reply, "meta": {"feature": "medication-safety"}})
            elif feature == "image-analysis":
                title = "X-ray / imaging review"
                assistant_reply = (payload.get("assistantReply") or "").strip()
                if assistant_reply:
                    messages.append({"role": "assistant", "content": assistant_reply, "meta": {"feature": "image-analysis"}})
            else:
                title = feature or "Conversation"

            if len(title) > 42:
                title = title[:39].rstrip() + "..."

            # One recent conversation per feature for this user
            if feature in seen_features:
                continue
            seen_features.add(feature)

            items.append(
                {
                    "id": item.get("id"),
                    "feature": feature,
                    "title": title,
                    "createdAt": created_at,
                    "messages": messages,
                }
            )
        return jsonify({"items": items})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"items": [], "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
