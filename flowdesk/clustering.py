"""Pattern detection and incident clustering engine."""

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from flowdesk.config import settings
from flowdesk.db import Incident, Ticket
from flowdesk.triage.rules import extract_error_signature


@dataclass
class IncidentSummary:
    id: str
    title: str
    category: str
    severity: str
    ticket_count: int
    ticket_ids: list[str]
    first_seen: datetime
    last_seen: datetime
    affected_platforms: list[str]
    affected_versions: list[str]
    signature: str
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "severity": self.severity,
            "ticket_count": self.ticket_count,
            "ticket_ids": self.ticket_ids,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "affected_platforms": self.affected_platforms,
            "affected_versions": self.affected_versions,
            "signature": self.signature,
            "summary": self.summary,
        }


def generate_cluster_key(ticket: Ticket) -> tuple[str, str, str]:
    """Extract grouping key: (category, signature, platform)."""
    full_text = f"{ticket.subject} {ticket.body}"
    sig, sig_cat = extract_error_signature(full_text)

    category = ticket.category or sig_cat or "other"
    signature = sig or "Generic Issue"

    # Some systemic issues span platforms (e.g. backend auth or billing)
    platform = (
        ticket.platform
        if signature not in {"No Model Available", "Word limit not resetting", "Captcha loop"}
        else "all"
    )

    return category, signature, platform


def build_cluster_summary(
    cluster_key: tuple[str, str, str],
    tickets: list[Ticket],
) -> IncidentSummary:
    """Generate an engineering-grade incident summary for a group of tickets."""
    category, signature, _ = cluster_key
    sorted_tickets = sorted(tickets, key=lambda t: t.created_at)

    first_seen = sorted_tickets[0].created_at
    last_seen = sorted_tickets[-1].created_at
    ticket_ids = [t.id for t in sorted_tickets]

    platforms = sorted(list({t.platform for t in tickets if t.platform}))
    versions = sorted(list({t.app_version for t in tickets if t.app_version}))

    # Highest severity among tickets
    severities = [t.severity for t in tickets if t.severity]
    severity = "P2"
    for s in ("P0", "P1", "P2", "P3"):
        if s in severities:
            severity = s
            break

    # Stable deterministic ID
    hash_seed = f"{category}:{signature}:{first_seen.isoformat()}"
    cluster_hash = hashlib.sha1(hash_seed.encode("utf-8")).hexdigest()[:8]
    inc_id = f"INC-{first_seen.strftime('%Y%m%d')}-{cluster_hash}"

    title = f"Probable Incident: {signature} on {', '.join(platforms)} ({category})"

    # Narrative summary
    span_hours = max(0.1, round((last_seen - first_seen).total_seconds() / 3600.0, 1))
    first_str = first_seen.strftime("%Y-%m-%d %H:%M")
    last_str = last_seen.strftime("%Y-%m-%d %H:%M")
    summary = (
        f"Detected {len(tickets)} related tickets within {span_hours} hours "
        f"(from {first_str} to {last_str} UTC). "
        f"Shared signal: '{signature}'. Affected platforms: {', '.join(platforms)}; "
        f"versions: {', '.join(versions)}. Severity assessed at {severity}."
    )

    return IncidentSummary(
        id=inc_id,
        title=title,
        category=category,
        severity=severity,
        ticket_count=len(tickets),
        ticket_ids=ticket_ids,
        first_seen=first_seen,
        last_seen=last_seen,
        affected_platforms=platforms,
        affected_versions=versions,
        signature=signature,
        summary=summary,
    )


def cluster_tickets(
    tickets: list[Ticket],
    min_tickets: int = 3,
    window_hours: int = 48,
) -> list[IncidentSummary]:
    """Cluster tickets sharing platform + app version/signature + category within time window."""
    groups: dict[tuple[str, str, str], list[Ticket]] = defaultdict(list)

    for t in tickets:
        key = generate_cluster_key(t)
        # Skip tickets with no distinct signature and generic category
        if key[1] == "Generic Issue" and key[0] in {"other", "feature request"}:
            continue
        groups[key].append(t)

    incidents: list[IncidentSummary] = []
    window_delta = timedelta(hours=window_hours)

    for cluster_key, group_tickets in groups.items():
        if len(group_tickets) < min_tickets:
            continue

        sorted_group = sorted(group_tickets, key=lambda t: t.created_at)

        # Sliding window partition
        current_batch: list[Ticket] = []
        for t in sorted_group:
            if not current_batch:
                current_batch.append(t)
                continue

            if t.created_at - current_batch[0].created_at <= window_delta:
                current_batch.append(t)
            else:
                if len(current_batch) >= min_tickets:
                    incidents.append(build_cluster_summary(cluster_key, current_batch))
                current_batch = [t]

        if len(current_batch) >= min_tickets:
            incidents.append(build_cluster_summary(cluster_key, current_batch))

    return sorted(incidents, key=lambda inc: (inc.severity, -inc.ticket_count))


def run_pattern_detection(
    db: Session,
    min_tickets: int | None = None,
    window_hours: int | None = None,
) -> list[IncidentSummary]:
    """Run pattern detection on all tickets in the DB, link cluster IDs, and persist incidents."""
    m_tickets = min_tickets or settings.incident_min_tickets
    w_hours = window_hours or settings.incident_window_hours

    tickets = db.query(Ticket).all()
    incidents = cluster_tickets(tickets, min_tickets=m_tickets, window_hours=w_hours)

    # Persist or update incidents in DB and assign cluster_id to tickets
    for inc in incidents:
        # Check existing incident
        existing_inc = db.get(Incident, inc.id)
        if not existing_inc:
            db_incident = Incident(
                id=inc.id,
                title=inc.title,
                category=inc.category,
                severity=inc.severity,
                ticket_count=inc.ticket_count,
                first_seen=inc.first_seen,
                last_seen=inc.last_seen,
                affected_platforms=",".join(inc.affected_platforms),
                affected_versions=",".join(inc.affected_versions),
                signature=inc.signature,
                summary=inc.summary,
            )
            db.add(db_incident)

        # Tag tickets
        for tid in inc.ticket_ids:
            t = db.get(Ticket, tid)
            if t:
                t.cluster_id = inc.id

    db.commit()
    return incidents
