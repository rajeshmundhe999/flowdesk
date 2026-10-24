"""PII redaction utility to sanitize user inputs before external processing."""

import re
from typing import NamedTuple

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)

# Handles international and domestic formats, 7-digit or 10-digit with optional country code
# e.g., +1-555-0142, (555) 123-4567, 555.987.6543, +44 20 7946 0958
PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b"
)

# Common API key and auth token patterns (Bearer eyJ..., sk-..., etc.)
SECRET_PATTERN = re.compile(
    r"\b(?:Bearer\s+[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*|sk-[A-Za-z0-9_-]{20,})\b",
    re.IGNORECASE,
)


class RedactionResult(NamedTuple):
    sanitized_text: str
    redacted_emails: int
    redacted_phones: int
    redacted_secrets: int

    @property
    def has_redactions(self) -> bool:
        return (self.redacted_emails + self.redacted_phones + self.redacted_secrets) > 0


def redact_pii(text: str) -> RedactionResult:
    """Scrub PII (email, phone numbers, API secrets) from the input string."""
    if not text:
        return RedactionResult(text, 0, 0, 0)

    # Redact secrets first
    sanitized, secrets_count = SECRET_PATTERN.subn("[REDACTED_SECRET]", text)

    # Redact emails
    sanitized, emails_count = EMAIL_PATTERN.subn("[REDACTED_EMAIL]", sanitized)

    # Redact phone numbers
    sanitized, phones_count = PHONE_PATTERN.subn("[REDACTED_PHONE]", sanitized)

    return RedactionResult(
        sanitized_text=sanitized,
        redacted_emails=emails_count,
        redacted_phones=phones_count,
        redacted_secrets=secrets_count,
    )
