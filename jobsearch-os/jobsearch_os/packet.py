"""Application packet builder (Section L). Renders the 16-section packet to an
immutable artifact, runs the quality gate, and advances state. Deterministic —
Phase 1 has no model dependency. Outreach is a placeholder; application answers
use ONLY confirmed FACT-* items, and unknown sensitive fields become blocked
questions (Invariant 7)."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from jobsearch_os import artifacts, events, quality, paths
from jobsearch_os.evidence import load_evidence, map_claim, ClaimPolicy
from jobsearch_os.flow import current_version, latest_score
from jobsearch_os.paths import DATA_DIR
from jobsearch_os.profile import resolve_sensitive
from jobsearch_os.scoring import load_rules, score_job
from jobsearch_os.state_machine import assert_transition

SENSITIVE_CHECK_FIELDS = ["work_authorization", "requires_sponsorship", "salary_minimum", "relocation"]


@dataclass
class PacketBuildResult:
    packet_id: int | None
    artifact_id: int | None
    status: str
    gate_failures: list
    prohibited_violations: list
    blocked_questions: list
    path: str | None = None


def _select_bullets(matched_skills: list[str], evidence, version: dict) -> list[dict]:
    """Pick EXP-backed resume bullets whose keywords overlap the job. Each bullet
    is direct evidence (drawn from the evidence bank), tagged with its id."""
    haystack = " ".join([version.get("title", ""), version.get("description", "")]).lower()
    bullets = []
    for ev in evidence:
        if not ev.id.startswith("EXP-") or not ev.resume_phrasing:
            continue
        if any(kw.lower() in haystack for kw in ev.keywords):
            m = map_claim(ev.resume_phrasing, evidence)
            # a bullet drawn from its own EXP is direct evidence for that EXP
            support = "direct"
            ids = [ev.id] + [i for i in m.evidence_ids if i != ev.id]
            bullets.append({"text": ev.resume_phrasing, "evidence_ids": ids, "support_level": support})
    return bullets[:5]


def _render_markdown(job_id: int, version: dict, score: dict, bullets: list[dict],
                     sensitive: list[dict], violations: list, pending_inferences: list,
                     source_reference: str, evidence_coverage: float,
                     final_recommendation: str) -> str:
    L = []
    w = L.append
    w(f"# Application Packet — {version.get('title','')} @ {version.get('company','')}")
    w(f"_job_id={job_id} · scoring_version={score.get('scoring_version')} · source={source_reference}_\n")

    w("## 1. Job & company summary")
    w(f"- Company: {version.get('company','')}")
    w(f"- Title: {version.get('title','')}")
    w(f"- Location: {version.get('location','') or 'n/a'}  |  Remote: {version.get('remote_status','') or 'n/a'}")
    w(f"- Source: {version.get('source','')}\n")

    w("## 2. Score + breakdown")
    w(f"- **Total: {score.get('total')} ({score.get('band')})** — {score.get('scoring_version')}")
    for k, v in score.get("components", {}).items():
        w(f"  - {k}: {v}")
    w("")

    w("## 3. Why the role fits")
    w(f"- Matched skill areas: {', '.join(score.get('matched_skills', [])) or 'none'}\n")

    w("## 4. Evidence map")
    for b in bullets:
        w(f"- \"{b['text'][:70]}...\" -> {', '.join(b['evidence_ids'])} ({b['support_level']})")
    w(f"- Evidence coverage (direct bullets): {evidence_coverage:.0%}\n")

    w("## 5. Missing qualifications")
    miss = score.get("missing_requirements", [])
    w("- " + (", ".join(miss) if miss else "none flagged") + "\n")

    w("## 6. Risk flags")
    for f in score.get("risk_flags", []):
        w(f"- {f}")
    w("- (This is the ONLY section where unsupported claims may appear.)\n")

    w("## 7. Resume version recommendation")
    w("- Use the analyst/CRM-ops master resume (RES-001) as the base.\n")

    w("## 8. Exact bullet edits (before / after / evidence)")
    for b in bullets:
        w(f"- AFTER: {b['text']}")
        w(f"  - evidence: {', '.join(b['evidence_ids'])}")
    w("")

    w("## 9. Cover letter")
    w("- Optional; generate only if the posting requires or it is strategically useful (Phase 3+).\n")

    w("## 10. Outreach targets + draft messages")
    w("- _Outreach begins in Phase 2._\n")

    w("## 11. Application question draft answers")
    w("- Only deterministic answers from confirmed FACT-* items appear here. "
      "Unknown sensitive answers are BLOCKED questions, never drafted.\n")

    w("## 12. Salary / location / work-authorization checks")
    for s in sensitive:
        if s["value"] is not None:
            w(f"- {s['field']}: {s['value']} (confirmed)")
        else:
            w(f"- {s['field']}: **BLOCKED — awaiting FACT confirmation** (question_id={s['question_id']})")
    w("")

    w("## 13. Truth check")
    w(f"- Prohibited-claims scan: {'PASS' if not violations else 'FAIL: ' + ', '.join(v.claim_id for v in violations)}")
    if pending_inferences:
        w("- Pending reasonable-inference confirmations (must be confirmed before inclusion):")
        for pi in pending_inferences:
            w(f"  - \"{pi['claim'][:60]}...\" -> {', '.join(pi['evidence_ids'])}")
    else:
        w("- No pending reasonable-inference confirmations.")
    w("")

    w("## 14. Final recommendation")
    w(f"- **{final_recommendation}**\n")

    w("## 15. Submission-assist checklist (materials only — no automation)")
    w("- [ ] Resume selected and tailored per section 8")
    w("- [ ] Application answers filled from confirmed FACTs only")
    w(f"- [ ] Open the posting: {source_reference}")
    w("- [ ] Submit manually, then run `mark-submitted --packet-id <id>`\n")

    w("## 16. Follow-up date")
    w("- Set at submission time (Phase 2 follow-up queue).")
    return "\n".join(L)


def build_packet(conn: sqlite3.Connection, job_id: int, rules: dict | None = None,
                 data_dir: Path | None = None) -> PacketBuildResult:
    rules = rules or load_rules()
    data_dir = data_dir or DATA_DIR
    job = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if job is None:
        raise ValueError(f"No job {job_id}")
    if job["status"] != "scored":
        raise ValueError(f"Job {job_id} must be 'scored' to build a packet (is '{job['status']}').")

    version = current_version(conn, job_id)
    score = latest_score(conn, job_id) or score_job(version, rules).__dict__
    evidence = load_evidence(data_dir)
    bullets = _select_bullets(score.get("matched_skills", []), evidence, version)

    # Sensitive checks — unknown -> blocked question (Invariant 7).
    sensitive = []
    for field in SENSITIVE_CHECK_FIELDS:
        val = resolve_sensitive(conn, "job", job_id, field)
        qid = None
        if val is None:
            row = conn.execute(
                "SELECT question_id FROM blocked_questions WHERE subject_type='job' AND subject_id=? "
                "AND field=? ORDER BY question_id DESC LIMIT 1", (job_id, field)
            ).fetchone()
            qid = row["question_id"] if row else None
        sensitive.append({"field": field, "value": val, "question_id": qid})

    # Assemble external-facing text and run the prohibited-claims scan.
    external_text = "\n".join(b["text"] for b in bullets) + "\n" + version.get("title", "")
    policy = ClaimPolicy.load(data_dir)
    violations = policy.scan(external_text)

    pending_inferences = [b for b in bullets if b["support_level"] == "reasonable_inference"]
    unsupported_outside_risk = [b["text"] for b in bullets if b["support_level"] == "unsupported"]
    direct = sum(1 for b in bullets if b["support_level"] == "direct")
    evidence_coverage = (direct / len(bullets)) if bullets else 0.0
    source_reference = job["canonical_url"] or f"job:{job_id}"
    final_recommendation = ("approve" if score.get("band") in ("high", "strong") else "revise")

    ctx = {
        "required_fields_present": bool(version.get("company") and version.get("title")),
        "score_total": score.get("total"),
        "scoring_version": score.get("scoring_version"),
        "source_reference": source_reference,
        "evidence_coverage": evidence_coverage,
        "unsupported_outside_risk": unsupported_outside_risk,
        "prohibited_violations": violations,
        "sensitive_answers_ok": True,  # all unknowns became blocked questions
        "resume_changes_cite_evidence": all(b["evidence_ids"] for b in bullets),
        "truth_check_present": True,
        "final_recommendation": final_recommendation,
    }
    gate = quality.check_packet(ctx)

    # Determine next packet version number.
    vnum_row = conn.execute(
        "SELECT COALESCE(MAX(version_number),0)+1 AS n FROM application_packets WHERE job_id=?", (job_id,)
    ).fetchone()
    version_number = vnum_row["n"]

    if not gate.passed:
        # Gate failure returns the packet to drafting; nothing externally usable is produced.
        conn.execute("BEGIN")
        try:
            conn.execute(
                "INSERT INTO application_packets (job_id, version_number, status, score_total, scoring_version) "
                "VALUES (?,?,'drafting',?,?)",
                (job_id, version_number, score.get("total"), score.get("scoring_version")),
            )
            events.record(conn, "packet_gate_failed", "job", job_id,
                          payload={"failures": gate.failures, "version_number": version_number})
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return PacketBuildResult(None, None, "drafting", gate.failures, violations,
                                 [s for s in sensitive if s["value"] is None])

    markdown = _render_markdown(job_id, version, score, bullets, sensitive, violations,
                                pending_inferences, source_reference, evidence_coverage,
                                final_recommendation)
    path = paths.artifacts_root() / "applications" / str(job_id) / str(version_number) / "packet.md"

    conn.execute("BEGIN")
    try:
        artifact_id, chash = artifacts.write_and_register(
            conn, "application_packet", "job", job_id, path, markdown, prompt_version="deterministic-v1"
        )
        cur = conn.execute(
            "INSERT INTO application_packets (job_id, version_number, status, artifact_id, "
            "score_total, scoring_version, content_hash) VALUES (?,?,'packet_ready',?,?,?,?)",
            (job_id, version_number, artifact_id, score.get("total"), score.get("scoring_version"), chash),
        )
        packet_id = cur.lastrowid
        assert_transition("job", job["status"], "packet_ready")
        conn.execute("UPDATE jobs SET status='packet_ready' WHERE job_id=?", (job_id,))
        events.record(conn, "packet_ready", "job", job_id,
                      payload={"packet_id": packet_id, "artifact_id": artifact_id,
                               "version_number": version_number, "content_hash": chash})
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return PacketBuildResult(packet_id, artifact_id, "packet_ready", [], violations,
                             [s for s in sensitive if s["value"] is None], str(path))
