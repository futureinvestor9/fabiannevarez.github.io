# BUILD_PLAN — jobsearch-os

Phases execute in order (Section G). Each ends: run tests → triage → commit →
update state files. Phase 1 is the priority: **usable end-to-end**.

| Phase | Scope | Status |
|---|---|---|
| 0 | Repo audit, preflight, Section E docs, state files, `doctor` | DONE |
| 1 | Deterministic walking skeleton (ingest→score→packet→approve→mark-submitted) | IN PROGRESS |
| 2 | Outreach + quality gates + follow-ups + defer + contacts | deferred |
| 3 | Model router + budgets + research (optional providers) | deferred |
| 4 | Full dashboard | deferred |
| 5 | Replies | deferred |
| 6 | Orchestrator loop + continuity | deferred |
| 7 | Claude Code bridge (needs `CLAUDE_CODE_ENABLED=true`) | deferred |
| 8 | Handoffs (needs `HANDOFFS_ENABLED=true`) | deferred |
| 9 | Hardening + release | deferred |

## Phase 1 build items
- BUILD-110 package + config precedence + db pragmas + versioned migrations
- BUILD-120 ingest / normalize / canonical-URL / dedupe / rule-extractor / scoring
- BUILD-130 evidence mapper + claim-policy matcher + candidate profile + packet
- BUILD-140 state machine + review_service + CLI + accept-phase1 harness
- BUILD-160 Phase-1-blocking test suite green

## Phase 1 exit (Section V)
1. Runs with zero API keys, deterministic only.
2. `doctor` reports environment; `--repair-artifacts` report-only, `--apply` fixes.
3. Isolated `accept-phase1` passes (temp workspace, temp DB, deterministic clock).
4. Approvals version+hash locked; post-approval-edit e2e passes; mark-submitted
   blocked pre-approval.
5. Every external claim has evidence or is confined to the risk section;
   prohibited claims blocked; sensitive answers never inferred.
6. All Phase-1-blocking tests pass.
7. Build resumes from repository state alone.
