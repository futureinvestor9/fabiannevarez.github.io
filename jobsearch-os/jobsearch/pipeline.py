"""Orchestrates the B14 pipeline: ingest -> diagnose -> score -> route ->
(cover letter + contact checklist) -> approval queue -> touches -> metrics.

Every function here takes a live sqlite3.Connection so callers (CLI,
dashboard, tests) share one connection/transaction model. Nothing in this
module ever sends an email, posts to LinkedIn, or calls a browser — see the
NON-GOALS in the spec's Section B14 and the acceptance test that greps for
that.
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3

from jobsearch.coverletter import generate_cover_letter
from jobsearch.diagnosis import Diagnosis, diagnose
from jobsearch.contacts import (
    build_contact_research_checklist,
    generate_touch_drafts,
    classification_rank,
)
from jobsearch.scoring import compute_score, detect_flags


def ingest_job(
    conn: sqlite3.Connection,
    company: str,
    title: str,
    jd_text: str,
    url: str = "",
    location: str = "",
    comp_range: str = "",
    source: str = "manual",
) -> int:
    cur = conn.execute(
        "INSERT INTO jobs (company, title, url, location, comp_range, jd_text, source, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'new')",
        (company, title, url, location, comp_range, jd_text, source),
    )
    conn.commit()
    return cur.lastrowid


def find_recent_duplicate(conn: sqlite3.Connection, company: str, title: str, within_days: int = 30) -> int | None:
    """B11 duplicate detection: same company+title within 30 days -> merge
    (i.e. don't re-ingest). Case-insensitive match; returns the existing
    job_id if found."""
    row = conn.execute(
        "SELECT job_id FROM jobs WHERE lower(company)=lower(?) AND lower(title)=lower(?) "
        "AND date_found >= date('now', ?) ORDER BY job_id DESC LIMIT 1",
        (company, title, f"-{within_days} days"),
    ).fetchone()
    return row["job_id"] if row else None


def ingest_batch(conn: sqlite3.Connection, rows: list[dict], source: str = "batch") -> dict:
    """Ingest many postings at once. Each row needs at least company, title,
    jd_text; url/location/comp optional. Skips duplicates per B11 and never
    guesses a diagnosis on an empty JD (B11 error handling).

    Returns {"ingested": [job_ids], "duplicates": [...], "malformed": [...]}.
    """
    result = {"ingested": [], "duplicates": [], "malformed": []}
    for i, r in enumerate(rows):
        company = (r.get("company") or "").strip()
        title = (r.get("title") or "").strip()
        jd_text = (r.get("jd_text") or "").strip()
        if not company or not title or len(jd_text) < 30:
            result["malformed"].append({"row": i + 1, "company": company, "title": title,
                                         "reason": "missing company/title or JD too short (<30 chars)"})
            continue
        dup = find_recent_duplicate(conn, company, title)
        if dup:
            result["duplicates"].append({"row": i + 1, "company": company, "title": title, "existing_job_id": dup})
            continue
        job_id = ingest_job(conn, company=company, title=title, jd_text=jd_text,
                            url=(r.get("url") or "").strip(), location=(r.get("location") or "").strip(),
                            comp_range=(r.get("comp_range") or r.get("comp") or "").strip(), source=source)
        result["ingested"].append(job_id)
    return result


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def get_job(conn: sqlite3.Connection, job_id: int) -> dict:
    row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    if row is None:
        raise ValueError(f"No job with id {job_id}")
    return _row_to_dict(row)


def process_job(conn: sqlite3.Connection, job_id: int) -> dict:
    """Runs diagnosis + scoring + routing for one job. Idempotent-ish: re-running
    inserts fresh diagnosis/score rows (history is kept, not overwritten)."""
    job = get_job(conn, job_id)
    flags = detect_flags(job["title"], job["jd_text"])
    diag = diagnose(job["title"], job["jd_text"], flags=flags)
    score = compute_score(job["title"], job["jd_text"], flags=flags)

    conn.execute(
        "INSERT INTO diagnoses (job_id, likely_struggle, role_problem, messy_systems, "
        "success_90d, success_6mo, matching_background, proof_points, language_to_avoid, "
        "value_prop_paragraph, recommendation, flags) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            job_id,
            diag.likely_struggle,
            diag.role_problem,
            diag.messy_systems,
            diag.success_90d,
            diag.success_6mo,
            diag.matching_background,
            json.dumps([p["id"] for p in diag.proof_points]),
            json.dumps(diag.language_to_avoid),
            diag.value_prop_paragraph,
            diag.recommendation,
            json.dumps(diag.flags),
        ),
    )

    conn.execute(
        "INSERT INTO scores (job_id, d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12, total, "
        "category, raw_category, downgrade_reason, research_deadline) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            job_id,
            score.dims["d1"], score.dims["d2"], score.dims["d3"], score.dims["d4"],
            score.dims["d5"], score.dims["d6"], score.dims["d7"], score.dims["d8"],
            score.dims["d9"], score.dims["d10"], score.dims["d11"], score.dims["d12"],
            score.total, score.category, score.raw_category,
            "; ".join(score.downgrade_reasons) if score.downgrade_reasons else None,
            score.research_deadline,
        ),
    )

    if score.category == "skip":
        reason = "; ".join(score.downgrade_reasons) if score.downgrade_reasons else (
            f"Scored {score.total} (below 50 threshold)."
        )
        conn.execute(
            "UPDATE jobs SET status='skipped', skip_reason=? WHERE job_id=?",
            (reason, job_id),
        )
        conn.commit()
        return {"job_id": job_id, "diagnosis": diag, "score": score, "cover_letter": None}

    conn.execute("UPDATE jobs SET status='scored' WHERE job_id=?", (job_id,))

    cover_letter_row = None
    if score.category in ("strong", "tailored"):
        existing = {
            r["opening_sentence"]
            for r in conn.execute("SELECT opening_sentence FROM cover_letters").fetchall()
        }
        letter = generate_cover_letter(job["company"], job["title"], diag, job["jd_text"], existing)
        cur = conn.execute(
            "INSERT INTO cover_letters (job_id, opening_sentence, body, pasted_version, approved) "
            "VALUES (?,?,?,?,0)",
            (job_id, letter.opening_sentence, letter.body, letter.pasted_version),
        )
        cover_letter_row = {"cover_letter_id": cur.lastrowid, **letter.__dict__}

    conn.commit()
    return {"job_id": job_id, "diagnosis": diag, "score": score, "cover_letter": cover_letter_row}


def research_checklist_for_job(conn: sqlite3.Connection, job_id: int) -> list[str]:
    job = get_job(conn, job_id)
    return build_contact_research_checklist(job["company"], job["title"])


def _latest_diagnosis(conn: sqlite3.Connection, job_id: int) -> Diagnosis | None:
    row = conn.execute(
        "SELECT * FROM diagnoses WHERE job_id=? ORDER BY diagnosis_id DESC LIMIT 1", (job_id,)
    ).fetchone()
    if row is None:
        return None
    from jobsearch.config import PROOF_POINTS
    pp_ids = json.loads(row["proof_points"] or "[]")
    proof_points = [pp for pp in PROOF_POINTS if pp["id"] in pp_ids]
    return Diagnosis(
        likely_struggle=row["likely_struggle"],
        role_problem=row["role_problem"],
        messy_systems=row["messy_systems"],
        success_90d=row["success_90d"],
        success_6mo=row["success_6mo"],
        matching_background=row["matching_background"],
        proof_points=proof_points,
        language_to_avoid=json.loads(row["language_to_avoid"] or "[]"),
        value_prop_paragraph=row["value_prop_paragraph"],
        recommendation=row["recommendation"],
        flags=json.loads(row["flags"] or "[]"),
    )


def add_contact(
    conn: sqlite3.Connection,
    job_id: int,
    name: str,
    title: str,
    linkedin_url: str = "",
    email: str = "",
    email_source: str | None = None,
    classification: str = "influencer",
    why_selected: str = "",
    audience: str | None = None,
) -> int:
    job = get_job(conn, job_id)
    diag = _latest_diagnosis(conn, job_id)

    cur = conn.execute(
        "INSERT INTO contacts (job_id, company, name, title, linkedin_url, email, "
        "email_source, classification, why_selected, status) "
        "VALUES (?,?,?,?,?,?,?,?,?, 'active')",
        (job_id, job["company"], name, title, linkedin_url, email, email_source, classification, why_selected),
    )
    contact_id = cur.lastrowid

    resolved_audience = audience or ("recruiter" if classification == "recruiter" else None)
    drafts = generate_touch_drafts({"name": name, "title": title, "classification": classification},
                                    job, diag, audience=audience)
    for d in drafts:
        conn.execute(
            "INSERT INTO touches (contact_id, touch_number, channel, draft_text, template_id, "
            "status, date_due) VALUES (?,?,?,?,?,?,?)",
            (contact_id, d["touch_number"], d["channel"], d["draft_text"], d["template_id"],
             d["status"], d["date_due"]),
        )
        _record_template_use(conn, d["template_id"], d["touch_number"], resolved_audience or "general")
    conn.commit()
    return contact_id


def _record_template_use(conn: sqlite3.Connection, template_id: str, touch_number: int, audience_class: str) -> None:
    row = conn.execute("SELECT template_id FROM templates WHERE template_id=?", (template_id,)).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO templates (template_id, touch_number, audience_class, times_used, responses) "
            "VALUES (?,?,?,1,0)",
            (template_id, touch_number, audience_class),
        )
    else:
        conn.execute("UPDATE templates SET times_used = times_used + 1 WHERE template_id=?", (template_id,))


def approve_touch(conn: sqlite3.Connection, touch_id: int, edited_text: str | None = None) -> None:
    if edited_text:
        conn.execute("UPDATE touches SET status='approved', draft_text=? WHERE touch_id=?",
                     (edited_text, touch_id))
    else:
        conn.execute("UPDATE touches SET status='approved' WHERE touch_id=?", (touch_id,))
    conn.commit()


def skip_touch(conn: sqlite3.Connection, touch_id: int) -> None:
    conn.execute("UPDATE touches SET status='skipped' WHERE touch_id=?", (touch_id,))
    conn.commit()


def mark_touch_sent(conn: sqlite3.Connection, touch_id: int) -> None:
    conn.execute(
        "UPDATE touches SET status='sent', date_sent=? WHERE touch_id=?",
        (dt.date.today().isoformat(), touch_id),
    )
    conn.commit()


def log_response(conn: sqlite3.Connection, touch_id: int, summary: str) -> None:
    """A response pauses the rest of that contact's sequence (B6 sequence rules)."""
    row = conn.execute(
        "SELECT contact_id, template_id FROM touches WHERE touch_id=?", (touch_id,)
    ).fetchone()
    conn.execute(
        "UPDATE touches SET status='responded', response_summary=?, date_responded=? WHERE touch_id=?",
        (summary, dt.date.today().isoformat(), touch_id),
    )
    if row and row["template_id"]:
        conn.execute(
            "UPDATE templates SET responses = responses + 1 WHERE template_id=?",
            (row["template_id"],),
        )
    if row:
        conn.execute(
            "UPDATE touches SET status='closed' WHERE contact_id=? AND status IN ('draft','approved')",
            (row["contact_id"],),
        )
        conn.execute("UPDATE contacts SET status='responded' WHERE contact_id=?", (row["contact_id"],))
    conn.commit()


def approve_cover_letter(conn: sqlite3.Connection, cover_letter_id: int, edited_body: str | None = None) -> None:
    if edited_body:
        conn.execute("UPDATE cover_letters SET approved=1, body=? WHERE cover_letter_id=?",
                     (edited_body, cover_letter_id))
    else:
        conn.execute("UPDATE cover_letters SET approved=1 WHERE cover_letter_id=?", (cover_letter_id,))
    conn.commit()


def mark_applied(conn: sqlite3.Connection, job_id: int, method: str = "ATS",
                  resume_version: str = "", cover_letter_file: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO applications (job_id, method, resume_version, cover_letter_file, status) "
        "VALUES (?,?,?,?, 'submitted')",
        (job_id, method, resume_version, cover_letter_file),
    )
    conn.execute("UPDATE jobs SET status='applied' WHERE job_id=?", (job_id,))
    conn.commit()
    return cur.lastrowid


def skip_job(conn: sqlite3.Connection, job_id: int, reason: str) -> None:
    conn.execute("UPDATE jobs SET status='skipped', skip_reason=? WHERE job_id=?", (reason, job_id))
    conn.commit()


# --- B8/B9 queue + metrics queries --------------------------------------

def due_today(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT t.*, c.name AS contact_name, c.company AS company, c.classification "
        "FROM touches t JOIN contacts c ON c.contact_id = t.contact_id "
        "WHERE t.status='approved' AND t.date_due <= date('now')"
    ).fetchall()
    dicts = [_row_to_dict(r) for r in rows]
    dicts.sort(key=lambda r: (r["date_due"], classification_rank(r["classification"])))
    return dicts


def approval_queue(conn: sqlite3.Connection) -> dict:
    touches = conn.execute(
        "SELECT t.*, c.name AS contact_name, c.company AS company, c.classification "
        "FROM touches t JOIN contacts c ON c.contact_id = t.contact_id WHERE t.status='draft'"
    ).fetchall()
    touches = [_row_to_dict(r) for r in touches]
    touches.sort(key=lambda r: (r["date_due"], classification_rank(r["classification"])))
    letters = conn.execute(
        "SELECT cl.*, j.company AS company, j.title AS title FROM cover_letters cl "
        "JOIN jobs j ON j.job_id = cl.job_id WHERE cl.approved=0"
    ).fetchall()
    return {
        "touches": touches,
        "cover_letters": [_row_to_dict(r) for r in letters],
    }


def new_jobs_today(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT j.*, s.total, s.category FROM jobs j "
        "LEFT JOIN scores s ON s.job_id = j.job_id "
        "WHERE j.date_found = date('now') ORDER BY j.job_id DESC"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def apply_queue(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT j.*, s.total, s.category, "
        "CAST(julianday('now') - julianday(j.date_found) AS INTEGER) AS age_days "
        "FROM jobs j JOIN scores s ON s.job_id = j.job_id "
        "WHERE j.status='scored' AND s.category IN ('strong','tailored') "
        "ORDER BY s.total DESC"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def responses(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT t.*, c.name AS contact_name, c.company AS company FROM touches t "
        "JOIN contacts c ON c.contact_id = t.contact_id WHERE t.status='responded' "
        "ORDER BY t.date_sent DESC"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def stale_applications(conn: sqlite3.Connection) -> list[dict]:
    from jobsearch.config import STALE_AFTER_DAYS
    rows = conn.execute(
        "SELECT a.*, j.company AS company, j.title AS title, "
        "CAST(julianday('now') - julianday(a.date_applied) AS INTEGER) AS age_days "
        "FROM applications a JOIN jobs j ON j.job_id = a.job_id "
        "WHERE a.status='submitted' "
        "AND CAST(julianday('now') - julianday(a.date_applied) AS INTEGER) >= ? "
        "ORDER BY age_days DESC",
        (STALE_AFTER_DAYS,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def research_timers(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT j.job_id, j.company, j.title, s.total, s.research_deadline, "
        "CAST(julianday(s.research_deadline) - julianday('now') AS INTEGER) AS days_left "
        "FROM jobs j JOIN scores s ON s.job_id = j.job_id "
        "WHERE s.category='research' ORDER BY days_left"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def skipped_today(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT job_id, company, title, skip_reason FROM jobs "
        "WHERE status='skipped' AND date_found = date('now')"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def top_open_opportunities(conn: sqlite3.Connection, limit: int = 5) -> list[dict]:
    rows = conn.execute(
        "SELECT j.job_id, j.company, j.title, s.total, s.category, j.date_found FROM jobs j "
        "JOIN scores s ON s.job_id = j.job_id "
        "WHERE j.status IN ('scored','applied') AND s.category IN ('strong','tailored') "
        "ORDER BY s.total DESC, j.date_found DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]
