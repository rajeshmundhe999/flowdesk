"""Structured engineering-quality bug report generator."""

from flowdesk.clustering import IncidentSummary
from flowdesk.db import Ticket
from flowdesk.triage.rules import extract_error_signature

SCENARIO_DETAILS: dict[str, dict[str, str]] = {
    "ERR_PROXY_CONNECTION_FAILED": {
        "root_cause_hypothesis": (
            "The desktop client's HTTP/WebSocket transport is attempting direct connections "
            "or failing to inherit system proxy configuration (PAC / WPAD / Zscaler tunnel). "
            "Under SSL inspection, FlowDesk may be rejecting internal proxy root certificates "
            "because the application relies on an isolated certificate bundle."
        ),
        "repro_steps": (
            "1. Connect Windows workstation to corporate network with active Zscaler proxy.\n"
            "2. Ensure proxy enforces SSL MITM inspection or requires proxy auth on port 8080.\n"
            "3. Launch FlowDesk and trigger dictation hotkey.\n"
            "4. Observe immediate modal failure: 'Connection lost: ERR_PROXY_CONNECTION_FAILED'."
        ),
        "expected": (
            "FlowDesk honors OS system proxy settings and completes TLS handshake "
            "with enterprise CA."
        ),
        "actual": "Connection fails immediately with network drop error.",
        "workaround": (
            "Configure corporate proxy bypass for `*.dictation-api.com` or export company root CA "
            "and set `NODE_EXTRA_CA_CERTS` / import into FlowDesk custom trust store."
        ),
        "logs_requested": (
            "- `C:\\Users\\<user>\\AppData\\Local\\FlowDesk\\logs\\network.log`\n"
            "- Zscaler Client Connector policy version and diagnostic export\n"
            "- Proxy PAC URL and output from `netsh winhttp show proxy`"
        ),
        "unknowns": (
            "- Whether proxy requires NTLM authentication challenge\n"
            "- If WebSockets (WSS) are blocked on enterprise firewall port 443"
        ),
    },
    "No Model Available": {
        "root_cause_hypothesis": (
            "Cloud inference cluster routing failure or regional model server capacity "
            "exhaustion. Alternatively, a client-side config deserialization bug where the "
            "requested tier/model identifier does not match any key in the active model registry."
        ),
        "repro_steps": (
            "1. Launch FlowDesk v1.4.3.\n"
            "2. Ensure language is set to English (US).\n"
            "3. Press dictation hotkey (Ctrl+Space or Option+Space).\n"
            "4. Immediate red popup appears: 'No Model Available for current language/tier'."
        ),
        "expected": (
            "Audio stream connects to active transcription model and returns streaming text."
        ),
        "actual": (
            "Client receives HTTP 503 / 404 from inference router and surfaces "
            "'No Model Available'."
        ),
        "workaround": (
            "Switch model provider preference in Developer Settings if available, "
            "or retry in 5 minutes."
        ),
        "logs_requested": (
            "- Server request-id from client error banner\n"
            "- App log: `app.log` containing model routing handshake JSON\n"
            "- User account tier and assigned cluster endpoint"
        ),
        "unknowns": (
            "- Is this localized to a specific cloud region (e.g. us-east-1) or global?\n"
            "- Is the model router rejecting requests due to an expired deployment token?"
        ),
    },
    "Secure Keyboard Entry": {
        "root_cause_hypothesis": (
            "macOS `EnableSecureEventInput()` is enabled by a foreground application (e.g., "
            "Terminal, iTerm2, 1Password, or Bitwarden). When active, macOS intentionally blocks "
            "global `CGEventTap` interception to prevent keylogging, causing FlowDesk's global "
            "hotkey listener to fail."
        ),
        "repro_steps": (
            "1. Open Terminal.app or iTerm2 on macOS 14+.\n"
            "2. Enable 'Secure Keyboard Entry' in the Terminal menu.\n"
            "3. Press global dictation hotkey (Option+Space).\n"
            "4. Hotkey is completely ignored; system log outputs `kCGErrorCannotComplete`."
        ),
        "expected": (
            "FlowDesk detects locked event tap and displays an informational hint, or utilizes "
            "an alternative trigger mechanism."
        ),
        "actual": "Hotkey fails silently with zero user feedback.",
        "workaround": (
            "Uncheck 'Secure Keyboard Entry' in Terminal/iTerm2 menu, or blur focus from "
            "the password field."
        ),
        "logs_requested": (
            "- Output of `ioreg -l -w 0 | grep SecureInput` in terminal\n"
            "- macOS Console log filtered for `FlowDesk` event tap status\n"
            "- Name of active foreground application holding SecureInput lock"
        ),
        "unknowns": (
            "- Which third-party utility is maintaining persistent SecureInput lock when "
            "Terminal is closed?\n"
            "- Can FlowDesk register as an Input Method (IME) to bypass event tap restrictions?"
        ),
    },
    "Missing first words": {
        "root_cause_hypothesis": (
            "Bluetooth Low Energy / HFP (Hands-Free Profile) audio devices enter a low-power "
            "standby state when idle. Audio capture stream initiation lacks pre-roll buffering, "
            "causing the first 300-600ms of audio frames to be dropped before the Bluetooth SCO "
            "link is established."
        ),
        "repro_steps": (
            "1. Connect Bluetooth earbuds (AirPods Pro, Bose QC45) to iOS or macOS.\n"
            "2. Leave audio idle for 15 seconds so Bluetooth audio link sleeps.\n"
            "3. Tap dictation hotkey and immediately speak 'Today we need to review budget'.\n"
            "4. Inspect transcript: 'review budget' (first 2 words omitted)."
        ),
        "expected": "Full utterance captured without clipping initial syllables.",
        "actual": (
            "First 300-500ms of speech missing from audio buffer sent to transcription service."
        ),
        "workaround": (
            "Pause for half a second after pressing the hotkey before speaking, or keep an "
            "active low-volume audio keepalive."
        ),
        "logs_requested": (
            "- Audio input device properties (sample rate, buffer size, Bluetooth profile)\n"
            "- Local raw PCM recording dump if diagnostic logging enabled\n"
            "- Headset firmware version and OS Bluetooth stack logs"
        ),
        "unknowns": (
            "- Does introducing a 200ms audio ring-buffer before speech-to-text trigger "
            "eliminate the clipping?\n"
            "- Is the issue restricted to HFP profile or also present on A2DP with separate mic?"
        ),
    },
    "Text not pasting": {
        "root_cause_hypothesis": (
            "On macOS, synthetic keystroke injection via `CGEventPost` fails when OS Accessibility "
            "permissions are stale or invalidated by an app update. Alternatively, clipboard "
            "restoration fires before the target application processes `Cmd+V`."
        ),
        "repro_steps": (
            "1. Launch FlowDesk on macOS 14+.\n"
            "2. Focus target app (e.g., Slack, Notion, VS Code).\n"
            "3. Dictate a phrase and release hotkey.\n"
            "4. Dictation finishes and displays in floating pill, but target app remains unchanged."
        ),
        "expected": "Text is pasted into active caret position via simulated Cmd+V / paste event.",
        "actual": "No text appears in target app; clipboard retains previous contents.",
        "workaround": (
            "Remove and re-grant FlowDesk in System Settings > Privacy & Security > Accessibility."
        ),
        "logs_requested": (
            "- macOS `tccutil` accessibility permission status\n"
            "- App log showing `CGEventPost` return codes\n"
            "- Target application bundle identifier and window focus state"
        ),
        "unknowns": (
            "- Does target app block synthetic paste events?\n"
            "- Does switching from synthetic keypress to direct AXUIElement set-value fix this?"
        ),
    },
    "Non-QWERTY layout": {
        "root_cause_hypothesis": (
            "Text insertion engine uses hardcoded QWERTY virtual keycodes (`VK_A`, `VK_Q`, etc.) "
            "instead of querying `GetKeyboardLayout()` and translating unicode characters via "
            "`SendInput` `KEYEVENTF_UNICODE`."
        ),
        "repro_steps": (
            "1. Configure OS keyboard layout to French AZERTY or German QWERTZ.\n"
            "2. Dictate a sentence containing letters 'A' or 'Z'.\n"
            "3. Observe inserted text in Notepad or Word."
        ),
        "expected": "Text matches transcription exactly regardless of active keyboard layout.",
        "actual": (
            "'A' is typed as 'Q', 'Z' is typed as 'W', or punctuation characters are shifted."
        ),
        "workaround": "Switch active OS keyboard layout to English QWERTY before dictating.",
        "logs_requested": (
            "- Active Input Method and Keyboard Layout ID (`GetKeyboardLayout`)\n"
            "- Sample text transcribed vs text inserted\n"
            "- Windows SDK `SendInput` event tracer log"
        ),
        "unknowns": (
            "- Why is the text insertion driver not using `KEYEVENTF_UNICODE` exclusively?"
        ),
    },
}

DEFAULT_DETAILS: dict[str, str] = {
    "root_cause_hypothesis": (
        "Preliminary hypothesis: Software regression or unhandled edge case in client-server "
        "interaction under specific environmental constraints."
    ),
    "repro_steps": (
        "1. Open FlowDesk on affected platform.\n"
        "2. Trigger dictation under the reported environment conditions.\n"
        "3. Observe unexpected failure or abnormal behavior."
    ),
    "expected": "Application behaves normally according to specification.",
    "actual": "Application encounters errors, timeouts, or unexpected behavior.",
    "workaround": "Restart application and review known issues KB.",
    "logs_requested": "Client application debug logs, operating system build info, network logs.",
    "unknowns": "Exact trigger conditions across differing hardware configurations.",
}


def generate_bug_report(
    title: str,
    category: str,
    severity: str,
    platforms: list[str],
    versions: list[str],
    ticket_ids: list[str],
    first_seen: str,
    last_seen: str,
    signature: str | None = None,
    customer_quotes: list[str] | None = None,
) -> str:
    """Generate a standardized engineering Markdown bug report."""
    sig_key = signature or ""
    details = DEFAULT_DETAILS.copy()
    for known_sig, spec in SCENARIO_DETAILS.items():
        if known_sig.lower() in sig_key.lower():
            details.update(spec)
            break

    platforms_str = ", ".join(platforms) if platforms else "Unknown"
    versions_str = ", ".join(versions) if versions else "Unknown"
    ticket_links_str = ", ".join(f"`{tid}`" for tid in ticket_ids) if ticket_ids else "None"

    quotes_section = ""
    if customer_quotes:
        quotes_section = (
            "### Customer Verbatim\n"
            + "\n".join(f'> "{q.strip()}"' for q in customer_quotes[:3])
            + "\n\n"
        )

    time_span = f"First seen: {first_seen}, Last seen: {last_seen}"

    report = f"""# [BUG] {title}

| Field | Value |
|---|---|
| **Severity** | **{severity}** |
| **Category** | `{category}` |
| **Affected Platforms** | {platforms_str} |
| **Affected Versions** | {versions_str} |
| **Frequency / Volume** | {len(ticket_ids)} reported tickets ({time_span}) |
| **Related Tickets** | {ticket_links_str} |

---

## 1. Customer Impact & Symptom Overview
{details['actual']}
Multiple users report critical disruptions to their dictation workflow, preventing regular usage.

{quotes_section}## 2. Steps to Reproduce
{details['repro_steps']}

## 3. Expected vs Actual Behavior
- **Expected**: {details['expected']}
- **Actual**: {details['actual']}

## 4. Suspected Root Cause (Hypothesis)
> [!NOTE]
> **Engineering Hypothesis Only**: This root cause hypothesis is based on frontline support
> signal correlation and requires verification by Core Engineering.

{details['root_cause_hypothesis']}

## 5. Confirmed Workaround
{details['workaround']}

## 6. Logs & Diagnostic Evidence Requested
{details['logs_requested']}

## 7. What We Still Don't Know
{details['unknowns']}
"""
    return report.strip()


def generate_bug_report_from_incident(incident: IncidentSummary, tickets: list[Ticket]) -> str:
    """Generate bug report from an aggregated incident cluster."""
    quotes = [t.body[:200] for t in tickets if t.body]
    return generate_bug_report(
        title=incident.title.replace("Probable Incident: ", ""),
        category=incident.category,
        severity=incident.severity,
        platforms=incident.affected_platforms,
        versions=incident.affected_versions,
        ticket_ids=incident.ticket_ids,
        first_seen=incident.first_seen.strftime("%Y-%m-%d %H:%M UTC"),
        last_seen=incident.last_seen.strftime("%Y-%m-%d %H:%M UTC"),
        signature=incident.signature,
        customer_quotes=quotes,
    )


def generate_bug_report_from_ticket(
    ticket: Ticket,
    related_tickets: list[Ticket] | None = None,
) -> str:
    """Generate a single-ticket bug report."""
    related = related_tickets or []
    all_tids = [ticket.id] + [t.id for t in related]
    all_platforms = list({ticket.platform} | {t.platform for t in related if t.platform})
    all_versions = list({ticket.app_version} | {t.app_version for t in related if t.app_version})

    sig, _ = extract_error_signature(f"{ticket.subject} {ticket.body}")
    created_str = (
        ticket.created_at.strftime("%Y-%m-%d %H:%M UTC") if ticket.created_at else "Unknown"
    )

    return generate_bug_report(
        title=ticket.subject,
        category=ticket.category or "other",
        severity=ticket.severity or "P2",
        platforms=all_platforms,
        versions=all_versions,
        ticket_ids=all_tids,
        first_seen=created_str,
        last_seen=created_str,
        signature=sig,
        customer_quotes=[ticket.body[:250]],
    )
