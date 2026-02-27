"""Azure AI Content Safety — analyze text for harmful content."""

import httpx
from config import Config

_http_client = httpx.Client(timeout=15.0)


def analyze_safety(text: str) -> dict:
    """
    Run Azure Content Safety text analysis.
    Returns a dict with maxSeverity (0–6) and categories; empty dict if disabled or on error.
    """
    if not text or not (
        Config.AZURE_CONTENT_SAFETY_ENDPOINT and Config.AZURE_CONTENT_SAFETY_KEY
    ):
        return {}

    try:
        url = (
            (Config.AZURE_CONTENT_SAFETY_ENDPOINT or "").rstrip("/")
            + "/contentsafety/text:analyze"
        )
        params = {"api-version": "2024-09-01"}
        headers = {
            "Ocp-Apim-Subscription-Key": Config.AZURE_CONTENT_SAFETY_KEY,
            "Content-Type": "application/json",
        }
        payload = {"text": text}
        response = _http_client.post(url, params=params, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        result = {"maxSeverity": 0, "categories": {}}
        for item in data.get("categoriesAnalysis", []):
            name = item.get("category", "")
            severity = item.get("severity", 0)
            result["categories"][name] = severity
            if severity > result["maxSeverity"]:
                result["maxSeverity"] = severity
        return result
    except Exception:
        return {}
