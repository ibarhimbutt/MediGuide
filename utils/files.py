"""File and PDF handling utilities."""

import io
import os
from PyPDF2 import PdfReader


def get_file_extension(filename: str) -> str:
    """Return the lowercased file extension, e.g. '.pdf'."""
    return os.path.splitext(filename or "")[1].lower()


def extract_pdf_text(file_bytes: bytes) -> str:
    """Extract text from a PDF byte stream. Returns concatenated page text."""
    reader = PdfReader(io.BytesIO(file_bytes))
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts)
