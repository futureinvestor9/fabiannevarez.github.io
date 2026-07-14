"""Evidence mapping, claim-policy matcher, sensitive-answer blocking (Section U)."""
from jobsearch_os.evidence import load_evidence, map_claim, ClaimPolicy
from jobsearch_os import profile


def test_evidence_mapping_namespaces():
    ev = load_evidence()
    ids = {e.id for e in ev}
    assert any(i.startswith("EXP-") for i in ids)
    assert any(i.startswith("RES-") for i in ids)
    m = map_claim("Designed a Follow Up Boss cadence managing a pipeline with Smart Lists", ev)
    assert m.support_level == "direct"
    assert any(i.startswith("EXP-") for i in m.evidence_ids)


def test_unsupported_claim_maps_unsupported():
    ev = load_evidence()
    m = map_claim("Led a 50-person offshore Kubernetes platform team", ev)
    assert m.support_level == "unsupported"
    assert m.evidence_ids == []


def test_claim_policy_blocks_true_matches():
    policy = ClaimPolicy.load()
    for bad in ["I am a Salesforce Administrator", "AI expert with 10 years",
                "proficient in SQL", "seasoned data scientist"]:
        assert policy.scan(bad), f"should block: {bad}"


def test_claim_policy_allows_permitted_context():
    policy = ClaimPolicy.load()
    for ok in ["supported Salesforce administrators on data quality",
               "hands-on Salesforce data quality work",
               "working knowledge of SQL, actively building",
               "AI-assisted analysis with a validation step"]:
        assert policy.scan(ok) == [], f"should NOT block: {ok}"


def test_sensitive_answer_never_inferred_becomes_blocked_question(workspace):
    # No FACT for work_authorization -> resolve returns None + creates blocked question.
    val = profile.resolve_sensitive(workspace, "job", 1, "work_authorization")
    assert val is None
    qs = profile.open_blocked_questions(workspace)
    assert any(q["field"] == "work_authorization" for q in qs)
    # idempotent: calling again does not create a duplicate
    profile.resolve_sensitive(workspace, "job", 1, "work_authorization")
    qs2 = [q for q in profile.open_blocked_questions(workspace) if q["field"] == "work_authorization"]
    assert len(qs2) == 1


def test_confirm_fact_unblocks(workspace):
    profile.resolve_sensitive(workspace, "job", 1, "salary_minimum")
    q = [q for q in profile.open_blocked_questions(workspace) if q["field"] == "salary_minimum"][0]
    fact_id = profile.confirm_fact(workspace, q["question_id"], "$70,000")
    assert fact_id.startswith("FACT-")
    assert profile.get_fact(workspace, "salary_minimum") == "$70,000"
    # now resolvable without a new block
    assert profile.resolve_sensitive(workspace, "job", 2, "salary_minimum") == "$70,000"
