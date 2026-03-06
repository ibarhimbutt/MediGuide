"""
MediGuide AI — PDF generation for ER Prep Sheet and Health Timeline.
"""
from io import BytesIO
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_CENTER


def _header_style():
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        name="MediGuideHeader",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#5eb5c0"),
        spaceAfter=6,
        alignment=TA_CENTER,
    )


def _section_style():
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        name="SectionStyle",
        parent=styles["Heading2"],
        fontSize=11,
        textColor=colors.HexColor("#374151"),
        spaceBefore=10,
        spaceAfter=4,
    )


def _body_style():
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        name="BodyStyle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#4b5563"),
        spaceAfter=6,
    )


def build_er_prep_sheet(
    patient_name: str,
    symptoms: str,
    symptom_timeline: str,
    urgency: str,
    medications: List[str],
    past_interactions: List[dict],
    doctor_questions: List[str],
) -> bytes:
    """Generate a one-page ER Prep Sheet PDF."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    story = []

    # Header
    story.append(Paragraph("MediGuide AI", _header_style()))
    story.append(Paragraph("Emergency Room Prep Sheet", ParagraphStyle(
        name="SubHeader",
        fontSize=14,
        textColor=colors.HexColor("#6b7280"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )))
    story.append(Spacer(1, 6))

    # Patient info
    story.append(Paragraph("Patient Information", _section_style()))
    story.append(Paragraph(f"<b>Name:</b> {patient_name}", _body_style()))
    story.append(Spacer(1, 4))

    # Symptoms
    story.append(Paragraph("Symptoms Described", _section_style()))
    story.append(Paragraph(symptoms.replace("\n", "<br/>"), _body_style()))
    story.append(Spacer(1, 4))

    # Symptoms timeline
    story.append(Paragraph("Symptom Timeline", _section_style()))
    story.append(Paragraph(symptom_timeline.replace("\n", "<br/>"), _body_style()))
    story.append(Spacer(1, 4))

    # Urgency
    story.append(Paragraph("Urgency Level", _section_style()))
    urgency_colors = {"HIGH": "#dc2626", "MEDIUM": "#d97706", "LOW": "#059669"}
    hex_color = urgency_colors.get(urgency.upper(), "#6b7280")
    story.append(Paragraph(
        f'<font color="{hex_color}"><b>{urgency.upper()}</b></font> — '
        f'{"Seek urgent care" if urgency.upper() == "HIGH" else "See a doctor soon" if urgency.upper() == "MEDIUM" else "Self-care may be sufficient"}',
        _body_style(),
    ))
    story.append(Spacer(1, 4))

    # Current medications
    story.append(Paragraph("Current Medications", _section_style()))
    med_text = ", ".join(medications) if medications else "None reported"
    story.append(Paragraph(med_text, _body_style()))
    story.append(Spacer(1, 4))

    # Past health interactions
    story.append(Paragraph("Relevant Past Health Interactions", _section_style()))
    if past_interactions:
        for i, item in enumerate(past_interactions[:3], 1):
            feat = item.get("feature", "")
            summary = item.get("summary", "")
            story.append(Paragraph(f"{i}. {feat}: {summary}", _body_style()))
    else:
        story.append(Paragraph("No recent interactions on record.", _body_style()))
    story.append(Spacer(1, 4))

    # Doctor questions
    story.append(Paragraph("Questions to Ask Your Doctor", _section_style()))
    for i, q in enumerate(doctor_questions[:5], 1):
        story.append(Paragraph(f"{i}. {q}", _body_style()))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "<i>This sheet is for informational purposes only. Always seek professional medical care for urgent symptoms.</i>",
        ParagraphStyle(name="Disclaimer", fontSize=8, textColor=colors.HexColor("#9ca3af")),
    ))

    doc.build(story)
    return buffer.getvalue()


def build_health_timeline_pdf(
    patient_name: str,
    date_range: str,
    ai_summary: str,
    entries: List[dict],
) -> bytes:
    """Generate a PDF summary of the health timeline."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    story = []

    story.append(Paragraph("MediGuide AI", _header_style()))
    story.append(Paragraph("Health Timeline Report", ParagraphStyle(
        name="SubHeader",
        fontSize=14,
        textColor=colors.HexColor("#6b7280"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Patient", _section_style()))
    story.append(Paragraph(patient_name, _body_style()))
    story.append(Paragraph(f"<b>Period:</b> {date_range}", _body_style()))
    story.append(Spacer(1, 4))

    story.append(Paragraph("AI Health Summary", _section_style()))
    story.append(Paragraph(ai_summary.replace("\n", "<br/>"), _body_style()))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Timeline Entries", _section_style()))
    for i, entry in enumerate(entries[:30], 1):
        dt = entry.get("date", "")
        feat = entry.get("feature", "")
        summary = entry.get("summary", "")
        urgency = entry.get("urgency", "")
        story.append(Paragraph(
            f"<b>{dt}</b> — {feat} | {urgency}<br/>{summary}"
            if summary else f"<b>{dt}</b> — {feat} | {urgency}",
            _body_style(),
        ))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "<i>This report is for informational purposes only. Always consult a healthcare provider for medical advice.</i>",
        ParagraphStyle(name="Disclaimer", fontSize=8, textColor=colors.HexColor("#9ca3af")),
    ))

    doc.build(story)
    return buffer.getvalue()
