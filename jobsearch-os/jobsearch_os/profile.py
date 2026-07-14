"""Candidate profile + FACT-* resolution (Section C.2, Invariant 7).

Sensitive answers come ONLY from a confirmed FACT (candidate_facts table or a
non-null value in candidate_profile.yaml). If unknown, we create a BLOCKED
QUESTION and never guess or infer.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml

from jobsearch_os import events
from jobsearch_os.paths import DATA_DIR

SENSITIVE_FIELDS = {
    "work_authorization", "requires_sponsorship", "salary_minimum", "salary_target",
    "relocation", "commute_radius_miles", "veteran_status", "disability_status",
    "criminal_history",
}


def load_profile(data_dir: Path | None = None) -> dict:
    d = data_dir or DATA_DIR
    path = d / "candidate_profile.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def seed_facts(conn: sqlite3.Connection, profile: dict | None = None) -> int:
    """Insert confirmed facts from the profile YAML into candidate_facts,
    idempotently. Returns the number newly inserted."""
    profile = profile if profile is not None else load_profile()
    inserted = 0
    conn.execute("BEGIN")
    try:
        for fact in profile.get("confirmed_facts", []) or []:
            cur = conn.execute(
                "INSERT OR IGNORE INTO candidate_facts (fact_id, key, value, source) "
                "VALUES (?, ?, ?, 'profile_yaml')",
                (fact["id"], fact["key"], str(fact["value"])),
            )
            inserted += cur.rowcount
        for key, value in (profile.get("sensitive_facts") or {}).items():
            if value is not None and str(value).strip():
                cur = conn.execute(
                    "INSERT OR IGNORE INTO candidate_facts (fact_id, key, value, source) "
                    "VALUES (?, ?, ?, 'profile_yaml')",
                    (f"FACT-{key.upper().replace('_', '-')}", key, str(value)),
                )
                inserted += cur.rowcount
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return inserted


def get_fact(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute(
        "SELECT value FROM candidate_facts WHERE key=? ORDER BY confirmed_at DESC LIMIT 1", (key,)
    ).fetchone()
    return row["value"] if row else None


def resolve_sensitive(conn: sqlite3.Connection, subject_type: str, subject_id: int,
                      field: str, prompt: str | None = None) -> str | None:
    """Return a confirmed value for a sensitive field, or create/ensure a
    blocked question and return None. Never infers."""
    value = get_fact(conn, field)
    if value is not None:
        return value
    existing = conn.execute(
        "SELECT question_id FROM blocked_questions WHERE subject_type=? AND subject_id=? "
        "AND field=? AND status='open' LIMIT 1", (subject_type, subject_id, field)
    ).fetchone()
    if existing:
        return None
    conn.execute("BEGIN")
    try:
        cur = conn.execute(
            "INSERT INTO blocked_questions (subject_type, subject_id, field, prompt, sensitive, status) "
            "VALUES (?, ?, ?, ?, 1, 'open')",
            (subject_type, subject_id, field,
             prompt or f"Sensitive field '{field}' is unknown. Confirm it before it can appear in any application."),
        )
        events.record(conn, "blocked_question_created", subject_type, subject_id,
                      payload={"field": field, "question_id": cur.lastrowid})
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return None


def confirm_fact(conn: sqlite3.Connection, question_id: int, answer: str) -> str:
    """Record a FACT from a user's answer to a blocked question. Returns the
    fact_id. This is the ONLY way a sensitive answer becomes usable."""
    q = conn.execute("SELECT * FROM blocked_questions WHERE question_id=?", (question_id,)).fetchone()
    if q is None:
        raise ValueError(f"No blocked question {question_id}")
    fact_id = f"FACT-Q{question_id}"
    conn.execute("BEGIN")
    try:
        conn.execute(
            "INSERT OR REPLACE INTO candidate_facts (fact_id, key, value, source, question_id) "
            "VALUES (?, ?, ?, 'user_confirmed', ?)",
            (fact_id, q["field"], answer, question_id),
        )
        conn.execute(
            "UPDATE blocked_questions SET status='answered', answered_fact_id=? WHERE question_id=?",
            (fact_id, question_id),
        )
        events.record(conn, "fact_confirmed", q["subject_type"], q["subject_id"],
                      actor_type="user", actor_id="cli",
                      payload={"field": q["field"], "fact_id": fact_id, "question_id": question_id})
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return fact_id


def open_blocked_questions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM blocked_questions WHERE status='open' ORDER BY question_id"
    ).fetchall()
