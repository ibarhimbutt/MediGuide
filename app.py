import os
import base64
import traceback

from flask import Flask, request, jsonify, render_template
from openai import AzureOpenAI
from PyPDF2 import PdfReader
import io

from config import Config

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_FILE_SIZE_MB * 1024 * 1024

client = AzureOpenAI(
    azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
    api_key=Config.AZURE_OPENAI_KEY,
    api_version=Config.AZURE_OPENAI_API_VERSION,
)

DEPLOYMENT = Config.AZURE_OPENAI_DEPLOYMENT

# ---------------------------------------------------------------------------
# System prompts for each feature
# ---------------------------------------------------------------------------

SYMPTOM_CHECKER_PROMPT = """You are MediGuide AI, a compassionate and knowledgeable medical information assistant and triage agent.

Your goals:
- Understand the user's symptoms in everyday language.
- Ask 1–2 focused follow-up questions when needed.
- Suggest possible explanations and an urgency level.
- Recommend which type of doctor or specialist to see if appropriate.

When a user describes their symptoms:
1. Start with a short, empathetic acknowledgement.
2. List 2–4 possible explanations or conditions that match their symptoms, from most common to less common.
3. For each possibility, briefly explain why it might match.
4. Assign an urgency level: 🟢 Low (self‑care likely sufficient), 🟡 Medium (see a doctor within a few days), 🔴 High (seek urgent or emergency care).
5. If more information is needed, ask 1–2 clear follow‑up questions before giving a strong recommendation.
6. When you have enough information, give a final triage recommendation: what type of doctor to see (GP, cardiologist, neurologist, etc.) and how soon.
7. Always suggest simple self‑care steps that are generally safe (rest, hydration, etc.) when appropriate.

Format your response with clear headings, bullet points, and short paragraphs for readability.

IMPORTANT DISCLAIMER: Always remind the user that you provide general health information only and are NOT a substitute for professional medical advice, diagnosis, or treatment."""

REPORT_EXPLAINER_PROMPT = """You are MediGuide AI, a medical report explainer that makes complex medical reports easy to understand.

When given the text content of a medical report (blood test, lab results, etc.):
1. Identify the type of report.
2. Go through each value or finding in the report.
3. For each value, explain:
   - What it measures (in simple terms)
   - Whether the result is normal, high, or low
   - What it might mean if abnormal
4. Provide a plain‑language summary at the end highlighting:
   - ✅ Values that look normal
   - ⚠️ Values that need attention
   - Key takeaways and questions to ask a doctor.

Use simple, everyday language. Avoid medical jargon where possible — when you must use a medical term, define it immediately.

IMPORTANT DISCLAIMER: Always remind the user that this is an educational explanation only and they should discuss their results with their doctor."""

MEDICATION_INFO_PROMPT = """You are MediGuide AI, a medication safety and interaction assistant.

When a user provides one or more medication names:
1. Recognise generic and common brand names.
2. For each medication, explain in simple language:
   - What it is used for.
   - Common side effects.
   - Rare but serious side effects that require urgent care.
3. Check for important drug–drug interactions between the medications in the list:
   - For each pair, classify the combination as: Safe, Use with caution, or Dangerous.
   - Briefly explain why, in plain language.
4. Mention important warnings (pregnancy, kidney or liver problems, alcohol, driving, etc.) when relevant.
5. Provide all information in a structured, easy‑to‑scan format.

Format with clear sections and bullet points for easy reading.

IMPORTANT DISCLAIMER: This is general medication information only. Never start, stop, or change medications without speaking to a doctor or pharmacist who knows the patient’s full medical history."""

IMAGE_ANALYSIS_PROMPT = """You are MediGuide AI, a medical image description assistant.

When shown a medical image (X‑ray, MRI, CT scan, or other medical imagery):
1. Describe what type of image it appears to be.
2. Describe the visible anatomical structures in plain language.
3. Note any visible areas that appear unusual — areas of unusual density, asymmetry, or irregularity.
4. Explain what these observations might generally indicate (without diagnosing).
5. Clearly state what a professional would typically look for in this type of image.

Use simple, descriptive language. You are describing, NOT diagnosing.

IMPORTANT DISCLAIMER: Always state clearly that this is NOT a medical diagnosis. AI image analysis is for educational and informational purposes only. The user MUST consult a qualified radiologist or physician for professional interpretation of any medical images."""

LANGUAGE_INSTRUCTIONS = {
    "en": "Respond in clear, simple English that a non‑medical person can understand.",
    "ur": "Respond in clear, simple Urdu that is easy for patients to understand.",
    "ar": "Respond in clear, simple Modern Standard Arabic that is easy for patients to understand.",
    "hi": "Respond in clear, simple Hindi that is easy for patients to understand.",
}

DEFAULT_LANGUAGE = "en"


def _get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def _extract_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    return "\n".join(text_parts)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """Feature 1 & 5: Symptom Checker + Triage Agent (multi‑turn)"""
    try:
        data = request.get_json() or {}
        user_message = (data.get("message") or "").strip()
        if not user_message:
            return jsonify({"error": "Please enter a message."}), 400

        language = (data.get("language") or DEFAULT_LANGUAGE).lower()
        history = data.get("history") or []

        system_prompt = SYMPTOM_CHECKER_PROMPT + "\n\n" + LANGUAGE_INSTRUCTIONS.get(
            language, LANGUAGE_INSTRUCTIONS[DEFAULT_LANGUAGE]
        )

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
        reply = response.choices[0].message.content
        return jsonify(
            {
                "reply": reply,
                "meta": {
                    "feature": "symptom-checker",
                    "model": DEPLOYMENT,
                    "language": language,
                },
            }
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500


@app.route("/analyze-report", methods=["POST"])
def analyze_report():
    """Feature 2: Medical Report Explainer (PDF upload)"""
    try:
        language = (request.form.get("language") or DEFAULT_LANGUAGE).lower()

        if "file" not in request.files:
            return jsonify({"error": "No file uploaded."}), 400

        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "No file selected."}), 400

        ext = _get_file_extension(file.filename)
        if ext not in Config.ALLOWED_PDF_EXTENSIONS:
            return jsonify({"error": "Only PDF files are supported."}), 400

        file_bytes = file.read()
        pdf_text = _extract_pdf_text(file_bytes)

        if not pdf_text.strip():
            return jsonify({"error": "Could not extract text from the PDF. It may be scanned/image-based."}), 400

        user_message = (
            "Please explain this medical report in plain language. "
            "For each value, say if it is normal or abnormal and why it matters.\n\n"
            f"{pdf_text[:8000]}"
        )

        system_prompt = REPORT_EXPLAINER_PROMPT + "\n\n" + LANGUAGE_INSTRUCTIONS.get(
            language, LANGUAGE_INSTRUCTIONS[DEFAULT_LANGUAGE]
        )

        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        reply = response.choices[0].message.content
        return jsonify(
            {
                "reply": reply,
                "meta": {
                    "feature": "report-explainer",
                    "model": DEPLOYMENT,
                    "language": language,
                },
            }
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500


@app.route("/medication-info", methods=["POST"])
def medication_info():
    """Feature 6: Medication Safety Checker"""
    try:
        data = request.get_json() or {}
        raw_value = (data.get("medication") or "").strip()
        if not raw_value:
            return jsonify({"error": "Please enter one or more medication names."}), 400

        language = (data.get("language") or DEFAULT_LANGUAGE).lower()

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

        system_prompt = MEDICATION_INFO_PROMPT + "\n\n" + LANGUAGE_INSTRUCTIONS.get(
            language, LANGUAGE_INSTRUCTIONS[DEFAULT_LANGUAGE]
        )

        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        reply = response.choices[0].message.content
        return jsonify(
            {
                "reply": reply,
                "meta": {
                    "feature": "medication-safety",
                    "model": DEPLOYMENT,
                    "language": language,
                },
            }
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500


@app.route("/analyze-image", methods=["POST"])
def analyze_image():
    """Feature 4: Medical Image Description Assistant (GPT-4o vision)"""
    try:
        language = (request.form.get("language") or DEFAULT_LANGUAGE).lower()

        if "file" not in request.files:
            return jsonify({"error": "No image uploaded."}), 400

        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "No file selected."}), 400

        ext = _get_file_extension(file.filename)
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

        system_prompt = IMAGE_ANALYSIS_PROMPT + "\n\n" + LANGUAGE_INSTRUCTIONS.get(
            language, LANGUAGE_INSTRUCTIONS[DEFAULT_LANGUAGE]
        )

        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please describe this medical image in plain, simple language. "
                            "Do NOT diagnose. Always recommend that a qualified radiologist or physician reviews the scan.",
                        },
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}},
                    ],
                },
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        reply = response.choices[0].message.content
        return jsonify(
            {
                "reply": reply,
                "meta": {
                    "feature": "image-analysis",
                    "model": DEPLOYMENT,
                    "language": language,
                },
            }
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
