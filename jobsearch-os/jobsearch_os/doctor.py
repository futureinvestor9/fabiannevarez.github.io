"""`doctor` — environment + artifact health report (Section R, Section V.2).
`--repair-artifacts` is report-only by default; `--apply` is required to change."""
from __future__ import annotations

import os
import sqlite3
import sys

from jobsearch_os import artifacts, migrations
from jobsearch_os.config import Config


def environment_report(conn: sqlite3.Connection | None) -> dict:
    rep: dict = {
        "python": sys.version.split()[0],
        "sqlite": sqlite3.sqlite_version,
        "feature_flags": {},
        "migrations": {},
    }
    try:
        import yaml  # noqa
        rep["pyyaml"] = True
    except Exception:
        rep["pyyaml"] = False

    cfg = Config(conn=conn)
    for key in ("claude_code_enabled", "handoffs_enabled", "claude_chat_mode", "budget_mode"):
        rep["feature_flags"][key] = cfg.get(key)

    if conn is not None:
        applied = migrations.applied_migrations(conn)
        pending = [p.stem for p in migrations.discover() if p.stem not in applied]
        rep["migrations"] = {"applied": sorted(applied.keys()), "pending": pending}
    return rep


def repair_artifacts(conn: sqlite3.Connection, apply: bool = False) -> dict:
    """Report artifact issues. Report-only unless apply=True. Even with apply,
    we only remove unregistered temp files — we never delete registered content
    or 'fix' hashes silently."""
    report = artifacts.audit(conn)
    actions: list[str] = []
    if apply:
        for tmp in report["unregistered_temp_file"]:
            try:
                os.unlink(tmp)
                actions.append(f"deleted unregistered temp file: {tmp}")
            except OSError as e:
                actions.append(f"could not delete {tmp}: {e}")
    return {"report": report, "applied": apply, "actions": actions}
