# ARCHITECTURE — jobsearch-os

## One-paragraph shape
A deterministic Python core over SQLite. Jobs are ingested (CSV / manual),
normalized, deduped, scored against `config/scoring_rules.yaml`, and rendered
into an immutable application **packet** artifact. A user reviews each packet
through the **review service** — the single authoritative transaction layer for
approve / revise / reject — which version- and hash-locks approvals. Nothing is
ever sent; `mark-submitted` records a manual action. Phases 3+ add optional
model providers behind a router; the system runs fully with zero API keys.

## Layering (Phase 1)
```
cli.py ─┐
        ├─ review_service.py ──┐
dashboard (P4, thin wrapper) ──┘   (all state changes go through here)
                    │
   ingest → normalize → dedupe → extract → score → packet
                    │
     evidence.py (deterministic mapper + claim-policy matcher)
     profile.py  (FACT-* lookups; unknown → blocked question)
                    │
   state_machine.py (transition maps as data)
   artifacts.py     (atomic write + os.replace + register; immutable)
   events.py        (audit row written in same txn as state change)
   db.py + migrations.py (WAL, busy_timeout, foreign_keys; schema_migrations)
   config.py        (CLI > env > yaml > db settings > defaults)
   redaction.py     (never log secrets)
```

## Sources of truth
- **SQLite** (`db/jobsearch.db`): all job-search runtime state. Authoritative
  for every artifact's status.
- **`state/`**: build process + recovery only (`build_state.json`,
  `build_work_items.yaml`). Never runtime state.
- **`artifacts/`**: immutable content, registered in DB. Never moves.
- **`approvals/`**: regenerable derived views only.

## ID spaces (never mix)
- `TASK-*` runtime tasks (SQLite `tasks`).
- `BUILD-*` build items (`state/build_work_items.yaml`).
- Evidence: `EXP-* / RES-* / FACT-* / CRED-* / PORT-*`.

## Key invariants realized in code
- Approval = DB transaction; content-hash + version lock; post-edit
  invalidation (`review_service.py`).
- State change + event row in one transaction (`events.record` called inside
  the same `with conn:` block as the UPDATE).
- Artifact immutability enforced by writing to temp then `os.replace`, and a
  `doctor --repair-artifacts` report of orphaned/missing/hash-mismatch.
- No external-action code path; a test greps the package for send/automation
  imports and forbidden calls.

## Relationship to the earlier `jobsearch/` prototype
See `docs/ADR/ADR-0002-supersede-prototype.md`. The earlier `jobsearch/`
package (PR #2) is a simpler, pre-v6 prototype. It is preserved, not deleted.
The v6 build lives in `jobsearch_os/`. Consolidation is a future user decision.
