"""Unit tests for PII redaction."""

from flowdesk.pii import redact_pii


def test_redact_email_addresses():
    sample = "Please email me at john.doe@example.com or support@company.co.uk immediately."
    res = redact_pii(sample)
    assert res.redacted_emails == 2
    assert "john.doe@example.com" not in res.sanitized_text
    assert "support@company.co.uk" not in res.sanitized_text
    assert "[REDACTED_EMAIL]" in res.sanitized_text


def test_redact_phone_numbers():
    sample = "Call me back at +1-555-0142 or (555) 123-4567, or 555.987.6543."
    res = redact_pii(sample)
    assert res.redacted_phones == 3
    assert "+1-555-0142" not in res.sanitized_text
    assert "[REDACTED_PHONE]" in res.sanitized_text


def test_redact_api_secrets():
    sample = "My token was sk-live1234567890abcdef1234567890."
    res = redact_pii(sample)
    assert res.redacted_secrets == 1
    assert "sk-live" not in res.sanitized_text
    assert "[REDACTED_SECRET]" in res.sanitized_text


def test_clean_text_remains_unchanged():
    sample = "Dictation does not work behind Zscaler proxy with ERR_TUNNEL_CONNECTION_FAILED."
    res = redact_pii(sample)
    assert not res.has_redactions
    assert res.sanitized_text == sample
