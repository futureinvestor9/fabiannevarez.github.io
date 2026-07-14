"""Tests for batch intake, duplicate detection, malformed-row handling, and
the morning-queue digest added for the 'agent' workflow."""
from pathlib import Path

from jobsearch import pipeline
from jobsearch.intake import load_intake_file
from jobsearch.digest import build_digest

from conftest import fixture_text


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_markdown_intake_parses_multiple_blocks(tmp_path):
    md = (
        "## Acme SaaS | Revenue Operations Analyst | https://x.com/1\n"
        "Own CRM data hygiene in Salesforce and improve lead follow-up.\n\n"
        "## Brightwave | CRM Operations Analyst\n"
        "Own CRM cadences in Follow Up Boss and clean up records.\n"
    )
    rows = load_intake_file(_write(tmp_path, "in.md", md))
    assert len(rows) == 2
    assert rows[0]["company"] == "Acme SaaS"
    assert rows[0]["title"] == "Revenue Operations Analyst"
    assert rows[0]["url"] == "https://x.com/1"
    assert "Salesforce" in rows[0]["jd_text"]
    assert rows[1]["company"] == "Brightwave"


def test_csv_intake_with_aliased_headers(tmp_path):
    csv = (
        "employer,role,description,link\n"
        'Datawave,Sales Operations Analyst,"Funnel tracking and pipeline reporting in Salesforce.",https://x.com/2\n'
    )
    rows = load_intake_file(_write(tmp_path, "in.csv", csv))
    assert len(rows) == 1
    assert rows[0]["company"] == "Datawave"
    assert rows[0]["title"] == "Sales Operations Analyst"
    assert "pipeline" in rows[0]["jd_text"]


def test_ingest_batch_dedup_and_malformed(conn):
    rows = [
        {"company": "Acme", "title": "RevOps Analyst",
         "jd_text": "Own CRM data hygiene in Salesforce and improve lead routing and follow-up."},
        {"company": "Acme", "title": "RevOps Analyst",  # exact duplicate
         "jd_text": "Own CRM data hygiene in Salesforce and improve lead routing and follow-up."},
        {"company": "", "title": "No Company", "jd_text": "x" * 40},        # malformed
        {"company": "Beta", "title": "Analyst", "jd_text": "too short"},     # malformed (JD < 30)
    ]
    result = pipeline.ingest_batch(conn, rows)
    assert len(result["ingested"]) == 1
    assert len(result["duplicates"]) == 1
    assert len(result["malformed"]) == 2


def test_digest_reflects_processed_jobs_and_never_sends(conn):
    job_id = pipeline.ingest_job(
        conn, company="Acme SaaS", title="Revenue Operations Analyst",
        jd_text=fixture_text("sample_revops.txt"), location="Chicago",
    )
    pipeline.process_job(conn, job_id)

    digest = build_digest(conn)
    assert "MORNING QUEUE" in digest
    assert "Revenue Operations Analyst @ Acme SaaS" in digest
    assert "COVER LETTER" in digest
    # The digest must always restate that the human does the sending.
    assert "You click Apply" in digest
    assert "hit Send yourself" in digest


def test_rcm_job_shows_in_skipped_section_of_digest(conn):
    job_id = pipeline.ingest_job(
        conn, company="Northwind Health", title="Revenue Cycle Analyst",
        jd_text=fixture_text("sample_rcm.txt"),
    )
    pipeline.process_job(conn, job_id)
    digest = build_digest(conn)
    assert "SKIPPED TODAY" in digest
    assert "RCM_HEALTHCARE" in digest
    # An auto-skipped job must never appear in the apply section.
    assert "READY TO APPLY (0)" in digest
