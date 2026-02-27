"""Azure AI Translator — translate AI responses into the user's language."""

import httpx
from config import Config

_http_client = httpx.Client(timeout=15.0)


def translate(text: str, target_language: str) -> str:
    """
    Translate text using Azure Translator.
    Returns original text if target is 'en', config is missing, or translation fails.
    """
    if not text or (target_language or "").strip().lower() == "en":
        return text
    if not all([
        Config.AZURE_TRANSLATOR_ENDPOINT,
        Config.AZURE_TRANSLATOR_KEY,
        Config.AZURE_TRANSLATOR_REGION,
    ]):
        return text

    try:
        url = (Config.AZURE_TRANSLATOR_ENDPOINT or "").rstrip("/") + "/translate"
        params = {"api-version": "3.0", "to": target_language.strip().lower()}
        headers = {
            "Ocp-Apim-Subscription-Key": Config.AZURE_TRANSLATOR_KEY,
            "Ocp-Apim-Subscription-Region": Config.AZURE_TRANSLATOR_REGION,
            "Content-Type": "application/json",
        }
        payload = [{"text": text}]
        response = _http_client.post(url, params=params, headers=headers, json=payload)
        response.raise_for_status()
        body = response.json()
        return body[0]["translations"][0]["text"]
    except Exception:
        return text
