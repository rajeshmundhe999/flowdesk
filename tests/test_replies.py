"""Unit tests for knowledge base matching and reply drafting."""

from flowdesk.db import Ticket
from flowdesk.kb import load_all_kb_articles, match_kb_article
from flowdesk.replies import audit_against_false_promises, draft_customer_reply


def test_load_all_kb_articles():
    articles = load_all_kb_articles()
    assert len(articles) == 11
    ids = {a.id for a in articles}
    assert "net_connection_lost_vpn" in ids
    assert "hotkey_macos_secure_input" in ids
    assert "ai_no_model_available" in ids


def test_match_kb_article_vpn():
    text = "Connection lost: ERR_PROXY_CONNECTION_FAILED behind corporate Zscaler VPN."
    article, conf = match_kb_article(text)
    assert article is not None
    assert article.id == "net_connection_lost_vpn"
    assert "Add an SSL bypass rule" in article.fix
    assert conf >= 0.7


def test_match_kb_article_secure_keyboard():
    text = "Option+Space fails because macOS Secure Keyboard Entry is active in Terminal."
    article, conf = match_kb_article(text)
    assert article is not None
    assert article.id == "hotkey_macos_secure_input"
    assert "Secure Keyboard Entry" in article.fix


def test_draft_customer_reply_contains_required_sections():
    ticket = Ticket(
        id="TCK-1001",
        subject="Connection lost every time I connect to company VPN",
        body="FlowDesk throws ERR_PROXY_CONNECTION_FAILED on Zscaler VPN.",
        platform="windows",
        app_version="1.4.2",
        os_version="Windows 11 23H2",
        plan_tier="enterprise",
        sentiment="frustrated",
    )

    draft = draft_customer_reply(ticket)

    assert draft["ticket_id"] == "TCK-1001"
    assert draft["requires_human_review"] is True
    assert draft["anti_promise_audit_passed"] is True
    assert "Recommended Steps to Fix" in draft["draft_text"]
    assert "Data Safety" in draft["draft_text"]
    assert "SSL bypass rule" in draft["draft_text"]


def test_anti_promise_auditor():
    unsafe_draft = (
        "We promise this will be fixed by tomorrow and guaranteed in the next release."
    )
    assert audit_against_false_promises(unsafe_draft) is False

    safe_draft = (
        "Here are the recommended steps to resolve the proxy timeout. Your data remains safe."
    )
    assert audit_against_false_promises(safe_draft) is True
