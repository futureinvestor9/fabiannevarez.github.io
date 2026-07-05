"""B3 job/company diagnosis: the 10-question read on a JD, done before scoring."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from jobsearch import signals
from jobsearch.config import PROOF_POINTS, MESSAGING_BANK, BANNED_PHRASES
from jobsearch.scoring import Flags, detect_flags

SIGNAL_CHEATSHEET = [
    (["data hygiene", "clean up", "audit records", "data quality"],
     "the CRM data is dirty and leadership doesn't trust the numbers coming out of it"),
    (["build dashboard", "build reporting", "reporting from scratch"],
     "there's no real visibility today and decisions are being made on gut feel"),
    (["document our", "document the", "create sops", "sop", "playbook"],
     "process knowledge is stuck in people's heads, which is a real risk if they leave"),
    (["cross-functional", "work with sales and marketing", "work with sales, marketing"],
     "leads or data are leaking in the handoff between teams"),
    (["fast-paced", "wear many hats", "wear multiple hats"],
     "the ops function is understaffed and this is one of the first dedicated ops hires"),
    (["migration", "implementation", "rollout"],
     "the team is mid-migration or mid-rollout and needs hands, not just strategy"),
    (["lead routing", "follow-up", "follow up", "nurtur"],
     "the pipeline data exists but nobody trusts it, and follow-up depends on individual rep discipline instead of process"),
    (["first revops hire", "first rev ops hire", "first ops hire"],
     "this is founder-led chaos turning into a real function, with a lot of latitude and scope risk"),
]

ROLE_PROBLEM_BY_CATEGORY = {
    "crm": "Make CRM data trustworthy and follow-up consistent enough that reps and leadership both rely on it.",
    "revops": "Connect day-to-day sales activity to revenue outcomes and keep the pipeline numbers honest.",
    "process": "Turn scattered, undocumented workflows into a repeatable, documented process.",
    "data": "Build reporting that leadership actually trusts and uses to make decisions.",
    "stakeholder": "Act as the translator between reps/clients on one side and the data on the other.",
    "ai": "Use AI tools to speed up analysis without the team trusting output blindly.",
}

SUCCESS_90D_BY_CATEGORY = {
    "crm": "Core CRM objects cleaned up, obvious data-quality gaps closed, one cadence or routing rule shipped.",
    "revops": "A trusted activity-to-outcome view (dials/contacts/appointments/closings or equivalent) leadership can point to.",
    "process": "The messiest workflow mapped, staged, and documented well enough for someone else to run it.",
    "data": "One pipeline or ops report leadership actually opens and trusts.",
    "stakeholder": "Established working relationships with the cross-functional teams whose handoffs are leaking.",
    "ai": "A first AI-assisted analysis workflow shipped with a validation step, not just a demo.",
}

SUCCESS_6MO_BY_CATEGORY = {
    "crm": "Data hygiene maintained by process, not heroics; documented cadence rules in daily use.",
    "revops": "Follow-up SLAs and channel response rates measured and reviewed on a cadence.",
    "process": "A documented, repeatable operating process covering the function's core workflows.",
    "data": "Reporting infrastructure other teams build on, not just consume.",
    "stakeholder": "Cross-functional handoffs measurably tighter; fewer leads or records falling through gaps.",
    "ai": "AI-assisted analysis is a normal part of the workflow, always paired with a validation step.",
}

LANGUAGE_TO_AVOID_BASE = [
    "AI expert / AI specialist",
    "Salesforce Administrator (say: hands-on data quality and governance support)",
    "proficient in SQL/Python (say: working knowledge / exposure)",
    "RevOps leader / led revenue operations",
]


def _matched_struggles(jd_text: str) -> list[str]:
    text = jd_text.lower()
    hits = []
    for keywords, problem in SIGNAL_CHEATSHEET:
        if any(kw in text for kw in keywords):
            hits.append(problem)
    return hits


def _top_categories(jd_text: str, n: int = 3) -> list[str]:
    ranked = signals.ranked_dimensions(jd_text)
    seen = []
    for dim, _count in ranked:
        cat = signals.DIMENSION_TO_MESSAGING_CATEGORY[dim]
        if cat not in seen:
            seen.append(cat)
        if len(seen) >= n:
            break
    return seen


def _select_proof_points(top_categories: list[str], jd_text: str, max_points: int = 3) -> list[dict]:
    scored = []
    text = jd_text.lower()
    for pp in PROOF_POINTS:
        tag_overlap = sum(1 for t in pp["tags"] if t in top_categories)
        bonus = 1 if "story_fit" in pp["tags"] else 0
        # small bonus if the JD explicitly names Salesforce and this proof point covers it
        if "salesforce" in text and "credibility" in pp["tags"]:
            bonus += 2
        scored.append((tag_overlap + bonus, pp))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [pp for score, pp in scored[:max_points] if score > 0] or [scored[0][1]]


@dataclass
class Diagnosis:
    likely_struggle: str = ""
    role_problem: str = ""
    messy_systems: str = ""
    success_90d: str = ""
    success_6mo: str = ""
    matching_background: str = ""
    proof_points: list = field(default_factory=list)
    language_to_avoid: list = field(default_factory=list)
    value_prop_paragraph: str = ""
    recommendation: str = ""
    flags: list = field(default_factory=list)

    def to_row(self) -> dict:
        return {
            "likely_struggle": self.likely_struggle,
            "role_problem": self.role_problem,
            "messy_systems": self.messy_systems,
            "success_90d": self.success_90d,
            "success_6mo": self.success_6mo,
            "matching_background": self.matching_background,
            "proof_points": json.dumps([p["id"] for p in self.proof_points]),
            "language_to_avoid": json.dumps(self.language_to_avoid),
            "value_prop_paragraph": self.value_prop_paragraph,
            "recommendation": self.recommendation,
            "flags": json.dumps(self.flags),
        }


def diagnose(title: str, jd_text: str, flags: Flags | None = None) -> Diagnosis:
    jd_text = jd_text or ""
    if flags is None:
        flags = detect_flags(title, jd_text)

    top_cats = _top_categories(jd_text)
    top_cat = top_cats[0] if top_cats else "process"

    struggles = _matched_struggles(jd_text)
    likely_struggle = struggles[0] if struggles else (
        "the day-to-day operational process this role covers hasn't been made repeatable or measurable yet"
    )

    tools = signals.matched_tools(jd_text)
    messy_systems = (
        f"Likely messy/undocumented: {', '.join(tools)}." if tools
        else "Likely messy/undocumented: no specific tools named in the posting; assume ad hoc spreadsheets."
    )

    proof_points = _select_proof_points(top_cats, jd_text)
    matching_background = " ".join(pp["resume_phrasing"].strip() for pp in proof_points[:2])

    language_to_avoid = list(LANGUAGE_TO_AVOID_BASE)
    if flags.admin_cert_required:
        language_to_avoid.append(
            "Do not imply Salesforce Administrator certification/config skills — this posting requires it and I don't have it."
        )
    if flags.senior_scope:
        language_to_avoid.append(
            "Do not imply people-management or multi-year seniority — this posting reads senior/managerial."
        )

    top_proof = proof_points[0]
    value_prop_paragraph = (
        f"Postings like this usually mean the same thing: {likely_struggle}. "
        f"I've worked that problem directly: {top_proof['cover_letter_phrasing'].strip()}"
    )

    if flags.rcm_healthcare:
        recommendation = (
            "Skip — this reads as healthcare revenue-cycle/claims work (RCM), not RevOps. Domain mismatch per A4."
        )
    elif flags.admin_cert_required:
        recommendation = (
            "Tailored Apply at best — requires Salesforce Administrator certification I don't hold; "
            "downgrade expected once scored."
        )
    elif top_cat in ("crm", "revops") and "PIPELINE_LEAKAGE" in flags.as_list():
        recommendation = "Apply — this is the DTD4X/CRM-cadence sweet spot (pipeline leakage language detected)."
    else:
        recommendation = f"Apply if scored well — best matching category is '{top_cat}'."

    return Diagnosis(
        likely_struggle=likely_struggle,
        role_problem=ROLE_PROBLEM_BY_CATEGORY.get(top_cat, ROLE_PROBLEM_BY_CATEGORY["process"]),
        messy_systems=messy_systems,
        success_90d=SUCCESS_90D_BY_CATEGORY.get(top_cat, SUCCESS_90D_BY_CATEGORY["process"]),
        success_6mo=SUCCESS_6MO_BY_CATEGORY.get(top_cat, SUCCESS_6MO_BY_CATEGORY["process"]),
        matching_background=matching_background,
        proof_points=proof_points,
        language_to_avoid=language_to_avoid,
        value_prop_paragraph=value_prop_paragraph,
        recommendation=recommendation,
        flags=flags.as_list(),
    )
