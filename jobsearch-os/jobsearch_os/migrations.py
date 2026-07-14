"""Versioned migration runner (Section I migration contract).

- Migrations are `db/migrations/NNNN_name.sql`, applied in numeric order.
- `schema_migrations(migration_id, checksum, applied_at)` records what ran.
- Each migration applies inside one transaction and rolls back on failure.
- `migrate` REFUSES to run if a recorded checksum no longer matches the file.
- No ad hoc CREATE TABLE lives in application code — only here.
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from jobsearch_os.paths import MIGRATIONS_DIR


class MigrationChecksumMismatch(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _split_statements(sql: str) -> list[str]:
    lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        lines.append(line)
    body = "\n".join(lines)
    return [s.strip() for s in body.split(";") if s.strip()]


def _ensure_registry(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "migration_id TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)"
    )


def discover(migrations_dir: Path | None = None) -> list[Path]:
    d = migrations_dir or MIGRATIONS_DIR
    return sorted(d.glob("*.sql"), key=lambda p: p.name)


def applied_migrations(conn: sqlite3.Connection) -> dict[str, str]:
    _ensure_registry(conn)
    rows = conn.execute("SELECT migration_id, checksum FROM schema_migrations").fetchall()
    return {r[0]: r[1] for r in rows}


def migrate(conn: sqlite3.Connection, migrations_dir: Path | None = None) -> list[str]:
    """Apply pending migrations. Returns the list of migration_ids applied.
    Raises MigrationChecksumMismatch if an already-applied file changed."""
    _ensure_registry(conn)
    already = applied_migrations(conn)
    applied_now: list[str] = []

    for path in discover(migrations_dir):
        migration_id = path.stem
        text = path.read_text(encoding="utf-8")
        checksum = _checksum(text)

        if migration_id in already:
            if already[migration_id] != checksum:
                raise MigrationChecksumMismatch(
                    f"Migration {migration_id} changed on disk after being applied "
                    f"(recorded {already[migration_id][:12]}, file {checksum[:12]}). Refusing to run."
                )
            continue

        statements = _split_statements(text)
        conn.execute("BEGIN")
        try:
            for stmt in statements:
                conn.execute(stmt)
            conn.execute(
                "INSERT INTO schema_migrations (migration_id, checksum, applied_at) VALUES (?, ?, ?)",
                (migration_id, checksum, _utc_now()),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        applied_now.append(migration_id)

    return applied_now
