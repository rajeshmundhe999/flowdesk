"""Provider-agnostic LLM caller with strict PII scrubbing and rules fallback."""

import json
import logging
import os
from typing import Any, NamedTuple

import httpx

from flowdesk.config import settings
from flowdesk.pii import redact_pii

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Technical Support Triage Engineer for a voice-dictation SaaS
desktop application.
Classify incoming tickets into the following taxonomy:
- category: one of ["billing", "account/login", "network/timeouts", "audio/mic",
  "text insertion", "hotkeys", "performance", "feature request", "other"]
- severity: one of ["P0", "P1", "P2", "P3"]
  (P0 = complete outage/No Model Available; P1 = enterprise/paid user totally blocked;
   P2 = degraded/workaround exists; P3 = minor/inquiry/feature request)
- sentiment: one of ["frustrated", "neutral", "satisfied"]
- confidence: float between 0.0 and 1.0
- reason: brief 1-sentence engineering justification

Respond with pure JSON only matching this schema:
{
  "category": "...",
  "severity": "...",
  "sentiment": "...",
  "confidence": 0.9,
  "reason": "..."
}"""


class LLMTriageResult(NamedTuple):
    category: str
    severity: str
    sentiment: str
    confidence: float
    reason: str
    raw_response: str | None


def is_llm_configured() -> bool:
    """Check if any LLM provider has an active API key configured."""
    provider = settings.llm_provider
    if provider == "none":
        return False
    if settings.gemini_api_key or os.getenv("GEMINI_API_KEY"):
        return True
    if settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"):
        return True
    return False


def call_gemini(prompt: str, api_key: str) -> str:
    """Call Google Gemini REST API using httpx."""
    base_url = "https://generativelanguage.googleapis.com/v1beta/models"
    url = f"{base_url}/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\nTicket to classify:\n{prompt}"}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


def call_anthropic(prompt: str, api_key: str) -> str:
    """Call Anthropic Claude REST API using httpx."""
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 300,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


def llm_triage(
    subject: str,
    body: str,
    platform: str = "unknown",
    app_version: str = "unknown",
    plan_tier: str = "free",
) -> LLMTriageResult | None:
    """Run LLM classification after strictly scrubbing all PII."""
    if not is_llm_configured():
        return None

    # Step 1: Strict PII redaction
    sanitized_subject = redact_pii(subject).sanitized_text
    sanitized_body = redact_pii(body).sanitized_text

    prompt = (
        f"Platform: {platform}\n"
        f"App Version: {app_version}\n"
        f"Plan Tier: {plan_tier}\n"
        f"Subject: {sanitized_subject}\n"
        f"Body:\n{sanitized_body}"
    )

    gemini_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
    anthropic_key = settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
    provider = settings.llm_provider

    text_resp: str | None = None
    try:
        if (provider in {"auto", "gemini"}) and gemini_key:
            text_resp = call_gemini(prompt, gemini_key)
        elif (provider in {"auto", "anthropic"}) and anthropic_key:
            text_resp = call_anthropic(prompt, anthropic_key)
        elif gemini_key:
            text_resp = call_gemini(prompt, gemini_key)
        elif anthropic_key:
            text_resp = call_anthropic(prompt, anthropic_key)
    except Exception as exc:
        logger.warning("LLM API call failed, falling back to rules: %s", exc)
        return None

    if not text_resp:
        return None

    try:
        cleaned = text_resp.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        parsed: dict[str, Any] = json.loads(cleaned.strip())
        return LLMTriageResult(
            category=str(parsed.get("category", "other")),
            severity=str(parsed.get("severity", "P2")),
            sentiment=str(parsed.get("sentiment", "neutral")),
            confidence=float(parsed.get("confidence", 0.85)),
            reason=str(parsed.get("reason", "Classified by LLM")),
            raw_response=text_resp,
        )
    except Exception as exc:
        logger.warning("Failed to parse LLM JSON response: %s", exc)
        return None
