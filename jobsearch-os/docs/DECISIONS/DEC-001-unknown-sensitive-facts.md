# DEC-001 — Sensitive candidate facts are unknown and must not be inferred

Status: OPEN (does not block Phase 1)

## Question
Several application-critical facts are not derivable from any source material
and, per Invariant 7, must never be inferred or model-generated:

- Work authorization / sponsorship needs
- Salary minimum / target
- Relocation stance and commute radius
- Any demographic / disability / veteran / criminal-history voluntary answers

## Why it matters
Application forms ask these directly. If the system guessed, it would violate
Invariant 7 and could submit a false statement on the user's behalf.

## Recommended default (implemented)
Ship `data/candidate_profile.yaml` with these fields present but explicitly
`null` / `unconfirmed`. Any packet or form answer that needs one produces a
**blocked question** in the review inbox instead of a draft. The user answers
via `confirm-fact --question-id <id> --answer "..."`, which records a `FACT-*`
row; only then can that answer appear in an artifact.

## Reversible alternatives
- User fills the fields in `candidate_profile.yaml` up front (bulk confirm).
- User answers blocked questions lazily, as each job surfaces them.

## Work that continues meanwhile
Everything deterministic: ingest, dedupe, scoring, evidence mapping, packet
rendering (with sensitive sections showing "BLOCKED — awaiting FACT
confirmation"), approval of packets that don't depend on the missing facts.
