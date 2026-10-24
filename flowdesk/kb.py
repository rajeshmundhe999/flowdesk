"""Knowledge base indexer and matching engine."""

import re
from dataclasses import dataclass
from pathlib import Path

from flowdesk.config import settings


@dataclass
class KBArticle:
    id: str
    title: str
    filename: str
    symptom: str
    cause: str
    fix: str
    data_safety: str
    escalation_criteria: str
    raw_markdown: str


def parse_kb_markdown(file_path: Path) -> KBArticle:
    """Parse a knowledge base markdown file into structured fields."""
    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    title = file_path.stem.replace("_", " ").title()
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip().replace("Knowledge Base: ", "")
            break

    def extract_section(section_name: str) -> str:
        pattern = rf"##\s+{section_name}\s*\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""

    return KBArticle(
        id=file_path.stem,
        title=title,
        filename=file_path.name,
        symptom=extract_section("Symptom"),
        cause=extract_section("Cause"),
        fix=extract_section("Fix"),
        data_safety=extract_section("Data Safety"),
        escalation_criteria=extract_section("Escalation Criteria"),
        raw_markdown=content,
    )


def load_all_kb_articles(kb_dir: Path | None = None) -> list[KBArticle]:
    """Load all markdown articles from the docs/known_issues directory."""
    target_dir = kb_dir or settings.kb_dir
    if not target_dir.exists():
        return []

    articles: list[KBArticle] = []
    for md_file in target_dir.glob("*.md"):
        articles.append(parse_kb_markdown(md_file))
    return articles


KB_KEYWORD_MAP: list[tuple[str, list[str]]] = [
    (
        "net_connection_lost_vpn",
        ["connection lost", "vpn", "zscaler", "anyconnect", "proxy", "err_proxy", "err_tunnel"],
    ),
    (
        "net_timeout_taking_longer",
        ["taking longer than usual", "timeout", "latency", "spins", "hangs"],
    ),
    (
        "ai_no_model_available",
        ["no model available", "model", "routing", "transcription worker"],
    ),
    (
        "audio_missing_first_words",
        ["missing first words", "first word", "bluetooth", "airpods", "cut off", "first 2-3 words"],
    ),
    (
        "insertion_text_not_pasting",
        ["text not pasting", "accessibility", "paste", "keystroke injection failure"],
    ),
    (
        "hotkey_macos_secure_input",
        ["secure keyboard entry", "hotkey", "kcgerrorcannotcomplete", "terminal", "1password"],
    ),
    (
        "audio_mic_bluetooth_switching",
        ["hands-free ag", "mic switching", "device switching", "bluetooth headset mic", "audclnt"],
    ),
    (
        "auth_login_captcha_loop",
        ["captcha loop", "turnstile", "state_mismatch", "login loop", "redirect loop"],
    ),
    (
        "billing_word_limit_reset",
        ["word limit", "resetting", "stripe", "subscription renewed", "renewal", "paid tier"],
    ),
    (
        "insertion_non_qwerty_layout",
        ["azerty", "qwertz", "dvorak", "non-qwerty", "swapped"],
    ),
    (
        "android_work_profile_sandbox",
        ["android work profile", "knox", "intune", "managed profile", "audiorecord"],
    ),
]


def match_kb_article(
    text: str,
    kb_articles: list[KBArticle] | None = None,
) -> tuple[KBArticle | None, float]:
    """Match input text against known issues knowledge base.

    Returns (KBArticle, confidence_score).
    """
    articles = kb_articles if kb_articles is not None else load_all_kb_articles()
    if not articles:
        return None, 0.0

    article_by_id = {a.id: a for a in articles}
    text_lower = text.lower()

    best_article: KBArticle | None = None
    best_score = 0.0

    for doc_id, keywords in KB_KEYWORD_MAP:
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > 0:
            score = min(1.0, 0.4 + (matches * 0.15))
            if score > best_score and doc_id in article_by_id:
                best_score = score
                best_article = article_by_id[doc_id]

    return best_article, round(best_score, 2)
