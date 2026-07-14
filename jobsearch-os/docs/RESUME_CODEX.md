# RESUME_CODEX — how to continue this build from repository state alone

1. Read `AGENTS.md`, `docs/INVARIANTS.md`, `docs/ARCHITECTURE.md`,
   `docs/NEXT_TASK.md`, `state/build_state.json`, `state/build_work_items.yaml`.
2. Recreate the environment: `python -m venv .venv` (or use `uv`), then
   `pip install -e .` (or `pip install pyyaml pytest`).
3. Run `python -m jobsearch_os.cli doctor` to confirm the environment.
4. Run `pytest tests/ -q`. If green through the Phase-1-blocking set, Phase 1 is
   complete; move to the next `pending`/`deferred` item in
   `state/build_work_items.yaml`.
5. Run `python -m jobsearch_os.cli accept-phase1` for the isolated end-to-end
   acceptance (temp workspace + temp DB; production untouched).

## If Phase 1 is not yet green
Continue the in-progress BUILD item named in `state/build_state.json`. The
Phase-1 module list is in `docs/BUILD_PLAN.md`. Keep to the deterministic path
(no providers). After each module: run its smallest test, update the state
files, commit a small coherent change.

## Continuity rule
If nearing a limit: finish or roll back the current atomic item, run tests,
commit last known-good, update this file with the exact next command, and stop.
The build must be recoverable from repository state alone.
