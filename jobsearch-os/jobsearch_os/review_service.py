"""Authoritative review transactions (Section P approval gate, Invariant 5).

The CLI and (later) the dashboard both go through here — one tested transaction
layer. Approvals are version- and content-hash-locked. Editing/regenerating an
artifact after approval invalidates that approval. `mark_submitted` (a record of
a MANUAL user action — nothing is sent) fails unless the exact current version
is approved and not invalidated.
"""
from __future__ import annotations

import sqlite3

from jobsearch_os import artifacts, events, paths
from jobsearch_os.flow import current_version
from jobsearch_os.state_machine import assert_transition


class ApprovalRequired(RuntimeError):
    pass


class StaleReview(RuntimeError):
    pass


def _packet(conn: sqlite3.Connection, packet_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM application_packets WHERE packet_id=?", (packet_id,)).fetchone()
    if row is None:
        raise ValueError(f"No packet {packet_id}")
    return row


def _set_packet_status(conn: sqlite3.Connection, packet_id: int, new_status: str) -> None:
    current = _packet(conn, packet_id)["status"]
    assert_transition("packet", current, new_status)
    conn.execute(
        "UPDATE application_packets SET status=?, updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') "
        "WHERE packet_id=?", (new_status, packet_id),
    )


def _maybe_advance_job(conn: sqlite3.Connection, job_id: int, from_status: str, to_status: str) -> None:
    row = conn.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if row and row["status"] == from_status:
        assert_transition("job", from_status, to_status)
        conn.execute("UPDATE jobs SET status=? WHERE job_id=?", (to_status, job_id))


def submit_for_review(conn: sqlite3.Connection, packet_id: int) -> None:
    pk = _packet(conn, packet_id)
    conn.execute("BEGIN")
    try:
        _set_packet_status(conn, packet_id, "approval_pending")
        _maybe_advance_job(conn, pk["job_id"], "packet_ready", "approval_pending")
        events.record(conn, "submitted_for_review", "packet", packet_id, actor_type="user", actor_id="cli")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def _active_approval(conn: sqlite3.Connection, packet_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM approvals WHERE subject_type='packet' AND subject_id=? "
        "AND decision='approved' AND invalidated_at IS NULL ORDER BY approval_id DESC LIMIT 1",
        (packet_id,),
    ).fetchone()


def _invalidate_active_approvals(conn: sqlite3.Connection, packet_id: int, reason: str) -> int:
    cur = conn.execute(
        "UPDATE approvals SET invalidated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now'), invalidation_reason=? "
        "WHERE subject_type='packet' AND subject_id=? AND decision='approved' AND invalidated_at IS NULL",
        (reason, packet_id),
    )
    return cur.rowcount


def approve(conn: sqlite3.Connection, packet_id: int, actor_id: str = "user",
            expected_content_hash: str | None = None) -> int:
    pk = _packet(conn, packet_id)
    if pk["artifact_id"] is None or pk["content_hash"] is None:
        raise ValueError("Packet has no registered artifact to approve.")
    if expected_content_hash is not None and expected_content_hash != pk["content_hash"]:
        raise StaleReview(
            "Reviewed content hash does not match the current packet — refusing to approve a stale version."
        )
    conn.execute("BEGIN")
    try:
        if pk["status"] == "packet_ready":
            _set_packet_status(conn, packet_id, "approval_pending")
            _maybe_advance_job(conn, pk["job_id"], "packet_ready", "approval_pending")
        cur = conn.execute(
            "INSERT INTO approvals (subject_type, subject_id, artifact_id, artifact_version, "
            "content_hash, actor_type, actor_id, decision) "
            "VALUES ('packet', ?, ?, ?, ?, 'user', ?, 'approved')",
            (packet_id, pk["artifact_id"], pk["version_number"], pk["content_hash"], actor_id),
        )
        approval_id = cur.lastrowid
        _set_packet_status(conn, packet_id, "approved")
        _set_packet_status(conn, packet_id, "submission_assist_ready")
        # advance job through the happy path only if it is waiting at approval_pending
        _maybe_advance_job(conn, pk["job_id"], "approval_pending", "approved_to_apply")
        _maybe_advance_job(conn, pk["job_id"], "approved_to_apply", "submission_assist_ready")
        events.record(conn, "approved", "packet", packet_id, actor_type="user", actor_id=actor_id,
                      payload={"approval_id": approval_id, "artifact_version": pk["version_number"],
                               "content_hash": pk["content_hash"]})
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return approval_id


def revise(conn: sqlite3.Connection, packet_id: int, note: str = "") -> None:
    conn.execute("BEGIN")
    try:
        n = _invalidate_active_approvals(conn, packet_id, "packet_revised")
        status = _packet(conn, packet_id)["status"]
        if status == "approval_pending":
            _set_packet_status(conn, packet_id, "revise")
            _set_packet_status(conn, packet_id, "drafting")
        events.record(conn, "revised", "packet", packet_id, actor_type="user", actor_id="cli",
                      payload={"note": note, "approvals_invalidated": n})
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def reject(conn: sqlite3.Connection, packet_id: int, note: str = "") -> None:
    pk = _packet(conn, packet_id)
    conn.execute("BEGIN")
    try:
        _invalidate_active_approvals(conn, packet_id, "packet_rejected")
        if pk["status"] == "approval_pending":
            _set_packet_status(conn, packet_id, "rejected")
            _set_packet_status(conn, packet_id, "closed")
        _maybe_advance_job(conn, pk["job_id"], "approval_pending", "withdrawn")
        events.record(conn, "rejected", "packet", packet_id, actor_type="user", actor_id="cli",
                      payload={"note": note})
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def regenerate_packet(conn: sqlite3.Connection, job_id: int, edit_note: str) -> dict:
    """Represents editing an artifact after it was produced/approved. Creates a
    new immutable packet version and INVALIDATES any active approval for the
    job's prior packet (Invariant 5). Job coarse-state is left unchanged; the
    authoritative submit gate is the approval-match check in mark_submitted."""
    from jobsearch_os.packet import build_packet  # local import to avoid cycle
    prev = conn.execute(
        "SELECT * FROM application_packets WHERE job_id=? ORDER BY version_number DESC LIMIT 1",
        (job_id,),
    ).fetchone()
    if prev is None:
        raise ValueError(f"No existing packet for job {job_id} to regenerate.")

    version = current_version(conn, job_id)
    prev_artifact = conn.execute("SELECT path FROM artifacts WHERE id=?", (prev["artifact_id"],)).fetchone()
    base_content = ""
    if prev_artifact:
        from pathlib import Path
        p = Path(prev_artifact["path"])
        if p.exists():
            base_content = p.read_text(encoding="utf-8")
    new_version_number = prev["version_number"] + 1
    new_content = base_content + f"\n\n## Editor revision (v{new_version_number})\n{edit_note}\n"
    path = paths.artifacts_root() / "applications" / str(job_id) / str(new_version_number) / "packet.md"

    conn.execute("BEGIN")
    try:
        artifact_id, chash = artifacts.write_and_register(
            conn, "application_packet", "job", job_id, path, new_content, prompt_version="edited-v1"
        )
        cur = conn.execute(
            "INSERT INTO application_packets (job_id, version_number, status, artifact_id, "
            "score_total, scoring_version, content_hash) VALUES (?,?,'packet_ready',?,?,?,?)",
            (job_id, new_version_number, artifact_id, prev["score_total"], prev["scoring_version"], chash),
        )
        new_packet_id = cur.lastrowid
        # invalidate any active approvals on the prior packet version
        _invalidate_active_approvals(conn, prev["packet_id"], "artifact_regenerated_after_approval")
        events.record(conn, "packet_regenerated", "job", job_id, actor_type="user", actor_id="cli",
                      payload={"new_packet_id": new_packet_id, "version_number": new_version_number,
                               "content_hash": chash, "invalidated_prior_packet_id": prev["packet_id"]})
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return {"packet_id": new_packet_id, "version_number": new_version_number, "content_hash": chash,
            "path": str(path)}


def mark_submitted(conn: sqlite3.Connection, packet_id: int, actor_id: str = "user") -> None:
    """Record that the USER submitted the application manually. Blocks unless the
    exact current packet version is approved and not invalidated (Invariant 5).
    This does NOT send anything (Invariant 1)."""
    pk = _packet(conn, packet_id)
    approval = _active_approval(conn, packet_id)
    if approval is None:
        raise ApprovalRequired(
            f"Packet {packet_id} has no active approval — cannot mark submitted. Approve it first."
        )
    if approval["artifact_version"] != pk["version_number"] or approval["content_hash"] != pk["content_hash"]:
        raise ApprovalRequired(
            f"Packet {packet_id}'s active approval is for a different version/content — "
            "the packet changed after approval. Re-approve the current version first."
        )
    conn.execute("BEGIN")
    try:
        _set_packet_status(conn, packet_id, "submitted_logged")
        _maybe_advance_job(conn, pk["job_id"], "submission_assist_ready", "submitted_logged")
        events.record(conn, "submitted_logged", "packet", packet_id, actor_type="user", actor_id=actor_id,
                      payload={"manual": True, "artifact_version": pk["version_number"]})
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
