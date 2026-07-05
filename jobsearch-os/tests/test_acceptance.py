"""The 5 acceptance tests from spec Section B14."""
import ast
import re
from pathlib import Path

import pytest

from jobsearch import pipeline
from jobsearch.coverletter import CoverLetterValidationError, assert_clean, find_banned_phrases
from jobsearch.scoring import TIER_ORDER

from conftest import fixture_text

JOBSEARCH_PKG = Path(__file__).resolve().parent.parent / "jobsearch"


# 1. B12 sample posting produces: diagnosis, score 80-90 range, Strong Apply
#    route, valid cover letter passing blocklist + uniqueness checks,
#    contact checklist, and 4 scheduled touch drafts.
def test_b12_sample_posting_full_pipeline(conn):
    jd_text = fixture_text("sample_revops.txt")
    job_id = pipeline.ingest_job(
        conn, company="Acme SaaS", title="Revenue Operations Analyst",
        jd_text=jd_text, location="Chicago (hybrid)",
    )

    result = pipeline.process_job(conn, job_id)

    assert result["diagnosis"].likely_struggle
    assert result["diagnosis"].recommendation
    assert 80 <= result["score"].total <= 90
    assert result["score"].category == "strong"

    assert result["cover_letter"] is not None
    letter_body = result["cover_letter"]["body"]
    assert find_banned_phrases(letter_body) == []
    assert not letter_body.lower().startswith("i am writing to apply")
    assert_clean(letter_body)  # raises if dirty

    checklist = pipeline.research_checklist_for_job(conn, job_id)
    assert len(checklist) >= 5
    assert any("linkedin.com/in" in c for c in checklist)

    contact_id = pipeline.add_contact(
        conn, job_id=job_id, name="Jamie Rivera", title="RevOps Manager",
        classification="decision_maker", why_selected="Hiring manager for the role",
    )
    touches = conn.execute(
        "SELECT * FROM touches WHERE contact_id=? ORDER BY touch_number", (contact_id,)
    ).fetchall()
    assert len(touches) == 4
    assert [t["touch_number"] for t in touches] == [1, 2, 3, 4]
    assert all(t["status"] == "draft" for t in touches)
    assert all(t["date_due"] for t in touches)


# 2. A posting titled "Revenue Cycle Analyst" with claims/billing language
#    auto-skips with RCM_HEALTHCARE reason.
def test_rcm_healthcare_auto_skip(conn):
    jd_text = fixture_text("sample_rcm.txt")
    job_id = pipeline.ingest_job(conn, company="Regional Hospital Network",
                                  title="Revenue Cycle Analyst", jd_text=jd_text)

    result = pipeline.process_job(conn, job_id)

    assert result["score"].category == "skip"
    assert "RCM_HEALTHCARE" in result["score"].flags

    job = pipeline.get_job(conn, job_id)
    assert job["status"] == "skipped"
    assert "RCM_HEALTHCARE" in job["skip_reason"] or "RCM" in job["skip_reason"]
    # No cover letter should ever be generated for an auto-skipped job.
    assert result["cover_letter"] is None


# 3. A JD requiring "Salesforce Administrator certification" sets
#    ADMIN_CERT_REQUIRED and downgrades one category.
def test_admin_cert_required_downgrades_one_tier(conn):
    jd_text = fixture_text("sample_admin_cert.txt")
    job_id = pipeline.ingest_job(conn, company="Growth SaaS Co",
                                  title="Salesforce Administrator", jd_text=jd_text)

    result = pipeline.process_job(conn, job_id)
    score = result["score"]

    assert "ADMIN_CERT_REQUIRED" in score.flags
    assert score.raw_category != score.category
    assert TIER_ORDER.index(score.category) == TIER_ORDER.index(score.raw_category) - 1
    assert any("ADMIN_CERT_REQUIRED" in r for r in score.downgrade_reasons)


# 4. Attempting to generate text containing "AI expert" or "Salesforce
#    Administrator" (as a self-claim) fails validation.
def test_banned_phrase_validation_rejects_self_claims():
    bad_text_1 = "I am an AI expert who builds automation at scale."
    bad_text_2 = "Certified Salesforce Administrator with hands-on config experience."

    assert find_banned_phrases(bad_text_1) != []
    assert find_banned_phrases(bad_text_2) != []

    with pytest.raises(CoverLetterValidationError):
        assert_clean(bad_text_1)
    with pytest.raises(CoverLetterValidationError):
        assert_clean(bad_text_2)

    clean_text = "I supported Salesforce data quality and governance at JLL Technologies."
    assert find_banned_phrases(clean_text) == []
    assert_clean(clean_text)  # should not raise


# 5. No code path exists that sends email or posts to LinkedIn.
FORBIDDEN_IMPORTS = {"smtplib", "selenium", "playwright"}
FORBIDDEN_CALL_NAMES = {"sendmail", "send_message"}


def test_no_send_or_browser_automation_code_path_exists():
    py_files = list(JOBSEARCH_PKG.rglob("*.py"))
    assert py_files, "expected jobsearch package source files"

    violations = []
    for path in py_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = (
                    [n.name.split(".")[0] for n in node.names]
                    if isinstance(node, ast.Import)
                    else [(node.module or "").split(".")[0]]
                )
                for n in names:
                    if n in FORBIDDEN_IMPORTS:
                        violations.append(f"{path}: forbidden import {n}")
            if isinstance(node, ast.Call):
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
                if name in FORBIDDEN_CALL_NAMES:
                    violations.append(f"{path}: forbidden call {name}")

    assert violations == [], f"Found send/automation code paths: {violations}"

    # Requests must never be POSTed at linkedin.com — outreach here is
    # draft-only, sent by the human copy-pasting into the LinkedIn UI.
    linkedin_post_pattern = re.compile(r"requests\.(post|put)\([^)]*linkedin", re.IGNORECASE)
    for path in py_files:
        text = path.read_text(encoding="utf-8")
        assert not linkedin_post_pattern.search(text), f"{path} appears to POST to LinkedIn"
