# ADR-0001 — SQLite + deterministic-first core

Status: accepted (Phase 0)

## Context
The v6 spec mandates a local-first, resumable, approval-gated system that is
"fully functional with zero API keys" and "deterministic-first" (Invariant 8).

## Decision
- Storage: a single SQLite database (`db/jobsearch.db`) with WAL,
  `busy_timeout>=5000`, `foreign_keys=ON` on every connection. One background
  worker; dashboard/CLI use short transactions via the review service.
- Versioned migrations only, tracked in `schema_migrations` with a checksum;
  `migrate` refuses to run on a checksum mismatch. No ad hoc DDL in app code.
- Versioning: `jobs` is a stable identity carrying `current_version_id`;
  `job_versions` are immutable content snapshots with unique
  `(job_id, version_number)`. Packets follow the identity + immutable-version
  pattern.
- Phase 1 has no provider/model dependency of any kind.

## Consequences
- The whole Phase-1 loop is testable without network or API keys.
- Adding providers later (Phase 3) is additive behind a router; it never
  replaces the deterministic block.
