"""Event audit trail (Section I). Every business-state change must write its
event row in the SAME transaction as the change. `record` performs only the
INSERT; the caller owns the surrounding transaction so the two commit together.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any


def record(
    conn: sqlite3.Connection,
    event_type: str,
    subject_type: str,
    subject_id: int,
    actor_type: str = "system",
    actor_id: str = "worker",
    payload: dict[str, Any] | None = None,
) -> int:
    cur = conn.execute(
        "INSERT INTO events (event_type, subject_type, subject_id, actor_type, actor_id, payload_json) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (event_type, subject_type, subject_id, actor_type, actor_id,
         json.dumps(payload or {}, sort_keys=True)),
    )
    return cur.lastrowid


def for_subject(conn: sqlite3.Connection, subject_type: str, subject_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM events WHERE subject_type=? AND subject_id=? ORDER BY id",
        (subject_type, subject_id),
    ).fetchall()
