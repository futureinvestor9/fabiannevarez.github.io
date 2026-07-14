"""Packet build, quality gate, artifact immutability, atomic state+event, and
the approval / post-approval-edit invalidation flow (Section U)."""
import datetime as dt

import pytest

from jobsearch_os import ingest, flow, packet, review_service, events, artifacts
from jobsearch_os.artifacts import ArtifactImmutabilityError

from conftest import REVOPS_JD

TODAY = dt.date(2026, 7, 14)


def _make_scored_job(conn, rules, url="https://a.com/1"):
    j = ingest.ingest_one(conn, {"company": "Acme SaaS", "title": "Revenue Operations Analyst",
                                 "description": REVOPS_JD, "url": url, "location": "Chicago",
                                 "posted_date": "2026-07-12"}, rules)
    flow.process_job(conn, j["job_id"], rules, today=TODAY)
    return j["job_id"]


def test_packet_builds_and_passes_gate(workspace, rules):
    job_id = _make_scored_job(workspace, rules)
    res = packet.build_packet(workspace, job_id, rules)
    assert res.status == "packet_ready"
    assert res.gate_failures == []
    assert res.prohibited_violations == []
    assert res.blocked_questions  # sensitive fields blocked


def test_atomic_state_and_event(workspace, rules):
    job_id = _make_scored_job(workspace, rules)
    ev = {e["event_type"] for e in events.for_subject(workspace, "job", job_id)}
    assert {"ingested", "normalized", "deduped", "scored"} <= ev
    status = workspace.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()["status"]
    assert status == "scored"


def test_artifact_immutability(workspace, rules, tmp_path):
    p = tmp_path / "artifacts" / "x" / "a.md"
    aid, h = artifacts.write_and_register(workspace, "t", "job", 1, p, "hello")
    # identical content is idempotent
    aid2, h2 = artifacts.write_and_register(workspace, "t", "job", 1, p, "hello")
    assert (aid, h) == (aid2, h2)
    # different content at the same path is refused
    with pytest.raises(ArtifactImmutabilityError):
        artifacts.write_and_register(workspace, "t", "job", 1, p, "changed")


def test_mark_submitted_blocked_before_approval(workspace, rules):
    job_id = _make_scored_job(workspace, rules)
    res = packet.build_packet(workspace, job_id, rules)
    with pytest.raises(review_service.ApprovalRequired):
        review_service.mark_submitted(workspace, res.packet_id)


def test_post_approval_edit_invalidation_e2e(workspace, rules):
    job_id = _make_scored_job(workspace, rules)
    res = packet.build_packet(workspace, job_id, rules)
    p1 = res.packet_id

    review_service.submit_for_review(workspace, p1)
    review_service.approve(workspace, p1)

    reg = review_service.regenerate_packet(workspace, job_id, "edited bullet")
    p2 = reg["packet_id"]

    # old approval invalidated -> v1 blocked
    with pytest.raises(review_service.ApprovalRequired):
        review_service.mark_submitted(workspace, p1)
    # v2 not yet approved -> blocked
    with pytest.raises(review_service.ApprovalRequired):
        review_service.mark_submitted(workspace, p2)

    review_service.submit_for_review(workspace, p2)
    review_service.approve(workspace, p2)
    review_service.mark_submitted(workspace, p2)  # succeeds

    inval = workspace.execute(
        "SELECT invalidated_at, invalidation_reason FROM approvals WHERE subject_id=? AND artifact_version=1",
        (p1,),
    ).fetchone()
    assert inval["invalidated_at"] is not None
    assert "regenerated" in inval["invalidation_reason"]


def test_stale_review_hash_guard(workspace, rules):
    job_id = _make_scored_job(workspace, rules)
    res = packet.build_packet(workspace, job_id, rules)
    review_service.submit_for_review(workspace, res.packet_id)
    with pytest.raises(review_service.StaleReview):
        review_service.approve(workspace, res.packet_id, expected_content_hash="wrong-hash")


def test_idempotency_unique_constraint(workspace):
    import sqlite3
    workspace.execute(
        "INSERT INTO tasks (task_type, subject_type, subject_id, idempotency_key) VALUES ('score','job',1,'k')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        workspace.execute(
            "INSERT INTO tasks (task_type, subject_type, subject_id, idempotency_key) VALUES ('score','job',1,'k')"
        )
