"""
MediGuide AI — Flask application.
Routes only; prompts, services, and file utils live in dedicated modules.
"""

import base64
import os
import traceback
from urllib.parse import quote

from flask import Flask, request, jsonify, render_template, redirect, session, url_for, Response
from openai import AzureOpenAI

from config import Config
from prompts import get_system_prompt, DEFAULT_LANGUAGE
from services.translator import translate
from services.content_safety import analyze_safety
from services.cosmos_store import (
    store_session_record,
    get_recent_sessions,
    get_medication_history,
    get_timeline_interactions,
    get_user_preference,
    set_user_preference,
)
from utils.files import get_file_extension, extract_pdf_text
from utils.pdf_generator import build_er_prep_sheet, build_health_timeline_pdf

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
# Helpers
# ---------------------------------------------------------------------------


def _parse_and_strip_referral_specialty(reply: str):
    """Extract REFERRAL_SPECIALTY from reply and return (cleaned_reply, taxonomy or '')."""
    import re
    if not reply:
        return reply, ""
    m = re.search(r"\n?\s*REFERRAL_SPECIALTY:\s*(.+?)\s*$", reply, re.IGNORECASE)
    if not m:
        return reply, ""
    taxonomy = m.group(1).strip()
    cleaned = re.sub(r"\n?\s*REFERRAL_SPECIALTY:\s*.+?\s*$", "", reply, flags=re.IGNORECASE).rstrip()
    return cleaned, taxonomy


def _parse_urgency_from_reply(reply: str) -> str:
    """Extract urgency level from symptom checker reply. Returns HIGH, MEDIUM, or LOW."""
    r = reply or ""
    if "🔴" in r or "urgency" in r.lower() and "high" in r.lower():
        return "HIGH"
    if "🟡" in r or "medium" in r.lower():
        return "MEDIUM"
    return "LOW"


def _generate_doctor_questions(symptoms: str, reply: str, language: str) -> list:
    """Generate 5 doctor questions using Azure OpenAI based on symptoms and AI reply."""
    try:
        prompt = (
            "Based on the following patient symptoms and triage response, generate exactly 5 short, "
            "specific questions the patient should ask their doctor in the emergency room. "
            "Each question should be one sentence. Output only the 5 questions, one per line, numbered 1-5. "
            "Use simple language.\n\n"
            f"Symptoms: {symptoms[:1500]}\n\n"
            f"Triage summary: {reply[:800]}"
        )
        resp = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
        )
        text = (resp.choices[0].message.content or "").strip()
        questions = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Remove leading "1." etc
            for i in range(1, 10):
                if line.startswith(f"{i}.") or line.startswith(f"{i})"):
                    line = line[2:].strip()
                    break
            if line:
                questions.append(line)
        return questions[:5]
    except Exception:
        return [
            "What could be causing these symptoms?",
            "What tests do you recommend?",
            "Are there any immediate treatments I should know about?",
            "When should I follow up?",
            "Is there anything I should avoid doing?",
        ]


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


@app.route("/api/location", methods=["GET"])
def get_location():
    """Return approximate user location (city, region, country) from IP for area-based recommendations."""
    try:
        import httpx
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").strip().split(",")[0].strip() or None
        url = "http://ip-api.com/json/"
        if client_ip and client_ip != "127.0.0.1":
            url = f"http://ip-api.com/json/{client_ip}"
        with httpx.Client(timeout=3.0) as http:
            r = http.get(url, params={"fields": "city,regionName,country"})
        if r.status_code != 200:
            return jsonify({"location": None, "city": None, "region": None, "country": None})
        data = r.json()
        city = (data.get("city") or "").strip()
        region = (data.get("regionName") or "").strip()
        country = (data.get("country") or "").strip()
        parts = [p for p in [city, region, country] if p]
        location_str = ", ".join(parts) if parts else None
        return jsonify({"location": location_str, "city": city or None, "region": region or None, "country": country or None})
    except Exception:
        return jsonify({"location": None, "city": None, "region": None, "country": None})


# NPPES taxonomy descriptions for doctor search (US only)
NPPES_TAXONOMIES = [
    "Cardiology", "Internal Medicine", "Family Medicine", "Pediatrics",
    "Neurology", "Orthopaedic Surgery", "General Practice", "Emergency Medicine",
    "Obstetrics & Gynecology", "Dermatology", "Psychiatry", "Gastroenterology",
    "Pulmonology", "Endocrinology", "Nephrology", "Rheumatology", "Urology",
]


@app.route("/api/doctors", methods=["GET"])
def get_doctors():
    """Search US healthcare providers via NPPES (free, no API key). Requires city and state."""
    try:
        import httpx
        city = (request.args.get("city") or "").strip()
        state = (request.args.get("state") or "").strip()
        taxonomy = (request.args.get("taxonomy") or request.args.get("taxonomy_description") or "Internal Medicine").strip()
        limit = min(int(request.args.get("limit", 10)), 50)
        if not city or not state:
            return jsonify({"error": "city and state are required", "providers": []}), 400
        with httpx.Client(timeout=8.0) as http:
            r = http.get(
                "https://npiregistry.cms.hhs.gov/api/",
                params={
                    "version": "2.1",
                    "city": city,
                    "state": state,
                    "taxonomy_description": taxonomy,
                    "limit": limit,
                },
            )
        if r.status_code != 200:
            return jsonify({"error": "Provider lookup failed", "providers": []}), 502
        data = r.json()
        results = data.get("result_count") or 0
        entries = data.get("results") or []
        providers = []
        for e in entries:
            basic = e.get("basic") or {}
            addr_list = e.get("addresses") or []
            addr = next((a for a in addr_list if (a.get("address_purpose") or "").lower() == "location"), addr_list[0] if addr_list else {})
            taxonomies = e.get("taxonomies") or []
            tax = next((t for t in taxonomies if t.get("primary")), taxonomies[0] if taxonomies else {})
            providers.append({
                "npi": e.get("number"),
                "name": basic.get("first_name", "") + " " + basic.get("last_name", "").strip() or (basic.get("organization_name") or "").strip(),
                "credential": basic.get("credential"),
                "taxonomy": tax.get("desc") or taxonomy,
                "address": ", ".join(filter(None, [
                    addr.get("address_1"),
                    addr.get("address_2"),
                    (addr.get("city") or "") + ", " + (addr.get("state") or "") + " " + (addr.get("postal_code") or ""),
                ])).strip(),
            })
        return jsonify({"providers": providers, "result_count": results})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e), "providers": []}), 500


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
        # Use relative path so Azure may redirect straight to app and skip the "You have been signed out" page
        logout_url = f"{base}/.auth/logout?post_logout_redirect_uri={quote('/')}"
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
        literacy_mode = (data.get("literacyMode") or get_user_preference(user_id, "literacyMode") or "standard").lower()
        user_location = (data.get("location") or data.get("userLocation") or "").strip() or None
        user_city = (data.get("city") or "").strip() or None
        user_state = (data.get("state") or data.get("region") or "").strip() or None
        user_country = (data.get("country") or "").strip() or None

        if not user_location or not user_city or not user_state:
            try:
                import httpx
                client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").strip().split(",")[0].strip() or None
                url = "http://ip-api.com/json/" if (not client_ip or client_ip == "127.0.0.1") else f"http://ip-api.com/json/{client_ip}"
                with httpx.Client(timeout=2.0) as http:
                    r = http.get(url, params={"fields": "city,regionName,country"})
                if r.status_code == 200:
                    loc_data = r.json()
                    c = (loc_data.get("city") or "").strip()
                    s = (loc_data.get("regionName") or "").strip()
                    co = (loc_data.get("country") or "").strip()
                    if c or s or co:
                        user_city = user_city or c
                        user_state = user_state or s
                        user_country = user_country or co
                        user_location = user_location or ", ".join(filter(None, [c, s, co]))
            except Exception:
                pass

        system_prompt = get_system_prompt("symptom-checker", language, literacy_mode, user_location)
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
        raw_reply, referral_specialty = _parse_and_strip_referral_specialty(raw_reply)
        safety = analyze_safety(raw_reply)
        reply = translate(raw_reply, language)

        providers = []
        if referral_specialty and user_city and user_state:
            us_like = (user_country or "").lower() in ("us", "usa", "united states", "united states of america")
            if us_like:
                try:
                    import httpx
                    with httpx.Client(timeout=8.0) as http:
                        r = http.get(
                            "https://npiregistry.cms.hhs.gov/api/",
                            params={
                                "version": "2.1",
                                "city": user_city,
                                "state": user_state,
                                "taxonomy_description": referral_specialty,
                                "limit": 10,
                            },
                        )
                    if r.status_code == 200:
                        data = r.json()
                        for e in (data.get("results") or [])[:10]:
                            basic = e.get("basic") or {}
                            addr_list = e.get("addresses") or []
                            addr = next((a for a in addr_list if (a.get("address_purpose") or "").lower() == "location"), addr_list[0] if addr_list else {})
                            taxonomies = e.get("taxonomies") or []
                            tax = next((t for t in taxonomies if t.get("primary")), taxonomies[0] if taxonomies else {})
                            name = (basic.get("first_name") or "") + " " + (basic.get("last_name") or "").strip()
                            if not name.strip():
                                name = (basic.get("organization_name") or "").strip()
                            providers.append({
                                "npi": e.get("number"),
                                "name": name.strip(),
                                "credential": basic.get("credential"),
                                "taxonomy": tax.get("desc") or referral_specialty,
                                "address": ", ".join(filter(None, [
                                    addr.get("address_1"),
                                    addr.get("address_2"),
                                    (addr.get("city") or "") + ", " + (addr.get("state") or "") + " " + (addr.get("postal_code") or ""),
                                ])).strip(),
                            })
                except Exception:
                    pass

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

        urgency = _parse_urgency_from_reply(raw_reply)
        meta = {
            "feature": "symptom-checker",
            "model": DEPLOYMENT,
            "language": language,
            "safety": safety,
            "urgency": urgency,
            "literacyMode": literacy_mode,
        }
        if providers:
            meta["doctors"] = providers
            meta["referralSpecialty"] = referral_specialty
        if urgency == "HIGH":
            symptoms_text = "\n".join(
                (h.get("content") or "").strip()
                for h in history
                if h.get("role") == "user"
            ) + "\n" + user_message
            symptom_timeline = "As reported in this session (most recent first)."
            doctor_questions = _generate_doctor_questions(symptoms_text, raw_reply, language)
            meta["erPdfAvailable"] = True
            meta["erPdfParams"] = {
                "symptoms": symptoms_text.strip(),
                "symptomTimeline": symptom_timeline,
                "urgency": urgency,
                "doctorQuestions": doctor_questions,
            }

        return jsonify({"reply": reply, "meta": meta})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/analyze-report", methods=["POST"])
def analyze_report():
    """Feature 2: Medical report explainer (PDF upload)."""
    try:
        language = (request.form.get("language") or DEFAULT_LANGUAGE).lower()
        user_id = (request.form.get("userId") or "").strip()
        literacy_mode = (request.form.get("literacyMode") or get_user_preference(user_id, "literacyMode") or "standard").lower()
        user_location = (request.form.get("location") or request.form.get("userLocation") or "").strip() or None

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
        system_prompt = get_system_prompt("report-explainer", language, literacy_mode, user_location)

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
                "literacyMode": literacy_mode,
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
        literacy_mode = (data.get("literacyMode") or get_user_preference(user_id, "literacyMode") or "standard").lower()
        user_location = (data.get("location") or data.get("userLocation") or "").strip() or None

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
        system_prompt = get_system_prompt("medication-safety", language, literacy_mode, user_location)

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
                "literacyMode": literacy_mode,
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
        literacy_mode = (request.form.get("literacyMode") or get_user_preference(user_id, "literacyMode") or "standard").lower()
        user_location = (request.form.get("location") or request.form.get("userLocation") or "").strip() or None

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
        system_prompt = get_system_prompt("image-analysis", language, literacy_mode, user_location)

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
                "literacyMode": literacy_mode,
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/save-preference", methods=["POST"])
def save_preference():
    """Save user preference (e.g. literacy mode) to Cosmos DB."""
    try:
        data = request.get_json() or {}
        user_id = (data.get("userId") or "").strip()
        key = (data.get("key") or "").strip()
        value = data.get("value")
        if not user_id or not key:
            return jsonify({"error": "Missing userId or key."}), 400
        set_user_preference(user_id, key, value)
        return jsonify({"status": "ok"})
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


@app.route("/generate-er-pdf", methods=["POST"])
def generate_er_pdf():
    """Generate and return a downloadable ER Prep Sheet PDF."""
    try:
        data = request.get_json() or {}
        user_id = (data.get("patient_id") or data.get("userId") or "").strip()
        patient_name = (data.get("patient_name") or "").strip() or "Patient"
        symptoms = (data.get("symptoms") or "").strip() or "Not specified"
        symptom_timeline = (data.get("symptom_timeline") or data.get("symptomTimeline") or "").strip() or "As reported in this session."
        urgency = (data.get("urgency") or "HIGH").upper()
        doctor_questions = data.get("doctor_questions") or data.get("doctorQuestions") or []

        medications = get_medication_history(user_id, limit=10) if user_id else []
        raw_items = get_timeline_interactions(user_id, limit=20) if user_id else []
        past_interactions = []
        for item in raw_items:
            feat = item.get("feature", "")
            payload = item.get("payload") or {}
            if feat == "symptom-checker":
                summary = (payload.get("latestUserMessage") or "")[:80] or "Symptom check"
            elif feat == "medication-safety":
                summary = (payload.get("medicationInput") or "")[:80] or "Medication check"
            elif feat == "report-explainer":
                summary = "Blood test / report"
            elif feat == "image-analysis":
                summary = "Image analysis"
            else:
                summary = feat or "Interaction"
            past_interactions.append({"feature": feat, "summary": summary})

        if not doctor_questions:
            doctor_questions = _generate_doctor_questions(symptoms, "", "en")

        pdf_bytes = build_er_prep_sheet(
            patient_name=patient_name,
            symptoms=symptoms,
            symptom_timeline=symptom_timeline,
            urgency=urgency,
            medications=medications,
            past_interactions=past_interactions[:3],
            doctor_questions=doctor_questions,
        )

        from datetime import datetime
        filename = f"MediGuide_ER_Prep_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.pdf"
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def _generate_health_summary(interactions: list, language: str) -> str:
    """Generate a 3-sentence AI health summary from interactions."""
    if not interactions:
        return "No recent health interactions to summarize."
    try:
        lines = []
        for i, item in enumerate(interactions[:15], 1):
            feat = item.get("feature", "")
            payload = item.get("payload") or {}
            created = item.get("createdAt", "")[:10]
            if feat == "symptom-checker":
                msg = (payload.get("latestUserMessage") or "")[:120]
                lines.append(f"{created} Symptom: {msg}")
            elif feat == "medication-safety":
                med = (payload.get("medicationInput") or "")[:80]
                lines.append(f"{created} Medication: {med}")
            elif feat == "report-explainer":
                lines.append(f"{created} Blood test/report")
            elif feat == "image-analysis":
                lines.append(f"{created} Image analysis")
        text = "\n".join(lines)
        prompt = (
            "Based on these health interactions, write a 3-sentence health summary for the patient "
            "highlighting patterns, concerns, and any positive notes. Keep it simple and reassuring. "
            "Do not diagnose. Output only the 3 sentences, no numbering.\n\n" + text
        )
        resp = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
        )
        return (resp.choices[0].message.content or "").strip() or "No summary available."
    except Exception:
        return "Unable to generate summary at this time."


def _timeline_entry_from_item(item: dict) -> dict:
    """Convert Cosmos item to timeline entry format."""
    feat = item.get("feature", "")
    payload = item.get("payload") or {}
    created = item.get("createdAt", "")
    # Parse urgency from reply if symptom-checker or image-analysis
    urgency = "LOW"
    reply = (payload.get("assistantReply") or "").lower()
    if "🔴" in (payload.get("assistantReply") or ""):
        urgency = "HIGH"
    elif "🟡" in (payload.get("assistantReply") or ""):
        urgency = "MEDIUM"
    else:
        if "high" in reply and ("urgency" in reply or "urgent" in reply):
            urgency = "HIGH"
        elif "medium" in reply:
            urgency = "MEDIUM"
    summary = ""
    if feat == "symptom-checker":
        summary = (payload.get("latestUserMessage") or "")[:100] or "Symptom check"
    elif feat == "medication-safety":
        summary = (payload.get("medicationInput") or "")[:80] or "Medication check"
    elif feat == "report-explainer":
        summary = "Blood test / report"
    elif feat == "image-analysis":
        summary = "X-ray / imaging"
    else:
        summary = feat or "Interaction"
    return {
        "id": item.get("id"),
        "date": created,
        "feature": feat,
        "featureLabel": "Symptom Check" if feat == "symptom-checker" else "Medication Check" if feat == "medication-safety" else "Blood Test Analysis" if feat == "report-explainer" else "Image Analysis",
        "summary": summary,
        "urgency": urgency,
        "detail": payload.get("assistantReply") or payload.get("latestUserMessage") or "",
    }


@app.route("/timeline", methods=["GET"])
def timeline():
    """Return health timeline for the user with optional date filter and AI summary."""
    try:
        user_id = (request.args.get("userId") or "").strip()
        if not user_id:
            return jsonify({"items": [], "summary": ""})

        range_val = request.args.get("range", "30")
        since_days = None
        if range_val == "7":
            since_days = 7
        elif range_val == "30":
            since_days = 30
        elif range_val == "90":
            since_days = 90
        # "all" = None

        items = get_timeline_interactions(user_id, limit=100, since_days=since_days)
        entries = [_timeline_entry_from_item(it) for it in items]
        summary = _generate_health_summary(items, "en")
        return jsonify({"items": entries, "summary": summary})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"items": [], "summary": "", "error": str(e)}), 500


@app.route("/download-health-report", methods=["POST"])
def download_health_report():
    """Generate and return a PDF of the health timeline."""
    try:
        data = request.get_json() or {}
        user_id = (data.get("userId") or "").strip()
        patient_name = (data.get("patientName") or "").strip() or "Patient"
        date_range = (data.get("dateRange") or "").strip() or "Last 30 days"
        ai_summary = (data.get("summary") or "").strip() or "No summary available."
        entries = data.get("entries") or []

        pdf_bytes = build_health_timeline_pdf(
            patient_name=patient_name,
            date_range=date_range,
            ai_summary=ai_summary,
            entries=entries,
        )
        from datetime import datetime
        filename = f"MediGuide_Health_Report_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.pdf"
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
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
