"""Deterministic, versioned dedupe (Section K).

Order: 1) exact canonical URL  2) same ATS job id  3) exact description hash
4) same company/title/location + token-set Jaccard >= threshold.

Never deletes a duplicate; the caller links it to the canonical record.
"""
from __future__ import annotations

import re
import sqlite3

from jobsearch_os.normalize import _normalize_text

_BOILERPLATE = re.compile(
    r"\b(equal opportunity employer|eoe|we are committed|apply now|about us|"
    r"benefits include|competitive salary)\b",
    re.IGNORECASE,
)


def _tokens(text: str) -> set[str]:
    cleaned = _BOILERPLATE.sub(" ", text or "")
    return set(_normalize_text(cleaned).split())


def jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def find_duplicate(
    conn: sqlite3.Connection,
    canonical_url: str,
    ats_job_id: str | None,
    description_hash: str,
    company: str,
    title: str,
    location: str,
    description: str,
    threshold: float,
) -> tuple[int | None, str | None]:
    """Return (canonical_job_id, match_reason) or (None, None). Compares against
    the CURRENT version of existing non-duplicate jobs."""
    # 1) exact canonical URL
    if canonical_url:
        row = conn.execute(
            "SELECT job_id FROM jobs WHERE canonical_url = ? AND dedupe_of IS NULL LIMIT 1",
            (canonical_url,),
        ).fetchone()
        if row:
            return row["job_id"], "canonical_url"
    # 2) same ATS job id
    if ats_job_id:
        row = conn.execute(
            "SELECT job_id FROM jobs WHERE ats_job_id = ? AND dedupe_of IS NULL LIMIT 1",
            (ats_job_id,),
        ).fetchone()
        if row:
            return row["job_id"], "ats_job_id"
    # 3) exact description hash
    if description_hash:
        row = conn.execute(
            "SELECT job_id FROM jobs WHERE description_hash = ? AND dedupe_of IS NULL LIMIT 1",
            (description_hash,),
        ).fetchone()
        if row:
            return row["job_id"], "description_hash"
    # 4) same company/title/location + Jaccard similarity
    norm_company = _normalize_text(company)
    norm_title = _normalize_text(title)
    norm_location = _normalize_text(location)
    candidates = conn.execute(
        "SELECT j.job_id, v.company, v.title, v.location, v.description "
        "FROM jobs j JOIN job_versions v ON v.version_id = j.current_version_id "
        "WHERE j.dedupe_of IS NULL"
    ).fetchall()
    for c in candidates:
        if (_normalize_text(c["company"]) == norm_company
                and _normalize_text(c["title"]) == norm_title
                and _normalize_text(c["location"] or "") == norm_location):
            if jaccard(description, c["description"] or "") >= threshold:
                return c["job_id"], "similarity"
    return None, None
