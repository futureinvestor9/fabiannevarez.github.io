# MASTER_SPEC — jobsearch-os (v6)

This is a faithful, build-oriented condensation of the v6 master build prompt.
The safety invariants (Section B) are reproduced verbatim in
[`INVARIANTS.md`](INVARIANTS.md) and are authoritative. This file preserves the
binding schemas, state machines, and phase definitions the code depends on.

## Mission
Local-first, resumable, approval-gated job-search OS. Loop: ingest → normalize
/ dedupe / score → research + draft → review queue → user approves/revises/
rejects → record decision → next. Usable end-to-end at the **close of Phase 1**.

Target roles: Operations / Business / Business Systems / Revenue Operations /
Sales Operations / CRM Operations / Data-Reporting / Implementation / Customer
Operations / Revenue Cycle Analyst.

## Evidence namespaces
`EXP-###` experience-bank entry · `RES-###` resume_master content · `FACT-###`
user-confirmed candidate fact · `CRED-###` verified credential · `PORT-###`
portfolio project. Every externally visible claim maps to one of these or is
blocked. `support_level ∈ {direct, reasonable_inference, unsupported}`:
- `unsupported` → only inside the packet's internal risk/truth-check section.
- `reasonable_inference` → only in an internal proposed-draft section; cannot
  enter an approved external artifact until the user confirms the specific
  inference, recorded as a new `FACT-*`. Approving the packet does NOT silently
  confirm inferences.
- Phase-1 mapper is deterministic (evidence IDs, normalized skills, keywords,
  configured aliases). No model call.

## Sensitive answers (Invariant 7)
Work auth, sponsorship, comp expectations, relocation, demographic, disability,
veteran status, criminal history → only from a confirmed `FACT-*`, else a
blocked question. Never inferred or model-generated.

## Config precedence (everywhere)
CLI args → env vars → YAML config → DB `settings` table → built-in defaults.

## Database (Section I)
Every connection: `journal_mode=WAL`, `busy_timeout>=5000`, `foreign_keys=ON`.
UTC ISO-8601 timestamps. One background worker; dashboard/CLI do short txns via
the review service; SQLite serializes writes. Every business-state change and
its `events` row commit in the SAME transaction. Artifacts: temp file →
`os.replace` into immutable `artifacts/…` → register in DB. Registered
artifacts never move; status lives in SQLite. `approvals/` = regenerable views.

Versioned migrations only. `schema_migrations(id, checksum, applied_at)`;
`migrate` refuses to run on checksum mismatch; each migration is transactional.

`jobs` is stable identity with `current_version_id`; `job_versions` immutable
snapshots, unique `(job_id, version_number)`.

Approvals row: approval_id, subject_type, subject_id, artifact_id,
artifact_version, content_hash, actor_type, actor_id, decision, created_at,
invalidated_at, invalidation_reason.

Tasks (queue): id, task_type, subject_type, subject_id, idempotency_key,
priority, status, attempts, max_attempts, available_at, locked_by, locked_until,
input_json, output_artifact_id, error_code, error_message, created_at,
updated_at. UNIQUE `(task_type, subject_type, subject_id, idempotency_key)` —
duplicate enqueue returns the existing task.

Artifacts row: id, artifact_type, subject_type, subject_id, path, content_hash,
parent_artifact_id, prompt_version, provider, model, created_at.

Events row: id, event_type, subject_type, subject_id, actor_type, actor_id,
payload_json, created_at. The events table is the audit trail.

## State machines (Section J) — explicit transition maps, exhaustive
See `jobsearch_os/state_machine.py` for the authoritative maps. Parameterized
tests prove every listed edge succeeds and every unlisted edge raises. Job
machine (Phase-1 reachable subset): `new → normalized → deduped → scored →
packet_ready → approval_pending → approved_to_apply → submission_assist_ready →
submitted_logged → followup_due → …`. Research states exist in the map but only
become reachable in Phase 3. Any non-terminal → `duplicate|blocked|stale|
withdrawn|error`. Application-packet machine: `drafting → quality_check →
packet_ready|drafting; packet_ready → approval_pending; approval_pending →
approved → submission_assist_ready | revise → drafting | rejected → closed |
deferred (P2); deferred → approval_pending; submission_assist_ready →
submitted_logged → followup_due → closed`. No object skips the approval gate.

## Ingestion / dedupe / scoring (Section K)
MVP sources: CSV, manual URL + pasted description, folder markdown/JSON.
Canonical URL: lowercase scheme+host, strip fragments, strip tracking params
(utm_*, gclid, fbclid, ref, src — configurable), normalize trailing slash,
PRESERVE job-id path/query segments (greenhouse/lever/workday). Dedupe order:
canonical URL → ATS job id → description hash → company/title/location + token-
set Jaccard (default 0.85, `dedupe_version` recorded). Never delete dupes; link
to canonical.

Scoring is deterministic and driven by `config/scoring_rules.yaml`. 100-pt
rubric: Role fit 0–30 · Requirements 0–25 · Evidence 0–15 · Industry 0–10 ·
Salary/location 0–10 · Freshness 0–5 · Outreach potential 0–5. Missing-data
defaults: unknown salary → neutral; missing date → neutral freshness; direct
evidence → full points; reasonable inference → partial + flag; unsupported →
zero + flag; no contact info → zero outreach. Decision bands: 85–100 high /
75–84 strong / 65–74 research-only / 50–64 hold / 0–49 skip. Save total +
components + matched/missing + `scoring_version`.

## Application packet (Section L)
`artifacts/applications/<job_id>/<packet_version>/packet.md`, immutable. 16
sections in order (summary, score+breakdown, why-fit, evidence map, missing
quals, risk flags [only place unsupported claims may appear], resume version,
exact bullet edits before/after/evidence, cover letter if useful, outreach
[P1: placeholder], application answers [P1: FACT-* only, unknowns→blocked],
salary/location/work-auth checks, truth check + prohibited-claims scan +
pending inferences, final recommendation, submission-assist checklist,
follow-up date). Senior review is advisory/non-blocking.

## Quality + approval gates (Section P)
Packet gate blocks `approval_pending` unless: required fields; score+version;
source reference; evidence coverage computed; unsupported claims confined to
risk section; reasonable_inference items listed; prohibited-claims scan passes;
sensitive answers FACT-sourced or blocked; risk flags shown; resume changes
cite evidence; uncertainty shown; truth-check present; final rec present.
Approval gate: DB transaction with full approvals schema; version + content
hash must match reviewed version; post-approval regeneration sets
invalidated_at + reason; mark-submitted/mark-sent fail unless the exact version
is currently approved and not invalidated.

## Phases (Section G)
0 audit/recovery · **1 deterministic walking skeleton (usable end-to-end)** ·
2 outreach + gates + follow-ups + defer · 3 model router/budgets/research ·
4 dashboard · 5 replies · 6 orchestrator loop · 7 Claude Code bridge (flag) ·
8 handoffs (flag) · 9 hardening. Phase 1 has NO provider dependency.

## CLI (Section R)
doctor [--repair-artifacts [--apply]], init-db, migrate, ingest --csv,
add-job --url --description-file, score, review-export, approve/revise/reject
--type --id [--note], mark-submitted --packet-id, confirm-fact --question-id
--answer, accept-phase1 [--keep-temp]. (defer, add-contact, mark-sent,
add-reply, handoffs, claude-review are later phases.)

## Deferred backlog (Section X) — do NOT build in Phases 0–9
Keyring credential storage; DB backup/restore/sync; official ATS/Gmail/calendar
connectors; audited post-approval sender; automated score-weight experiments;
local-model routing; a11y/mobile dashboard; multi-user roles.

## Note on this file
For the full authoritative prose (rationale, glossary Section A, all edge
cases), see the v6 master build prompt provided by the user. This condensation
preserves the binding contracts; where any conflict arises, `INVARIANTS.md`
wins, then the user's full prompt, then this file.
