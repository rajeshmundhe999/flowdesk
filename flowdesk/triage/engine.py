"""Triage orchestrator: Rules first, LLM second for ambiguous cases."""

import logging
from datetime import UTC, datetime
from typing import Any

from flowdesk.config import settings
from flowdesk.db import Ticket
from flowdesk.triage.llm import is_llm_configured, llm_triage
from flowdesk.triage.rules import rules_triage

logger = logging.getLogger(__name__)


def triage_ticket_data(
    subject: str,
    body: str,
    platform: str = "unknown",
    app_version: str = "unknown",
    plan_tier: str = "free",
) -> dict[str, Any]:
    """Triage a ticket payload.

    Order of operations:
    1. Deterministic rules (regex + error signatures + keyword scoring)
    2. If confidence >= threshold or LLM unconfigured, accept rule decision.
    3. If confidence < threshold and LLM is configured, call LLM with PII scrubbed.
    """
    rule_res = rules_triage(
        subject=subject,
        body=body,
        plan_tier=plan_tier,
        platform=platform,
    )

    # If rules have high confidence or LLM is not configured, use rules
    if rule_res.confidence >= settings.confidence_threshold or not is_llm_configured():
        return {
            "category": rule_res.category,
            "severity": rule_res.severity,
            "sentiment": rule_res.sentiment,
            "confidence": round(rule_res.confidence, 2),
            "triage_reason": rule_res.reason,
            "triage_method": "rules",
            "error_signature": rule_res.error_signature,
        }

    # Low confidence -> fallback to LLM
    logger.info("Low confidence rule match (%.2f). Escalating to LLM...", rule_res.confidence)
    llm_res = llm_triage(
        subject=subject,
        body=body,
        platform=platform,
        app_version=app_version,
        plan_tier=plan_tier,
    )

    if llm_res:
        return {
            "category": llm_res.category,
            "severity": llm_res.severity,
            "sentiment": llm_res.sentiment,
            "confidence": round(llm_res.confidence, 2),
            "triage_reason": f"LLM triage: {llm_res.reason}",
            "triage_method": "llm",
            "error_signature": rule_res.error_signature,
        }

    # If LLM failed, fallback to rules decision
    return {
        "category": rule_res.category,
        "severity": rule_res.severity,
        "sentiment": rule_res.sentiment,
        "confidence": round(rule_res.confidence, 2),
        "triage_reason": f"{rule_res.reason} (LLM unavailable/fallback)",
        "triage_method": "rules",
        "error_signature": rule_res.error_signature,
    }


def triage_and_update_ticket(ticket: Ticket) -> Ticket:
    """Triage a Ticket ORM object and persist triage fields."""
    res = triage_ticket_data(
        subject=ticket.subject,
        body=ticket.body,
        platform=ticket.platform,
        app_version=ticket.app_version,
        plan_tier=ticket.plan_tier,
    )

    ticket.category = res["category"]
    ticket.severity = res["severity"]
    ticket.sentiment = res["sentiment"]
    ticket.confidence = res["confidence"]
    ticket.triage_reason = res["triage_reason"]
    ticket.triage_method = res["triage_method"]
    ticket.triaged_at = datetime.now(UTC)

    return ticket
