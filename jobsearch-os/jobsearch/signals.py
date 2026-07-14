"""Shared keyword/regex signal detection used by both diagnosis.py and
scoring.py, so the two modules read the same evidence from a JD instead of
maintaining parallel keyword lists (see spec Section B3 signal cheat sheet
and Section B4 scoring dimensions).
"""
from __future__ import annotations

import re

# Maps each of the 7 content-scoring dimensions (B4 d1-d7) to keyword
# phrases. Word-boundary matched, case-insensitive, against the JD text.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "d1_crm": [
        "crm", "salesforce", "follow up boss", "follow-up boss", "hubspot",
        "pipeline hygiene", "lead nurtur", "cadence", "smart list",
        "data hygiene", "crm accuracy", "lead routing", "tagging", "redx",
        "database cadence", "contact record",
    ],
    "d2_revops": [
        "revenue operations", "revops", "sales operations", "sales ops",
        "funnel", "quota", "pipeline reporting", "go-to-market", "gtm",
        "forecast", "book of business", "territory",
    ],
    "d3_process": [
        "process improvement", "process mapping", "sop", "standard operating procedure",
        "documented process", "workflow", "optimize", "streamline", "playbook",
        "operating process", "document our", "document the", "as we scale",
    ],
    "d4_data": [
        "data quality", "data hygiene", "dashboard", "reporting", "excel",
        "google sheets", "spreadsheet", "pivot table", "kpi", "metrics",
        "analytics", "xlookup",
    ],
    "d5_ba": [
        "requirements gathering", "stakeholder interview", "business analyst",
        "business requirements", "user stories", "uat", "process documentation",
        "discovery", "gap analysis",
    ],
    "d6_stakeholder": [
        "cross-functional", "stakeholder", "client-facing", "training users",
        "communication skills", "collaborate", "customer success", "account manager",
    ],
    "d7_ai": [
        "\\bai\\b", "artificial intelligence", "chatgpt", "generative ai",
        "\\bllm\\b", "machine learning", "\\bgpt\\b", "copilot",
    ],
}

# Which messaging-bank / cover-letter-paragraph category each scoring
# dimension speaks to (content/messaging_bank.yaml, content/cover_letter_content.yaml).
DIMENSION_TO_MESSAGING_CATEGORY: dict[str, str] = {
    "d1_crm": "crm",
    "d2_revops": "revops",
    "d3_process": "process",
    "d4_data": "data",
    "d5_ba": "process",
    "d6_stakeholder": "stakeholder",
    "d7_ai": "ai",
}

TOOL_KEYWORDS = [
    "salesforce", "hubspot", "marketo", "follow up boss", "follow-up boss",
    "redx", "homebot", "excel", "google sheets", "tableau", "zendesk",
    "netsuite", "outreach.io", "outreach", "salesloft", "gainsight",
    "pipedrive", "asana", "jira", "zapier", "power bi", "looker",
]

INDUSTRY_ACCESSIBLE_KEYWORDS = [
    "real estate", "proptech", "saas", "b2b", "professional services",
    "technology", "startup", "e-commerce", "retail", "hospitality",
]

INDUSTRY_DEEP_DOMAIN_KEYWORDS = [
    "clinical", "actuarial", "biotech", "pharmaceutical", "legal counsel",
    "underwriting", "aerospace", "semiconductor", "genomics",
]

SENIOR_SCOPE_KEYWORDS = [
    "5+ years", "6+ years", "7+ years", "8+ years", "10+ years",
    "manage a team", "managing a team", "lead a team", "leading a team",
    "director of", "head of", "people management", "direct reports",
]

ADMIN_CERT_PATTERN = re.compile(
    r"salesforce\s+administrator.{0,40}\bcertif|certified\s+salesforce\s+administrator",
    re.IGNORECASE | re.DOTALL,
)

RCM_HEALTHCARE_KEYWORDS = [
    "claims", "billing", "medical", "healthcare", "patient", "icd-10",
    "cpt code", "hospital", "payer", "revenue cycle management", "hipaa",
    "insurance reimbursement", "denials",
]

PIPELINE_LEAKAGE_KEYWORDS = [
    "lead routing", "follow-up", "follow up", "nurtur", "leads going cold",
    "pipeline leakage", "response time", "lead response",
]


# Short tokens where an unbounded suffix genuinely risks a false hit
# ("excel" inside "excellent") get a strict trailing \b. Everything else
# is matched with only a leading \b so plurals/suffixes ("Smart Lists",
# "cross-functionally", "nurturing") still count, and multi-word phrases
# match across wrapped whitespace/newlines.
_STRICT_TRAILING_BOUNDARY = {"excel"}


def _word_pattern(phrase: str) -> re.Pattern:
    # Phrases already containing regex metacharacters (e.g. \b, \\bai\\b)
    # are used as-is.
    if "\\b" in phrase:
        return re.compile(phrase, re.IGNORECASE | re.DOTALL)
    escaped = r"\s+".join(re.escape(w) for w in phrase.split())
    if phrase.lower() in _STRICT_TRAILING_BOUNDARY:
        return re.compile(r"\b" + escaped + r"\b", re.IGNORECASE | re.DOTALL)
    return re.compile(r"\b" + escaped, re.IGNORECASE | re.DOTALL)


def count_matches(text: str, phrases: list[str]) -> int:
    return sum(1 for p in phrases if _word_pattern(p).search(text))


def any_match(text: str, phrases: list[str]) -> bool:
    return any(_word_pattern(p).search(text) for p in phrases)


def matched_tools(jd_text: str) -> list[str]:
    return [t for t in TOOL_KEYWORDS if _word_pattern(t).search(jd_text)]


def dimension_counts(jd_text: str) -> dict[str, int]:
    return {dim: count_matches(jd_text, kws) for dim, kws in CATEGORY_KEYWORDS.items()}


def ranked_dimensions(jd_text: str) -> list[tuple[str, int]]:
    counts = dimension_counts(jd_text)
    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)


def extract_years_required(jd_text: str) -> int | None:
    match = re.search(r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?years?", jd_text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None
