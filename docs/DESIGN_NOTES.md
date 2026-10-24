# FlowDesk Design Notes & Architectural Decisions

This document details the engineering choices, trade-offs, and operational principles behind **FlowDesk**, a Technical Support Engineering toolkit designed for desktop voice-dictation SaaS products.

---

## 1. Rules-First vs. LLM-Only Architecture

### The Problem with LLM-Only Triage in Production Support
Many AI-powered support tools immediately pass raw customer ticket text directly into Large Language Models (LLMs). While flexible, in a production support engineering environment this introduces four critical liabilities:
1. **Unpredictable Latency:** An external LLM API call introduces 800ms–3500ms of network latency per ticket. When processing sudden incident spikes (e.g., 500 tickets during a regional outage), this creates severe backpressure.
2. **Hallucination & Inconsistent Categorization:** LLMs can categorize the same error string (`ERR_PROXY_CONNECTION_FAILED`) as "Billing" or "Other" depending on slight prompt or temperature variations.
3. **High Ongoing Inference Cost:** Classifying high-volume ticket streams with cloud LLMs costs thousands of dollars monthly for questions with deterministic answers.
4. **Offline Resilience:** If cloud network connectivity drops, an LLM-only tool fails completely.

### The FlowDesk Hybrid Tiered Approach
FlowDesk uses a **rules-first, tiered decision architecture**:
- **Tier 1 (Deterministic Rules & Exact Signatures):**
  - High-confidence regex matches known error signatures (e.g., `ERR_TUNNEL_CONNECTION_FAILED`, `No Model Available`, `macOS Secure Keyboard Entry`).
  - Weighted category keyword scoring with runner-up ratio checks.
  - Generates confidence scores ($0.0$ to $1.0$).
  - **Latency:** $< 2\text{ ms}$, **Cost:** $\$0.00$, **Hallucination Risk:** $0\%$.
- **Tier 2 (LLM Fallback for Ambiguous Edge Cases):**
  - Triggered **only** when rule confidence falls below the configurable threshold ($0.75$) or when keywords produce conflicting category scores.
  - Strict boundary: Before payload transmission, all PII (emails, phone numbers, auth secrets) is scrubbed.
  - Provider-agnostic interface: Seamlessly routes between Google Gemini and Anthropic Claude via standard REST wrappers, with an automatic fallback to rule results if no API key is configured.

---

## 2. Why Human-in-the-Loop Review is Strictly Required

In customer support for productivity software, an incorrect automated email can destroy user trust. FlowDesk strictly enforces that **AI and rule-generated customer replies are NEVER sent automatically**:

1. **Environmental Nuance:** A customer might be running a niche Linux distribution or customized MDM profile where standard troubleshooting steps (e.g. `tccutil reset Accessibility`) may cause unexpected system states.
2. **Anti-Promise Verification (`anti_promise_audit_passed`):**
   - Support engineers must never promise release timelines or guaranteed fixes that have not been committed to by Core Engineering.
   - FlowDesk includes an automated regex auditor that blocks any reply containing words like *"we promise"*, *"will be fixed by tomorrow"*, or *"ETA is next week"*.
3. **Data Safety Assurance:**
   - Every draft explicitly informs the user whether their dictated speech and transcripts were safely stored in local encrypted history or discarded.

---

## 3. Pattern Detection & Incident Clustering Algorithm

Support engineers are often the first to notice an active regression before cloud monitoring triggers alerts.

### Clustering Key & Sliding Window
FlowDesk aggregates tickets using a hierarchical composite key:
$$\text{Cluster Key} = (\text{Category}, \text{Error Signature}, \text{Platform})$$

- **Window Partitioning:** Tickets are evaluated across a configurable rolling window (default: 48 hours).
- **Incident Threshold:** A cluster is flagged as a **"Probable Incident"** when $\ge 3$ tickets share the same signature within the window.
- **Systemic Outages vs. Local Bugs:**
  - Errors like `No Model Available` or `Word limit not resetting` represent global backend outages and span all platforms.
  - Hardware/OS-level conflicts like `macOS Secure Keyboard Entry` or `Hands-Free AG Audio` are isolated to specific platforms and versions.

---

## 4. PII Redaction Strategy at the Boundary

To satisfy GDPR, CCPA, and SOC 2 enterprise requirements:
- FlowDesk scrubs customer email addresses (`[REDACTED_EMAIL]`), international and domestic phone numbers (`[REDACTED_PHONE]`), and bearer tokens/API keys (`[REDACTED_SECRET]`).
- Redaction executes **synchronously in-memory before** any network payload is constructed for external LLM endpoints.
- Tests in `tests/test_pii.py` verify zero leakage of sensitive customer contact data.

---

## 5. Network Diagnostics Helper (`diagnose.py`)

When voice dictation fails, frontline support often struggles to determine whether the issue stems from the user's local network (corporate firewall / VPN SSL inspection) or cloud downtime.

### Design Principles:
- **Zero Third-Party Intrusion:** Probes only domains explicitly declared in `diagnose_config.json`.
- **Single Polite Probe:** Exactly one request per endpoint with strict timeouts (default 3.0s). No port scanning, no flood tests, no crawling.
- **Three-Stage Protocol Inspection:**
  1. **DNS Resolution:** Measures resolver latency and validates IP resolution.
  2. **TLS Handshake:** Catches corporate MITM proxies (e.g. Zscaler deep inspection) where the enterprise root CA is untrusted by the desktop client (`CERT_UNTRUSTED_ISSUER`).
  3. **HTTP Reachability:** Validates end-to-end round-trip latency and flags connections exceeding the warning threshold (500ms), which cause *"Taking longer than usual"* timeouts.

---

## 6. Technical Debt, Trade-offs & Limitations

| Decision | Trade-off | Rationale / Mitigation |
|---|---|---|
| **SQLite + SQLAlchemy** | Single-writer limitation; not suited for distributed horizontal scale. | Zero setup overhead for local evaluation; completely self-contained in a single file. |
| **Vanilla JS Frontend** | No reactive state management framework (e.g. React/Vue). | Zero node build step, zero npm vulnerability surface, instant loading via FastAPI static files. |
| **Heuristic Keyword Scorer** | Multi-intent tickets with overlapping keywords (e.g., "typing" + "lag") can misclassify. | Handled via low-confidence scoring ($<0.75$), routing ambiguous tickets to LLM fallback. |
