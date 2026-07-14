"""Deterministic evidence mapper + prohibited-claims matcher (Section C.1/C.3).

Phase 1 mapper: matches drafts against evidence IDs, normalized keywords, and
configured aliases. No model call. The claim matcher is case-insensitive and
word-boundary-aware with a permitted-context escape.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from jobsearch_os.paths import DATA_DIR
from jobsearch_os.normalize import _normalize_text


# ---------- evidence index (parsed from the markdown banks) ----------

@dataclass
class Evidence:
    id: str
    keywords: list[str]
    resume_phrasing: str = ""
    title: str = ""


def _parse_bank(path: Path, prefix: str) -> list[Evidence]:
    if not path.exists():
        return []
    entries: list[Evidence] = []
    blocks = re.split(r"(?m)^##\s+", path.read_text(encoding="utf-8"))
    for block in blocks:
        block = block.strip()
        if not block.startswith(prefix):
            continue
        eid = block.splitlines()[0].strip()
        fields: dict[str, str] = {}
        for line in block.splitlines()[1:]:
            if ":" in line:
                k, _, v = line.partition(":")
                fields[k.strip().lower()] = v.strip()
        keywords = [k.strip() for k in (fields.get("keywords", "")).split(",") if k.strip()]
        entries.append(Evidence(
            id=eid,
            keywords=keywords,
            resume_phrasing=fields.get("resume phrasing", ""),
            title=fields.get("title", ""),
        ))
    return entries


def load_evidence(data_dir: Path | None = None) -> list[Evidence]:
    d = data_dir or DATA_DIR
    return _parse_bank(d / "experience_bank.md", "EXP-") + _parse_bank(d / "resume_master.md", "RES-")


# ---------- deterministic claim -> evidence mapping ----------

@dataclass
class Mapping:
    claim: str
    evidence_ids: list[str] = field(default_factory=list)
    support_level: str = "unsupported"  # direct | reasonable_inference | unsupported
    needs_user_confirmation: bool = False

    def to_dict(self) -> dict:
        return {
            "claim": self.claim,
            "evidence_ids": self.evidence_ids,
            "support_level": self.support_level,
            "needs_user_confirmation": self.needs_user_confirmation,
        }


def map_claim(claim: str, evidence: list[Evidence]) -> Mapping:
    norm = _normalize_text(claim)
    scored: list[tuple[int, str]] = []
    for ev in evidence:
        hits = sum(1 for kw in ev.keywords if _normalize_text(kw) in norm)
        if hits:
            scored.append((hits, ev.id))
    scored.sort(reverse=True)
    ids = [eid for _h, eid in scored]
    if not ids:
        return Mapping(claim=claim, evidence_ids=[], support_level="unsupported")
    top_hits = scored[0][0]
    if top_hits >= 2:
        return Mapping(claim=claim, evidence_ids=ids, support_level="direct")
    return Mapping(claim=claim, evidence_ids=ids, support_level="reasonable_inference",
                   needs_user_confirmation=True)


# ---------- prohibited-claims matcher ----------

def _word_boundary_regex(pattern: str) -> re.Pattern:
    return re.compile(r"\b" + r"\s+".join(re.escape(w) for w in pattern.split()) + r"\b", re.IGNORECASE)


@dataclass
class ClaimViolation:
    claim_id: str
    pattern: str
    matched_text: str


class ClaimPolicy:
    def __init__(self, policy: dict):
        self.prohibited = policy.get("prohibited_claims", [])
        self.permitted_credentials = set(policy.get("permitted_credentials", []))
        self.portfolio_anchors = set(policy.get("portfolio_anchors", []))

    @classmethod
    def load(cls, data_dir: Path | None = None) -> "ClaimPolicy":
        d = data_dir or DATA_DIR
        return cls(yaml.safe_load((d / "claim_policy.yaml").read_text(encoding="utf-8")))

    def scan(self, text: str) -> list[ClaimViolation]:
        violations: list[ClaimViolation] = []
        for rule in self.prohibited:
            permitted_ctx = rule.get("permitted_context_patterns", []) or []
            ctx_hit = any(_word_boundary_regex(pc).search(text) for pc in permitted_ctx)
            for pat in rule.get("patterns", []):
                m = _word_boundary_regex(pat).search(text)
                if m and not ctx_hit:
                    violations.append(ClaimViolation(rule["id"], pat, m.group(0)))
        return violations
