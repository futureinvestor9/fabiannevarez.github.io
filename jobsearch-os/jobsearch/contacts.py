"""B5 contact selection + B6 four-touch outreach sequence generation."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from jobsearch.config import PROOF_POINTS, TOUCH_OFFSETS, RECRUITER_TOUCH_OFFSETS, CANDIDATE
from jobsearch.diagnosis import Diagnosis

CLASSIFICATION_PRIORITY = [
    "decision_maker", "same_role", "influencer", "recruiter",
    "adjacent", "referral_path", "low_priority",
]


def classification_rank(classification: str) -> int:
    try:
        return CLASSIFICATION_PRIORITY.index(classification)
    except ValueError:
        return len(CLASSIFICATION_PRIORITY)


# Section A15 message-to-audience mapping: which functional audience gets
# which proof-point flavor.
AUDIENCE_KEYWORDS = {
    "recruiter": ["recruiter", "talent acquisition", "sourcer"],
    "sales_ops": ["sales operations", "sales ops"],
    "revops": ["revenue operations", "revops"],
    "ops_ba": ["business analyst", "operations analyst", "business systems"],
    "crm_manager": ["crm", "salesforce", "marketing operations"],
    "alumni": [],  # set explicitly by caller, never inferred from title alone
}

AUDIENCE_TO_PROOF_TAG = {
    "crm_manager": "credibility",   # data-quality proof
    "sales_ops": "revops",           # activity-metrics proof (framed as sales-ops relevant)
    "revops": "crm",                 # DTD4X cadence proof
    "ops_ba": "process",             # decision-framework proof
    "other": "story_fit",
}


def infer_audience(title: str) -> str:
    text = (title or "").lower()
    for audience, keywords in AUDIENCE_KEYWORDS.items():
        if audience == "alumni":
            continue
        if any(kw in text for kw in keywords):
            return audience
    return "other"


def _proof_line(tag: str, diagnosis: Diagnosis | None) -> str:
    if diagnosis:
        match = next((pp for pp in diagnosis.proof_points if tag in pp["tags"]), None)
        if match:
            return match["dm_phrasing"].strip()
    match = next((pp for pp in PROOF_POINTS if tag in pp["tags"]), PROOF_POINTS[0])
    return match["dm_phrasing"].strip()


STANDARD_TEMPLATES = {
    1: {
        "channel": "linkedin_cr",
        "template_id": "t1_standard",
        "body": (
            "Hi {name} — I applied to {company}'s {role} and wanted to reach a person, "
            "not just the ATS. Quick relevant line: {proof_line} Would value connecting."
        ),
    },
    2: {
        "channel": "linkedin_msg",
        "template_id": "t2_standard",
        "body": (
            "Thanks for connecting, {name}. One reason I'm serious about this role: the "
            "posting reads like {problem}, and that's exactly the kind of problem I've "
            "worked: {proof_line} If a 10-minute chat ever makes sense, I'd value it. "
            "Either way, glad to be connected."
        ),
    },
    3: {
        "channel": "email",
        "template_id": "t3_standard",
        "body": (
            "Subject: {role} application — quick note from a candidate\n\n"
            "Hi {name}, I applied for {role} and reached out on LinkedIn — following up "
            "here in case that's easier. The short version: {problem} is the kind of "
            "problem I've actually worked: {proof_line} I'd welcome 10 minutes, but if the "
            "timing's wrong, no response needed — I'll assume it's not a fit for now.\n\n"
            "Thanks,\nFabian\n{email} · github.com/{github}"
        ),
    },
    4: {
        "channel": "linkedin_msg",
        "template_id": "t4_close",
        "body": (
            "Closing the loop — I'll stop here. If {role} or anything similar opens up "
            "where CRM operations / follow-up systems matter, I'd love to be considered. "
            "Thanks for the time either way."
        ),
    },
    "4_value_add": {
        "channel": "linkedin_msg",
        "template_id": "t4_value_add",
        "body": (
            "I wrote up how I'd approach the first 90 days of {problem}; sharing in case "
            "it's useful even if the role's filled: github.com/{github}"
        ),
    },
}

RECRUITER_TEMPLATES = {
    1: {
        "channel": "linkedin_cr",
        "template_id": "t1_recruiter",
        "body": (
            "Hi {name} — I'm targeting CRM Ops / Sales Ops / RevOps analyst roles in "
            "{location}. Quick background: {proof_line} If you're working on anything in "
            "that lane, I'd love to be on your radar. Happy to send a resume."
        ),
    },
    2: {
        "channel": "linkedin_msg",
        "template_id": "t2_recruiter",
        "body": (
            "Hi {name} — floating this back up in case it got buried. Still very "
            "interested in {role} or similar roles. If the timing's wrong, no problem at all."
        ),
    },
    3: {
        "channel": "email",
        "template_id": "t3_recruiter",
        "body": (
            "Subject: {role} — quick note from a candidate\n\n"
            "Hi {name}, following up on {role} at {company} — wanted to make sure this "
            "reached a person. {proof_line}\n\nThanks,\nFabian\n{email} · github.com/{github}"
        ),
    },
}

ALUMNI_T1 = {
    "channel": "linkedin_cr",
    "template_id": "t1_alumni",
    "body": (
        "Hi {name} — fellow UIUC econ grad here. I'm targeting analyst/RevOps roles in "
        "{location} and noticed you're at {company}. Would you be open to a quick "
        "informational chat about how the team there thinks about ops/analyst hiring? "
        "Happy to work around your schedule."
    ),
}


def generate_touch_drafts(
    contact: dict,
    job: dict,
    diagnosis: Diagnosis | None,
    audience: str | None = None,
    value_add_close: bool = False,
) -> list[dict]:
    """Return draft touch rows (touch_number, channel, draft_text, template_id,
    date_due, status='draft') for one contact, per the B6 sequence."""
    is_recruiter = contact.get("classification") == "recruiter"
    audience = audience or ("recruiter" if is_recruiter else infer_audience(contact.get("title", "")))
    proof_tag = AUDIENCE_TO_PROOF_TAG.get(audience, "story_fit")
    proof_line = _proof_line(proof_tag, diagnosis)
    problem = (diagnosis.likely_struggle if diagnosis else "the process this role covers isn't fully repeatable yet")

    first_name = contact["name"].split()[0] if contact.get("name") else ""
    fmt_kwargs = dict(
        name=first_name,
        company=job.get("company", ""),
        role=job.get("title", ""),
        proof_line=proof_line,
        problem=problem,
        email=CANDIDATE["fallback_email"],
        github=CANDIDATE["github"],
        location=CANDIDATE["location"],
    )

    today = dt.date.today()

    if audience == "alumni":
        templates = {1: ALUMNI_T1, 2: STANDARD_TEMPLATES[2], 3: STANDARD_TEMPLATES[3], 4: STANDARD_TEMPLATES[4]}
        offsets = TOUCH_OFFSETS
    elif is_recruiter:
        templates = RECRUITER_TEMPLATES
        offsets = RECRUITER_TOUCH_OFFSETS
    else:
        templates = dict(STANDARD_TEMPLATES)
        if value_add_close:
            templates[4] = templates["4_value_add"]
        offsets = TOUCH_OFFSETS

    drafts = []
    for touch_number, offset in zip(sorted(k for k in templates if isinstance(k, int)), offsets):
        tmpl = templates[touch_number]
        date_due = (today + dt.timedelta(days=offset)).isoformat()
        drafts.append({
            "touch_number": touch_number,
            "channel": tmpl["channel"],
            "template_id": tmpl["template_id"],
            "draft_text": tmpl["body"].format(**fmt_kwargs),
            "date_due": date_due,
            "status": "draft",
        })
    return drafts


def build_contact_research_checklist(company: str, title: str) -> list[str]:
    """B5: no LinkedIn scraping — a human-run 5-minute lookup checklist instead."""
    return [
        f'site:linkedin.com/in "{title}" "{company}"',
        f'site:linkedin.com/in "RevOps" "{company}"',
        f'site:linkedin.com/in "Sales Operations" "{company}"',
        f'site:linkedin.com/in "Recruiter" "{company}"',
        f'"{company}" LinkedIn People page, filter by department (Sales / RevOps / Operations)',
        f'site:linkedin.com/in "University of Illinois" "{company}"  (alumni / referral path)',
        "Email fallback (touch 3 only): use a company-published address, or the standard "
        "first.last@company-domain pattern — never spray guessed addresses at scale.",
    ]
