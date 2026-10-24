"""Deterministic rules-based triage engine."""

import re
from typing import NamedTuple

CATEGORIES = [
    "billing",
    "account/login",
    "network/timeouts",
    "audio/mic",
    "text insertion",
    "hotkeys",
    "performance",
    "feature request",
    "other",
]

SEVERITIES = ["P0", "P1", "P2", "P3"]
SENTIMENTS = ["frustrated", "neutral", "satisfied"]


class RuleTriageResult(NamedTuple):
    category: str
    severity: str
    sentiment: str
    confidence: float
    reason: str
    error_signature: str | None


# Known exact error signatures
ERROR_SIGNATURES: list[tuple[str, re.Pattern, str]] = [
    (
        "No Model Available",
        re.compile(r"no\s+model\s+available", re.IGNORECASE),
        "network/timeouts",
    ),
    (
        "ERR_PROXY_CONNECTION_FAILED",
        re.compile(r"err_proxy_connection_failed", re.IGNORECASE),
        "network/timeouts",
    ),
    (
        "ERR_TUNNEL_CONNECTION_FAILED",
        re.compile(r"err_tunnel_connection_failed", re.IGNORECASE),
        "network/timeouts",
    ),
    (
        "CERT_UNTRUSTED_ISSUER",
        re.compile(r"cert_untrusted_issuer|ssl\s+deep\s+inspection", re.IGNORECASE),
        "network/timeouts",
    ),
    (
        "Taking longer than usual",
        re.compile(r"taking\s+longer\s+than\s+usual", re.IGNORECASE),
        "network/timeouts",
    ),
    (
        "Secure Keyboard Entry",
        re.compile(r"secure\s+keyboard\s+entry|kcgerrorcannotcomplete", re.IGNORECASE),
        "hotkeys",
    ),
    (
        "Missing first words",
        re.compile(
            r"missing\s+first\s+words?|first\s+(?:2-3\s+)?words?\s+(?:missing|omitted|cut\s+off)",
            re.IGNORECASE,
        ),
        "audio/mic",
    ),
    (
        "Hands-Free AG Audio",
        re.compile(r"hands-free\s+ag|audclnt_e_unsupported_format", re.IGNORECASE),
        "audio/mic",
    ),
    (
        "Text not pasting",
        re.compile(r"text\s+not\s+pasting|keystroke\s+injection\s+failure", re.IGNORECASE),
        "text insertion",
    ),
    (
        "Non-QWERTY layout",
        re.compile(r"azerty|qwertz|dvorak|non-qwerty", re.IGNORECASE),
        "text insertion",
    ),
    (
        "Captcha loop",
        re.compile(r"captcha\s+loop|turnstile|state_mismatch", re.IGNORECASE),
        "account/login",
    ),
    (
        "Word limit not resetting",
        re.compile(
            r"word\s+limit\s+not\s+resetting|limit\s+exceeded.*paid|subscription\s+renewed.*zero",
            re.IGNORECASE,
        ),
        "billing",
    ),
    (
        "Android work profile",
        re.compile(
            r"work\s+profile\s+sandbox|knox|intune|managed\s+profile|audio_record_restricted",
            re.IGNORECASE,
        ),
        "text insertion",
    ),
]

# Category pattern heuristics
CATEGORY_PATTERNS: dict[str, list[re.Pattern]] = {
    "billing": [
        re.compile(
            r"\b(?:invoice|receipt|stripe|refund|charge|charged|billing|credit\s+card|"
            r"word\s+limit|subscription|seat[s]?)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(?:upgrade[d]?|renewal|renewed|paid\s+tier|pro\s+plan)\b", re.IGNORECASE),
    ],
    "account/login": [
        re.compile(
            r"\b(?:login|sign\s*in|sso|google\s+sso|oauth|auth|password|captcha|turnstile|"
            r"2fa|session)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:redirect\s+loop|state_mismatch|unauthorized|forbidden|401|403)\b",
            re.IGNORECASE,
        ),
    ],
    "network/timeouts": [
        re.compile(
            r"\b(?:connection\s+lost|timeout|timed\s+out|taking\s+longer\s+than\s+usual|"
            r"vpn|proxy|zscaler|anyconnect|firewall)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:err_|gateway|dns|socket|websocket|disconnected|offline|no\s+model\s+available)\b",
            re.IGNORECASE,
        ),
    ],
    "audio/mic": [
        re.compile(
            r"\b(?:mic|microphone|audio|bluetooth|headset|earphones|airpods|airpod|sound|"
            r"recording|sample\s+rate)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:hands-free|cut\s+off|missing\s+first|muffled|mono|noise|unsupported_format)\b",
            re.IGNORECASE,
        ),
    ],
    "text insertion": [
        re.compile(
            r"\b(?:paste|pasting|clipboard|keystroke|typed|types|typing|accessibility|ime)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:azerty|qwertz|dvorak|layout|accent|inverted|swapped|garbled|gibberish)\b",
            re.IGNORECASE,
        ),
    ],
    "hotkeys": [
        re.compile(
            r"\b(?:hotkey|shortcut|keybinding|secure\s+keyboard\s+entry|option\+space|"
            r"ctrl\+space|cmd\+space)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:global\s+shortcut|unresponsive\s+key|event\s+tap|1password|bitwarden|terminal)\b",
            re.IGNORECASE,
        ),
    ],
    "performance": [
        re.compile(
            r"\b(?:cpu|memory|ram|leak|battery|drain|sluggish|freeze|frozen|lagging|high\s+usage)\b",
            re.IGNORECASE,
        ),
    ],
    "feature request": [
        re.compile(
            r"\b(?:feature\s+request|can\s+you\s+add|please\s+add|would\s+love|suggestion|"
            r"custom\s+vocabulary|custom\s+dictionary|multilingual|offline\s+mode)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(?:support\s+for|when\s+will|roadmap)\b", re.IGNORECASE),
    ],
}

FRUSTRATION_PATTERNS = [
    re.compile(
        r"\b(?:broken|unbearable|terrible|asap|urgent|frustrated|furious|fails?\s+instantly|"
        r"what\s+is\s+going\s+on|blocked|cannot\s+work|useless|horrible)\b",
        re.IGNORECASE,
    ),
    re.compile(r"!{2,}"),
]

SATISFACTION_PATTERNS = [
    re.compile(
        r"\b(?:love\s+the\s+app|great\s+tool|amazing|kudos|thank\s+you|appreciate|helpful)\b",
        re.IGNORECASE,
    ),
]


def extract_error_signature(text: str) -> tuple[str | None, str | None]:
    """Check text for known high-value error signatures. Returns (signature, suggested_category)."""
    for sig_name, pattern, cat in ERROR_SIGNATURES:
        if pattern.search(text):
            return sig_name, cat
    return None, None


def classify_category(text: str) -> tuple[str, float, str]:
    """Determine ticket category and confidence via keyword scoring."""
    scores: dict[str, int] = {cat: 0 for cat in CATEGORIES}

    for cat, patterns in CATEGORY_PATTERNS.items():
        for p in patterns:
            matches = len(p.findall(text))
            scores[cat] += matches

    best_cat, best_score = max(scores.items(), key=lambda item: item[1])

    if best_score == 0:
        return "other", 0.40, "No strong category keywords matched"

    sorted_scores = sorted(scores.values(), reverse=True)
    runner_up = sorted_scores[1] if len(sorted_scores) > 1 else 0

    if best_score >= 3 and runner_up == 0:
        confidence = 0.95
    elif best_score >= 2 and best_score > runner_up * 1.5:
        confidence = 0.88
    elif best_score > runner_up:
        confidence = 0.72
    else:
        confidence = 0.55

    reason = (
        f"Keyword matching matched category '{best_cat}' with score {best_score} "
        f"(runner-up: {runner_up})"
    )
    return best_cat, confidence, reason


def determine_severity(
    category: str,
    text: str,
    plan_tier: str,
    error_sig: str | None,
) -> str:
    """Determine ticket severity level (P0 to P3)."""
    tier = (plan_tier or "free").lower()
    text_lower = text.lower()

    # P0: Systemic outages
    if error_sig == "No Model Available" or "no model available" in text_lower:
        return "P0"

    # Feature requests are always P3
    if category == "feature request":
        return "P3"

    # Inquiries or simple questions
    if category == "other" and any(k in text_lower for k in ("question", "dpa", "retention")):
        return "P3"

    # P1: Enterprise users experiencing complete blockage or paid billing lockouts
    if tier == "enterprise":
        if category in {"network/timeouts", "billing", "account/login"} or any(
            k in text_lower for k in ("cannot", "blocked")
        ):
            return "P1"

    if category == "billing" and any(k in text_lower for k in ("word limit", "paid", "stripe")):
        return "P1"

    if category == "account/login" and "captcha loop" in text_lower:
        return "P1" if tier in {"pro", "enterprise"} else "P2"

    if category == "network/timeouts":
        return "P1" if tier in {"pro", "enterprise"} else "P2"

    # Performance memory leak / high CPU
    if category == "performance":
        return "P2"

    # Audio/Mic & Text insertion issues typically have workarounds or affect specific hardware
    if category in {"audio/mic", "text insertion", "hotkeys"}:
        return "P2"

    return "P2" if tier in {"pro", "enterprise"} else "P3"


def detect_sentiment(text: str) -> str:
    """Detect customer sentiment based on affective terms."""
    frustrated_hits = sum(len(p.findall(text)) for p in FRUSTRATION_PATTERNS)
    satisfied_hits = sum(len(p.findall(text)) for p in SATISFACTION_PATTERNS)

    if frustrated_hits > satisfied_hits and frustrated_hits > 0:
        return "frustrated"
    if satisfied_hits > frustrated_hits and satisfied_hits > 0:
        return "satisfied"
    return "neutral"


def rules_triage(
    subject: str,
    body: str,
    plan_tier: str = "free",
    platform: str = "unknown",
) -> RuleTriageResult:
    """Run full deterministic rule-based triage on ticket text."""
    combined_text = f"{subject}\n{body}"

    # Step 1: Check known high-signal error signatures first
    sig, sig_cat = extract_error_signature(combined_text)

    # Step 2: Classify category
    if sig and sig_cat:
        category = sig_cat
        confidence = 0.95
        reason = f"High confidence: Exact signature detected '{sig}' pointing to '{sig_cat}'"
    else:
        cat_match, cat_conf, cat_reason = classify_category(combined_text)
        category = cat_match
        confidence = cat_conf
        reason = cat_reason

    # Step 3: Determine severity
    severity = determine_severity(category, combined_text, plan_tier, sig)

    # Step 4: Detect sentiment
    sentiment = detect_sentiment(combined_text)

    return RuleTriageResult(
        category=category,
        severity=severity,
        sentiment=sentiment,
        confidence=confidence,
        reason=reason,
        error_signature=sig,
    )
