"""Ingestion, canonical URL, dedupe, and deterministic scoring (Section U)."""
import datetime as dt

import pytest

from jobsearch_os import ingest, flow
from jobsearch_os.normalize import canonical_url, extract_ats_job_id, extract_requirements
from jobsearch_os.dedupe import jaccard
from jobsearch_os.scoring import score_job

from conftest import REVOPS_JD


@pytest.mark.parametrize("raw,expected", [
    # host lowercased, fragment + utm stripped; PATH CASE PRESERVED (slugs matter)
    ("https://Boards.Greenhouse.io/Acme/jobs/123?utm_source=li#top",
     "https://boards.greenhouse.io/Acme/jobs/123"),
    ("https://jobs.lever.co/acme/abc-123/?gclid=x",
     "https://jobs.lever.co/acme/abc-123"),
    ("https://example.com/job/42?gh_jid=99&ref=twitter",
     "https://example.com/job/42?gh_jid=99"),
])
def test_canonical_url_golden(raw, expected):
    assert canonical_url(raw) == expected


def test_ats_job_id_extraction():
    assert extract_ats_job_id("https://boards.greenhouse.io/acme/jobs/123") == "gh:123"
    assert extract_ats_job_id("https://example.com/x") is None


def test_requirement_extraction():
    reqs = extract_requirements(REVOPS_JD)
    assert any("experience" in r.lower() or "salesforce" in r.lower() for r in reqs)


def test_dedupe_by_canonical_url(workspace, rules):
    j1 = ingest.ingest_one(workspace, {"company": "Acme", "title": "RevOps Analyst",
                                        "description": REVOPS_JD, "url": "https://x.com/j/1?utm_source=a"}, rules)
    j2 = ingest.ingest_one(workspace, {"company": "Acme", "title": "RevOps Analyst",
                                        "description": REVOPS_JD, "url": "https://x.com/j/1?gclid=b"}, rules)
    assert j1["duplicate_of"] is None
    assert j2["duplicate_of"] == j1["job_id"]


def test_dedupe_by_description_hash(workspace, rules):
    j1 = ingest.ingest_one(workspace, {"company": "A", "title": "Analyst",
                                        "description": REVOPS_JD, "url": "https://a.com/1"}, rules)
    j2 = ingest.ingest_one(workspace, {"company": "B", "title": "Analyst",
                                        "description": REVOPS_JD, "url": "https://b.com/2"}, rules)
    assert j2["duplicate_of"] == j1["job_id"]
    assert j2["dedupe_reason"] == "description_hash"


def test_dedupe_by_similarity(workspace, rules):
    base = REVOPS_JD
    variant = REVOPS_JD + " Great team and benefits."
    j1 = ingest.ingest_one(workspace, {"company": "Acme", "title": "RevOps Analyst",
                                        "description": base, "url": "https://a.com/1", "location": "Chicago"}, rules)
    j2 = ingest.ingest_one(workspace, {"company": "Acme", "title": "RevOps Analyst",
                                        "description": variant, "url": "https://a.com/2", "location": "Chicago"}, rules)
    assert j2["duplicate_of"] == j1["job_id"]
    assert j2["dedupe_reason"] == "similarity"


def test_scoring_missing_data_defaults(rules):
    # unknown salary -> neutral (not zero); missing posted date -> neutral freshness
    version = {"title": "Operations Analyst", "description": "Excel reporting and process docs.",
               "location": "", "salary_text": "", "posted_date": "", "requirements": []}
    res = score_job(version, rules, has_contact=False, today=dt.date(2026, 7, 14))
    assert res.components["salary_location_fit"] == rules["salary_location"]["unknown_salary_points"]
    assert res.components["freshness"] == rules["missing_posted_date_points"]
    assert "salary_unknown" in res.risk_flags
    assert res.components["outreach_potential"] == 0  # no contact -> zero


def test_scoring_strong_fit_band(workspace, rules):
    j = ingest.ingest_one(workspace, {"company": "Acme SaaS", "title": "Revenue Operations Analyst",
                                       "description": REVOPS_JD, "url": "https://a.com/1",
                                       "location": "Chicago", "posted_date": "2026-07-12"}, rules)
    flow.process_job(workspace, j["job_id"], rules, today=dt.date(2026, 7, 14))
    score = flow.latest_score(workspace, j["job_id"])
    assert score["band"] in ("high", "strong")
    assert score["scoring_version"] == rules["scoring_version"]


def test_jaccard_bounds():
    assert jaccard("a b c", "a b c") == 1.0
    assert jaccard("", "anything") == 0.0
