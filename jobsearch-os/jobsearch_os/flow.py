"""Job flow driver: normalize -> dedupe -> scored, each transition validated
against the state machine and written with its event in the SAME transaction
(Section I atomic state+event; Section J transitions)."""
from __future__ import annotations

import json
import sqlite3

from jobsearch_os import events
from jobsearch_os.scoring import score_job, ScoreResult
from jobsearch_os.state_machine import assert_transition


def _job_row(conn: sqlite3.Connection, job_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if row is None:
        raise ValueError(f"No job {job_id}")
    return row


def current_version(conn: sqlite3.Connection, job_id: int) -> dict:
    row = conn.execute(
        "SELECT v.* FROM job_versions v JOIN jobs j ON j.current_version_id = v.version_id "
        "WHERE j.job_id = ?", (job_id,)
    ).fetchone()
    d = {k: row[k] for k in row.keys()}
    d["requirements"] = json.loads(d.get("normalized_requirements") or "[]")
    return d


def _set_status(conn: sqlite3.Connection, job_id: int, new_status: str,
                event_type: str, payload: dict | None = None) -> None:
    current = _job_row(conn, job_id)["status"]
    assert_transition("job", current, new_status)
    conn.execute("BEGIN")
    try:
        conn.execute(
            "UPDATE jobs SET status=?, updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE job_id=?",
            (new_status, job_id),
        )
        events.record(conn, event_type, "job", job_id, payload=payload or {})
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def process_job(conn: sqlite3.Connection, job_id: int, rules: dict, today=None) -> dict:
    """Advance a 'new' job through normalize -> dedupe -> scored. Duplicates
    stop at the 'duplicate' exception state. Returns a summary dict."""
    job = _job_row(conn, job_id)
    if job["status"] != "new":
        return {"job_id": job_id, "status": job["status"], "note": "already processed"}

    _set_status(conn, job_id, "normalized", "normalized")

    if job["dedupe_of"] is not None:
        _set_status(conn, job_id, "duplicate", "deduped_duplicate",
                    payload={"canonical_job_id": job["dedupe_of"]})
        return {"job_id": job_id, "status": "duplicate", "canonical_job_id": job["dedupe_of"]}

    _set_status(conn, job_id, "deduped", "deduped")

    version = current_version(conn, job_id)
    result: ScoreResult = score_job(version, rules, has_contact=False, today=today)
    _set_status(conn, job_id, "scored", "scored", payload={
        "total": result.total, "band": result.band, "components": result.components,
        "scoring_version": result.scoring_version, "matched_skills": result.matched_skills,
        "missing_requirements": result.missing_requirements, "risk_flags": result.risk_flags,
    })
    return {"job_id": job_id, "status": "scored", "score": result.total, "band": result.band}


def latest_score(conn: sqlite3.Connection, job_id: int) -> dict | None:
    row = conn.execute(
        "SELECT payload_json FROM events WHERE subject_type='job' AND subject_id=? "
        "AND event_type='scored' ORDER BY id DESC LIMIT 1", (job_id,)
    ).fetchone()
    return json.loads(row["payload_json"]) if row else None
