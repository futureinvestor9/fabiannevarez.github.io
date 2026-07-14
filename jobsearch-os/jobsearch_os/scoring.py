"""Deterministic scoring (Section K), fully driven by config/scoring_rules.yaml.
No model call. Missing-data defaults are mandated (neutral, not zero)."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from jobsearch_os.paths import CONFIG_DIR
from jobsearch_os.normalize import _normalize_text


def load_rules(path: Path | None = None) -> dict:
    p = path or (CONFIG_DIR / "scoring_rules.yaml")
    return yaml.safe_load(p.read_text(encoding="utf-8"))


@dataclass
class ScoreResult:
    components: dict = field(default_factory=dict)
    total: float = 0.0
    band: str = "skip"
    action: str = ""
    matched_skills: list = field(default_factory=list)
    missing_requirements: list = field(default_factory=list)
    risk_flags: list = field(default_factory=list)
    scoring_version: str = ""


def _title_role_fit(title: str, rules: dict) -> tuple[float, str]:
    t = _normalize_text(title)
    pts = rules["role_fit_points"]
    for target in rules["target_titles"]:
        if _normalize_text(target) in t:
            return pts["exact_target"], "exact_target"
    for _canon, aliases in (rules.get("target_title_aliases") or {}).items():
        for a in aliases:
            if _normalize_text(a) in t:
                return pts["alias_target"], "alias_target"
    for adj in rules.get("adjacent_titles", []):
        if _normalize_text(adj) in t:
            return pts["adjacent"], "adjacent"
    return pts["none"], "none"


def _requirements(haystack: str, rules: dict) -> tuple[float, list[str], list[str]]:
    matched: list[str] = []
    for category, aliases in rules["supported_skills"].items():
        if any(_normalize_text(a) in haystack for a in aliases):
            matched.append(category)
    missing: list[str] = [
        s for s in rules["overreach_skills"] if _normalize_text(s) in haystack
    ]
    rp = rules["requirements_points"]
    pts = min(len(matched) * rp["per_supported_hit"], rp["max_supported"])
    return pts, matched, missing


def _evidence_strength(n_matched: int, rules: dict) -> tuple[float, str]:
    ep = rules["evidence_points"]
    if n_matched >= 2:
        return ep["direct"], "direct"
    if n_matched == 1:
        return ep["reasonable_inference"], "reasonable_inference"
    return ep["unsupported"], "unsupported"


def _industry(haystack: str, rules: dict) -> float:
    ip = rules["industry_points"]
    if any(_normalize_text(k) in haystack for k in rules["industry_deep_domain"]):
        return ip["deep_domain"]
    if any(_normalize_text(k) in haystack for k in rules["industry_accessible"]):
        return ip["accessible"]
    return ip["neutral"]


def _salary_location(salary_text: str, location: str, rules: dict) -> tuple[float, list[str]]:
    sl = rules["salary_location"]
    flags: list[str] = []
    # Unknown salary -> neutral points (mandated: not zero); otherwise base.
    if (salary_text or "").strip():
        pts = sl["base_points"]
    else:
        pts = sl["unknown_salary_points"]
        flags.append("salary_unknown")
    loc = _normalize_text(location)
    if "chicago" in loc or "remote" in loc:
        pts = min(pts + sl["chicago_or_remote_bonus"], rules["components"]["salary_location_fit"])
    return pts, flags


def _freshness(posted_date: str, rules: dict, today: dt.date) -> tuple[float, list[str]]:
    if not (posted_date or "").strip():
        return rules["missing_posted_date_points"], ["posted_date_missing"]
    try:
        d = dt.date.fromisoformat(posted_date[:10])
    except ValueError:
        return rules["missing_posted_date_points"], ["posted_date_unparseable"]
    age = (today - d).days
    for bracket in rules["freshness_brackets"]:
        if age <= bracket["max_age_days"]:
            return bracket["points"], []
    return rules["freshness_brackets"][-1]["points"], []


def score_job(
    version: dict,
    rules: dict,
    has_contact: bool = False,
    today: dt.date | None = None,
) -> ScoreResult:
    today = today or dt.date.today()
    haystack = _normalize_text(
        " ".join(str(version.get(k, "")) for k in ("title", "description"))
        + " " + " ".join(version.get("requirements") or [])
    )

    role_pts, role_kind = _title_role_fit(version.get("title", ""), rules)
    req_pts, matched, missing = _requirements(haystack, rules)
    ev_pts, ev_kind = _evidence_strength(len(matched), rules)
    ind_pts = _industry(haystack, rules)
    sal_pts, sal_flags = _salary_location(version.get("salary_text", ""), version.get("location", ""), rules)
    fresh_pts, fresh_flags = _freshness(version.get("posted_date", ""), rules, today)
    out_pts = rules["outreach"]["with_contact_points"] if has_contact else rules["outreach"]["no_contact_points"]

    components = {
        "role_fit": role_pts,
        "requirements_match": req_pts,
        "evidence_strength": ev_pts,
        "industry_fit": ind_pts,
        "salary_location_fit": sal_pts,
        "freshness": fresh_pts,
        "outreach_potential": out_pts,
    }
    total = round(sum(components.values()), 1)

    band, action = "skip", ""
    for b in rules["decision_bands"]:
        if b["min"] <= total <= b["max"]:
            band, action = b["label"], b["action"]
            break

    risk_flags = list(sal_flags) + list(fresh_flags)
    if role_kind == "none":
        risk_flags.append("title_not_a_target_role")
    if missing:
        risk_flags.append("missing_requirements:" + ",".join(missing))
    if ev_kind == "unsupported":
        risk_flags.append("no_supported_evidence_match")

    return ScoreResult(
        components=components,
        total=total,
        band=band,
        action=action,
        matched_skills=matched,
        missing_requirements=missing,
        risk_flags=risk_flags,
        scoring_version=rules["scoring_version"],
    )
