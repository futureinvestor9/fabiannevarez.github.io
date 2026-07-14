"""Quality gates (Section P). The packet gate blocks the transition to
approval_pending unless every condition holds. Deterministic; no model call."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GateResult:
    passed: bool
    failures: list = field(default_factory=list)


def check_packet(ctx: dict) -> GateResult:
    failures: list[str] = []

    if not ctx.get("required_fields_present"):
        failures.append("missing required packet fields")
    if ctx.get("score_total") is None or not ctx.get("scoring_version"):
        failures.append("score or scoring_version missing")
    if not ctx.get("source_reference"):
        failures.append("no source reference")
    if ctx.get("evidence_coverage") is None:
        failures.append("evidence coverage not computed")
    if ctx.get("unsupported_outside_risk"):
        failures.append(f"unsupported claims outside risk section: {ctx['unsupported_outside_risk']}")
    if ctx.get("prohibited_violations"):
        ids = [v.claim_id for v in ctx["prohibited_violations"]]
        failures.append(f"prohibited-claims scan failed: {ids}")
    if not ctx.get("sensitive_answers_ok", True):
        failures.append("a sensitive answer was neither FACT-sourced nor blocked")
    if not ctx.get("resume_changes_cite_evidence", True):
        failures.append("a resume change does not cite evidence")
    if not ctx.get("truth_check_present"):
        failures.append("truth-check section missing")
    if not ctx.get("final_recommendation"):
        failures.append("final recommendation missing")

    return GateResult(passed=not failures, failures=failures)
