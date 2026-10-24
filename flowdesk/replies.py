"""Human-in-the-loop customer reply drafter."""

import re
from typing import Any

from flowdesk.db import Ticket
from flowdesk.kb import KBArticle, match_kb_article

# Strict safety rule: replies must NEVER promise fixes or specific deadlines
PROMISE_PATTERNS = [
    re.compile(
        r"\b(?:promise|guarantee|will\s+be\s+fixed\s+by|eta\s+is|next\s+(?:release|week|month)|"
        r"tomorrow|by\s+end\s+of\s+day)\b",
        re.IGNORECASE,
    ),
]


def audit_against_false_promises(text: str) -> bool:
    """Ensure reply does not promise fixes, release versions, or delivery timelines."""
    for pattern in PROMISE_PATTERNS:
        if pattern.search(text):
            return False
    return True


def draft_customer_reply(
    ticket: Ticket,
    matched_article: KBArticle | None = None,
) -> dict[str, Any]:
    """Draft a concise, empathetic customer reply with exact fix steps and data safety notice.

    Always flagged for human review. Never sent automatically.
    """
    full_text = f"{ticket.subject}\n{ticket.body}"

    article = matched_article
    confidence = 0.0
    if not article:
        article, confidence = match_kb_article(full_text)

    greeting = "Hello,"

    if ticket.sentiment == "frustrated":
        empathy_line = (
            "Thank you for reaching out, and I am very sorry for the frustration this "
            "disruption has caused to your workflow."
        )
    elif ticket.plan_tier == "enterprise":
        empathy_line = (
            "Thank you for contacting FlowDesk Enterprise Support. We understand this is "
            "impacting your team's production dictation."
        )
    else:
        empathy_line = (
            "Thanks for contacting FlowDesk support. I am glad to help you resolve this issue."
        )

    if article:
        fix_section = article.fix
        data_safety = (
            article.data_safety
            or "Your speech data and transcripts remain secure and were not lost or compromised."
        )
        article_title = article.title
        article_id = article.id
    else:
        fix_section = (
            "1. Fully restart the FlowDesk desktop application.\n"
            "2. Verify you are running the latest app version.\n"
            "3. If the issue persists, run our diagnostic helper (`diagnose.py`) and share output."
        )
        data_safety = (
            "Your existing dictations and account data remain safe and encrypted in local history."
        )
        article_title = "Standard Troubleshooting"
        article_id = "general_troubleshooting"

    closure_line = (
        "If these steps do not immediately resolve the issue, please reply with your latest log "
        "file and our engineering team will investigate the specific environmental factors."
    )

    reply_body = f"""{greeting}

{empathy_line}

### Recommended Steps to Fix
{fix_section}

### Data Safety
{data_safety}

{closure_line}

Best regards,
FlowDesk Support Team
"""

    is_safe = audit_against_false_promises(reply_body)

    return {
        "ticket_id": ticket.id,
        "draft_text": reply_body.strip(),
        "matched_kb_id": article_id,
        "matched_kb_title": article_title,
        "data_safety_note": data_safety,
        "requires_human_review": True,
        "anti_promise_audit_passed": is_safe,
        "confidence": confidence,
    }
