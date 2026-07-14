"""Canonical repo paths. Windows-safe (pathlib only, no os.sep literals)."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CONFIG_DIR = REPO_ROOT / "config"
DATA_DIR = REPO_ROOT / "data"
DB_DIR = REPO_ROOT / "db"
MIGRATIONS_DIR = DB_DIR / "migrations"
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
LOGS_DIR = REPO_ROOT / "logs"
DOCS_DIR = REPO_ROOT / "docs"
STATE_DIR = REPO_ROOT / "state"

DEFAULT_DB_PATH = DB_DIR / "jobsearch.db"


def artifacts_root() -> Path:
    """Artifacts directory, overridable via JOBSEARCH_ARTIFACTS_DIR so the
    isolated accept-phase1 harness and tests never touch the real artifacts/."""
    import os
    return Path(os.environ.get("JOBSEARCH_ARTIFACTS_DIR", str(ARTIFACTS_DIR)))
