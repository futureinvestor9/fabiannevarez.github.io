# ADR-0002 — Preserve the earlier `jobsearch/` prototype; build v6 in `jobsearch_os/`

Status: accepted (Phase 0)

## Context
Before this v6 spec arrived, the repo already contained a working, simpler
job-search prototype in `jobsearch/` (package name `jobsearch`), which is the
subject of open PR #2. The v6 spec defines a materially more rigorous
architecture (versioned migrations, transition-map state machines, evidence
namespaces, an authoritative review-service transaction layer, immutable
versioned artifacts) and its own package layout (`jobsearch_os/`).

Invariant 13 forbids discarding or overwriting pre-existing user work without
explicit approval.

## Decision
Build the v6 system fresh in `jobsearch_os/` and **preserve** the earlier
`jobsearch/` prototype untouched. Do not migrate or delete it in this build.
Record consolidation (removing the prototype, or folding its content YAML into
the v6 `data/` layer) as a future user decision.

## Consequences
- Two packages coexist temporarily: `jobsearch/` (prototype) and `jobsearch_os/`
  (v6). They do not import each other. Tests are namespaced separately.
- The prototype's real career content (docs/spec.md, content/*.yaml) is a useful
  seed for the v6 `data/` files (resume_master, experience_bank,
  candidate_profile, claim_policy) and is reused as source material.
- If the user later wants a single system, that is a reversible cleanup:
  delete `jobsearch/` and its tests, keep `jobsearch_os/`.

## Reversal
`git rm -r jobsearch/ jobsearch-os prototype tests` — trivial and non-destructive
to the v6 build.
