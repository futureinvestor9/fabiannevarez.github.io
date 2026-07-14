"""Isolated Phase-1 acceptance run (Section V.1). Runs the whole loop in a
temporary workspace with a temporary DB, fixture inputs, isolated artifact
directory, and a deterministic clock — NEVER touching the production database
or folders. Returns (passed, workspace_path, report)."""
from __future__ import annotations

import datetime as dt
import os
import tempfile
from pathlib import Path

from jobsearch_os import db, migrations, ingest, flow, scoring, packet, profile, review_service, events

FIXTURE_CSV = (
    "company,title,description,url,location,posted_date\n"
    "Acme SaaS,Revenue Operations Analyst,"
    "\"Own CRM data hygiene in Salesforce, improve lead routing and follow-up, build pipeline "
    "reports in Excel, and document our sales process. 1-3 years experience. SQL a plus. B2B SaaS.\","
    "https://boards.greenhouse.io/acme/jobs/4242,Chicago,2026-07-12\n"
)

DETERMINISTIC_TODAY = dt.date(2026, 7, 14)


def run(keep_temp: bool = False) -> tuple[bool, str, dict]:
    workspace = Path(tempfile.mkdtemp(prefix="jobsearch_accept_"))
    artifacts_dir = workspace / "artifacts"
    db_path = workspace / "accept.db"
    csv_path = workspace / "job_targets.csv"
    csv_path.write_text(FIXTURE_CSV, encoding="utf-8")

    prev_artifacts_env = os.environ.get("JOBSEARCH_ARTIFACTS_DIR")
    os.environ["JOBSEARCH_ARTIFACTS_DIR"] = str(artifacts_dir)
    report: dict = {"workspace": str(workspace), "steps": []}
    passed = False
    try:
        conn = db.connect(db_path)
        migrations.migrate(conn)
        profile.seed_facts(conn)
        rules = scoring.load_rules()

        ingest_results = ingest.ingest_csv(conn, csv_path, rules)
        job_id = ingest_results[0]["job_id"]
        report["steps"].append(f"ingested job_id={job_id}")

        proc = flow.process_job(conn, job_id, rules, today=DETERMINISTIC_TODAY)
        report["steps"].append(f"scored: {proc['score']} ({proc['band']})")

        res = packet.build_packet(conn, job_id, rules)
        assert res.status == "packet_ready", f"packet not ready: {res.gate_failures}"
        report["steps"].append(f"packet_ready packet_id={res.packet_id}")

        # mark-submitted must be blocked before approval
        blocked_pre = False
        try:
            review_service.mark_submitted(conn, res.packet_id)
        except review_service.ApprovalRequired:
            blocked_pre = True
        assert blocked_pre, "mark_submitted was NOT blocked before approval"
        report["steps"].append("mark_submitted correctly blocked pre-approval")

        review_service.submit_for_review(conn, res.packet_id)
        approval_id = review_service.approve(conn, res.packet_id)
        report["steps"].append(f"approved approval_id={approval_id}")

        review_service.mark_submitted(conn, res.packet_id)
        report["steps"].append("marked submitted (manual)")

        # audit trail verification
        job_events = {e["event_type"] for e in events.for_subject(conn, "job", job_id)}
        packet_events = {e["event_type"] for e in events.for_subject(conn, "packet", res.packet_id)}
        required_job = {"ingested", "normalized", "deduped", "scored", "packet_ready"}
        required_packet = {"approved", "submitted_logged"}
        missing = (required_job - job_events) | (required_packet - packet_events)
        assert not missing, f"audit trail missing events: {missing}"
        report["steps"].append("audit trail complete")

        final_job = conn.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()["status"]
        assert final_job == "submitted_logged", f"unexpected final job status {final_job}"

        # blocked sensitive questions exist (Invariant 7)
        n_blocked = len(profile.open_blocked_questions(conn))
        assert n_blocked > 0, "expected blocked sensitive questions"
        report["steps"].append(f"{n_blocked} sensitive fields correctly blocked")

        conn.close()
        passed = True
    finally:
        if prev_artifacts_env is None:
            os.environ.pop("JOBSEARCH_ARTIFACTS_DIR", None)
        else:
            os.environ["JOBSEARCH_ARTIFACTS_DIR"] = prev_artifacts_env
        if not keep_temp and not passed:
            report["note"] = f"FAILED — workspace preserved at {workspace}"
        elif not keep_temp:
            import shutil
            shutil.rmtree(workspace, ignore_errors=True)
            report["note"] = "workspace cleaned"
        else:
            report["note"] = f"workspace kept at {workspace}"

    return passed, str(workspace), report
