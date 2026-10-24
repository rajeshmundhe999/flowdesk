"""Unit tests for the triage engine and rules."""

from flowdesk.db import Ticket
from flowdesk.triage.engine import triage_and_update_ticket
from flowdesk.triage.rules import (
    detect_sentiment,
    rules_triage,
)


def test_classify_network_vpn():
    text = "Connection lost: ERR_PROXY_CONNECTION_FAILED when connected to corporate Zscaler VPN."
    res = rules_triage("VPN Connection Lost", text, plan_tier="enterprise")
    assert res.category == "network/timeouts"
    assert res.severity == "P1"
    assert res.confidence >= 0.85
    assert res.error_signature == "ERR_PROXY_CONNECTION_FAILED"


def test_classify_no_model_available_as_p0():
    text = "Pressing dictation hotkey triggers error: No Model Available for current language."
    res = rules_triage("No Model Available", text, plan_tier="pro")
    assert res.category == "network/timeouts"
    assert res.severity == "P0"
    assert res.confidence >= 0.90
    assert res.error_signature == "No Model Available"


def test_classify_audio_missing_first_words():
    text = "Missing first words in transcripts whenever I dictate on my Bluetooth AirPods Pro."
    res = rules_triage("First words cut off", text, plan_tier="free")
    assert res.category == "audio/mic"
    assert res.severity in {"P2", "P3"}
    assert res.error_signature == "Missing first words"


def test_classify_text_insertion_azerty():
    text = "On French AZERTY keyboard, FlowDesk types Q instead of A and Z instead of W."
    res = rules_triage("AZERTY layout swapped keys", text, plan_tier="pro")
    assert res.category == "text insertion"
    assert res.error_signature == "Non-QWERTY layout"


def test_classify_hotkey_secure_input():
    text = "Hotkey Option+Space fails because macOS Secure Keyboard Entry is active in Terminal."
    res = rules_triage("Hotkey conflict in Terminal", text, plan_tier="pro")
    assert res.category == "hotkeys"
    assert res.error_signature == "Secure Keyboard Entry"


def test_classify_billing_word_limit():
    text = (
        "Subscription renewed and Stripe charged, but word limit not resetting. Blocked from work!"
    )
    res = rules_triage("Word limit not resetting", text, plan_tier="pro")
    assert res.category == "billing"
    assert res.severity == "P1"
    assert res.sentiment == "frustrated"


def test_classify_feature_request_p3():
    text = "Would love to request custom vocabulary support for medical oncology terms."
    res = rules_triage("Feature Request: Custom vocabulary", text, plan_tier="pro")
    assert res.category == "feature request"
    assert res.severity == "P3"


def test_sentiment_detection():
    assert (
        detect_sentiment("This is completely broken and terrible! ASAP help needed!!")
        == "frustrated"
    )
    assert (
        detect_sentiment("Love the app, it is a great tool for my daily writing!")
        == "satisfied"
    )
    assert detect_sentiment("The application version is 1.4.2 on Windows 11.") == "neutral"


def test_triage_engine_updates_ticket_model():
    ticket = Ticket(
        id="TCK-MOCK-1",
        subject="Connection lost behind proxy",
        body="Getting ERR_TUNNEL_CONNECTION_FAILED on Windows 11 corporate proxy.",
        platform="windows",
        app_version="1.4.2",
        os_version="Windows 11",
        plan_tier="enterprise",
    )
    updated = triage_and_update_ticket(ticket)
    assert updated.category == "network/timeouts"
    assert updated.severity == "P1"
    assert updated.triage_method == "rules"
    assert updated.confidence >= 0.8
    assert updated.triaged_at is not None
