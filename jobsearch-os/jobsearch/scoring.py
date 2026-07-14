"""B4 job-fit scoring model: 12 weighted dimensions -> 0-100 total + category."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from jobsearch import signals
from jobsearch.config import WEIGHTS, CATEGORY_THRESHOLDS, RESEARCH_WINDOW_DAYS

CANDIDATE_KNOWN_TOOLS = [
    "salesforce", "follow up boss", "follow-up boss", "redx", "homebot",
    "excel", "google sheets",
]

TIER_ORDER = ["skip", "research", "tailored", "strong"]


def _count_to_score(count: int) -> float:
    if count <= 0:
        return 3.0
    if count == 1:
        return 7.0
    if count == 2:
        return 9.0
    return 10.0


@dataclass
class Flags:
    pipeline_leakage: bool = False
    rcm_healthcare: bool = False
    admin_cert_required: bool = False
    senior_scope: bool = False

    def as_list(self) -> list[str]:
        names = []
        if self.pipeline_leakage:
            names.append("PIPELINE_LEAKAGE")
        if self.rcm_healthcare:
            names.append("RCM_HEALTHCARE")
        if self.admin_cert_required:
            names.append("ADMIN_CERT_REQUIRED")
        if self.senior_scope:
            names.append("SENIOR_SCOPE")
        return names


def detect_flags(title: str, jd_text: str) -> Flags:
    text = jd_text or ""
    years = signals.extract_years_required(text)
    return Flags(
        pipeline_leakage=signals.any_match(text, signals.PIPELINE_LEAKAGE_KEYWORDS),
        rcm_healthcare=(
            "revenue cycle" in (title or "").lower()
            and signals.any_match(text, signals.RCM_HEALTHCARE_KEYWORDS)
        ),
        admin_cert_required=bool(signals.ADMIN_CERT_PATTERN.search(text)),
        senior_scope=(
            signals.any_match(text, signals.SENIOR_SCOPE_KEYWORDS)
            or (years is not None and years >= 5)
        ),
    )


@dataclass
class ScoreResult:
    dims: dict = field(default_factory=dict)
    raw_total: float = 0.0
    total: float = 0.0
    raw_category: str = "skip"
    category: str = "skip"
    downgrade_reasons: list = field(default_factory=list)
    research_deadline: str | None = None
    flags: list = field(default_factory=list)


def _experience_score(jd_text: str, senior_scope: bool) -> float:
    years = signals.extract_years_required(jd_text)
    if senior_scope:
        return 3.0
    if years is None:
        return 8.0
    if years <= 3:
        return 10.0
    if years <= 5:
        return 6.0
    return 2.0


def _technical_score(jd_text: str, admin_cert_required: bool) -> float:
    heavy_tools = [
        "tableau", "power bi", "looker", "\\bpython\\b", "sql server",
        "advanced sql", "\\betl\\b", "data warehouse", "snowflake",
    ]
    heavy_count = signals.count_matches(jd_text, heavy_tools)
    score = 10.0 - min(heavy_count * 2, 6)
    if admin_cert_required:
        score = min(score, 3.0)
    return score


def _industry_score(jd_text: str) -> float:
    accessible = signals.any_match(jd_text, signals.INDUSTRY_ACCESSIBLE_KEYWORDS)
    deep = signals.any_match(jd_text, signals.INDUSTRY_DEEP_DOMAIN_KEYWORDS)
    if deep:
        return 2.0
    if accessible:
        return 10.0
    return 6.0


def _credibility_score(admin_cert_required: bool, senior_scope: bool) -> float:
    score = 9.0
    if admin_cert_required:
        score = 4.0
    if senior_scope:
        score = min(score, 5.0)
    return score


def _story_fit_score(jd_text: str, pipeline_leakage: bool) -> float:
    matched_known = sum(
        1 for t in CANDIDATE_KNOWN_TOOLS if signals.count_matches(jd_text, [t]) > 0
    )
    score = 5.0 + min(matched_known, 4)
    if pipeline_leakage:
        score += 1
    return min(score, 10.0)


def _category_for_total(total: float) -> str:
    for name in ("strong", "tailored", "research", "skip"):
        bounds = CATEGORY_THRESHOLDS[name]
        if bounds["min"] <= total <= bounds["max"]:
            return name
    return "skip"


def compute_score(title: str, jd_text: str, flags: Flags | None = None) -> ScoreResult:
    jd_text = jd_text or ""
    if flags is None:
        flags = detect_flags(title, jd_text)

    dim_counts = signals.dimension_counts(jd_text)
    dims = {
        "d1": _count_to_score(dim_counts["d1_crm"]),
        "d2": _count_to_score(dim_counts["d2_revops"]),
        "d3": _count_to_score(dim_counts["d3_process"]),
        "d4": _count_to_score(dim_counts["d4_data"]),
        "d5": _count_to_score(dim_counts["d5_ba"]),
        "d6": _count_to_score(dim_counts["d6_stakeholder"]),
        "d7": _count_to_score(dim_counts["d7_ai"]),
        "d8": _experience_score(jd_text, flags.senior_scope),
        "d9": _technical_score(jd_text, flags.admin_cert_required),
        "d10": _industry_score(jd_text),
        "d11": _credibility_score(flags.admin_cert_required, flags.senior_scope),
        "d12": _story_fit_score(jd_text, flags.pipeline_leakage),
    }

    weight_keys = [
        "d1_crm_ops", "d2_revenue_sales_ops", "d3_workflow_process",
        "d4_data_quality_reporting", "d5_business_analysis",
        "d6_stakeholder_communication", "d7_ai_systems_thinking",
        "d8_experience_level_accessibility", "d9_technical_requirements_accessibility",
        "d10_industry_accessibility", "d11_credible_positioning_likelihood",
        "d12_story_fit",
    ]
    dim_keys = [f"d{i}" for i in range(1, 13)]
    weight_sum = sum(WEIGHTS[wk] for wk in weight_keys)
    raw_weighted_sum = sum(dims[dk] * WEIGHTS[wk] for dk, wk in zip(dim_keys, weight_keys))
    # Normalize to a 0-100 scale regardless of how the weights sum (see the
    # note in config.yaml about the spec's own arithmetic inconsistency).
    total = round(raw_weighted_sum / weight_sum * 10, 1)

    raw_category = _category_for_total(total)
    category = raw_category
    reasons: list[str] = []

    if flags.admin_cert_required:
        idx = max(0, TIER_ORDER.index(category) - 1)
        category = TIER_ORDER[idx]
        reasons.append(
            "ADMIN_CERT_REQUIRED: downgraded one tier — role requires Salesforce "
            "Administrator certification, which cannot be honestly claimed."
        )

    if flags.senior_scope and total < 85:
        idx = max(0, TIER_ORDER.index(category) - 1)
        category = TIER_ORDER[idx]
        reasons.append(
            "SENIOR_SCOPE: downgraded one tier — role scope reads senior/managerial "
            "and total score is below the 85 exception threshold."
        )

    if flags.rcm_healthcare:
        category = "skip"
        reasons = [
            "RCM_HEALTHCARE: domain mismatch — 'Revenue Cycle' + healthcare "
            "billing/claims language means this is RCM, not RevOps. Auto-skip per A4."
        ]

    research_deadline = None
    if category == "research":
        research_deadline = (dt.date.today() + dt.timedelta(days=RESEARCH_WINDOW_DAYS)).isoformat()

    return ScoreResult(
        dims=dims,
        raw_total=round(raw_weighted_sum, 1),
        total=total,
        raw_category=raw_category,
        category=category,
        downgrade_reasons=reasons,
        research_deadline=research_deadline,
        flags=flags.as_list(),
    )
