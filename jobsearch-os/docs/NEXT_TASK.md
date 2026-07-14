# NEXT_TASK

**Phase 1 is COMPLETE** — the v6 walking skeleton (`jobsearch_os/`) is usable
end-to-end, deterministic, zero API keys. All Phase-1-blocking tests pass
(`pytest tests/v6 -q`, 42 tests) and `python -m jobsearch_os.cli accept-phase1`
passes in an isolated workspace. See `docs/QUICKSTART_V6.md`.

**Next (deferred, not yet built):** Phase 2 — outreach drafts + contact
ingestion, full quality gates, follow-up queue, and `defer`. Build items
BUILD-200+ in `state/build_work_items.yaml`.

**Open decisions:** DEC-001 (unknown sensitive facts → blocked questions;
does not block anything — the user answers via `confirm-fact`).

**Do not:** add any model/provider dependency to Phase 1; delete the
`jobsearch/` prototype (ADR-0002); build Phases 2–9 without reading
`docs/MASTER_SPEC.md` for the relevant section.

To resume: follow `docs/RESUME_CODEX.md`.
