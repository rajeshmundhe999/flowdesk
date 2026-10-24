"""Unit tests for the bug report generator."""

from datetime import datetime

from flowdesk.bug_reports import (
    generate_bug_report,
    generate_bug_report_from_incident,
    generate_bug_report_from_ticket,
)
from flowdesk.clustering import IncidentSummary
from flowdesk.db import Ticket


def test_bug_report_contains_all_required_sections():
    report = generate_bug_report(
        title="macOS Secure Keyboard Entry Lockout",
        category="hotkeys",
        severity="P2",
        platforms=["macos"],
        versions=["1.4.3"],
        ticket_ids=["TCK-1021", "TCK-1022", "TCK-1023"],
        first_seen="2026-10-22 08:20 UTC",
        last_seen="2026-10-22 09:15 UTC",
        signature="Secure Keyboard Entry",
    )

    # Verify all required sections exist in markdown
    assert "# [BUG]" in report
    assert "Affected Platforms" in report
    assert "Affected Versions" in report
    assert "Steps to Reproduce" in report
    assert "Expected vs Actual Behavior" in report
    assert "Customer Impact" in report
    assert "Suspected Root Cause (Hypothesis)" in report
    assert "Hypothesis Only" in report
    assert "Confirmed Workaround" in report
    assert "Logs & Diagnostic Evidence Requested" in report
    assert "What We Still Don't Know" in report
    assert "TCK-1021" in report


def test_bug_report_from_incident():
    incident = IncidentSummary(
        id="INC-20261021-001",
        title="Probable Incident: No Model Available on windows",
        category="network/timeouts",
        severity="P0",
        ticket_count=4,
        ticket_ids=["TCK-1009", "TCK-1010", "TCK-1011", "TCK-1012"],
        first_seen=datetime(2026, 10, 21, 9, 0),
        last_seen=datetime(2026, 10, 21, 10, 12),
        affected_platforms=["windows"],
        affected_versions=["1.4.3"],
        signature="No Model Available",
        summary="Cluster of 4 tickets for No Model Available",
    )
    tickets = [
        Ticket(
            id=tid,
            platform="windows",
            app_version="1.4.3",
            os_version="Win11",
            subject="No Model Available",
            body="Cannot dictate, screen says No Model Available",
            category="network/timeouts",
            severity="P0",
        )
        for tid in incident.ticket_ids
    ]

    report = generate_bug_report_from_incident(incident, tickets)
    assert "**P0**" in report
    assert "TCK-1009" in report
    assert "Steps to Reproduce" in report
    assert "Engineering Hypothesis Only" in report
    assert "What We Still Don't Know" in report


def test_bug_report_from_single_ticket():
    ticket = Ticket(
        id="TCK-1001",
        created_at=datetime(2026, 10, 20, 8, 15),
        platform="windows",
        app_version="1.4.2",
        os_version="Windows 11 23H2",
        subject="Connection lost behind Zscaler VPN",
        body="App fails with ERR_PROXY_CONNECTION_FAILED on VPN.",
        category="network/timeouts",
        severity="P1",
    )

    report = generate_bug_report_from_ticket(ticket)
    assert "TCK-1001" in report
    assert "ERR_PROXY_CONNECTION_FAILED" in report
    assert "Steps to Reproduce" in report
    assert "Confirmed Workaround" in report
