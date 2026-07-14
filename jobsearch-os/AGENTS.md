# AGENTS.md — permanent repo rules for jobsearch-os

This is a local-first, resumable, approval-gated job-search operating system.

**Read [`docs/INVARIANTS.md`](docs/INVARIANTS.md) before doing anything.** Those
14 safety invariants override all other guidance. The most load-bearing:

- No autonomous external actions. Nothing sends, submits, connects, or posts.
  `mark-submitted` / `mark-sent` only record that the human did it by hand.
- No LinkedIn scraping / auto-connect / auto-message. No CAPTCHA/login-wall
  bypass. No reading of any credential store.
- Approval is a version- and content-hash-locked DB transaction. Editing an
  approved artifact invalidates the approval.
- Every externally visible claim maps to evidence (`EXP-* / RES-* / FACT-* /
  CRED-* / PORT-*`) or is blocked. Sensitive answers come only from a
  confirmed `FACT-*` or become a blocked question — never inferred.
- Deterministic Python first; every model call is bounded. When uncertain,
  block (write a `docs/DECISIONS/DEC-###.md`).

## Where things live
- SQLite (`db/jobsearch.db`) owns all runtime state. `state/` owns only the
  build process. An artifact's status is defined by SQLite, never its folder.
- Runtime tasks are `TASK-*` (SQLite `tasks` table). Build items are `BUILD-*`
  (`state/build_work_items.yaml`). Never mix the two ID spaces.
- Artifacts under `artifacts/` are immutable once registered. `approvals/`
  holds only regenerable derived views.

## Working rules
- Config precedence everywhere: CLI args → env vars → YAML → DB `settings` →
  built-in defaults.
- Versioned migrations only; no ad hoc `CREATE TABLE` in app code.
- Every business-state change writes its `events` row in the SAME transaction.
- Never hold a DB transaction across a model call. Exactly one worker process.
- Windows-safe paths. Never interpolate model output into a shell command.

## Build loop
After each build item: run smallest relevant tests → update
`state/build_work_items.yaml` + `state/build_state.json` + `docs/NEXT_TASK.md`
→ commit a small coherent change. If nearing a limit, commit last known-good
and write an exact continuation to `docs/RESUME_CODEX.md`.
