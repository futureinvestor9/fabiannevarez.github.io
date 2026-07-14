"""Configuration with a single, tested precedence chain (Section F):

    CLI arguments  >  environment variables  >  YAML config files
                    >  database `settings` table  >  built-in defaults

Every setting is declared once in SETTINGS with its env var name, type, and
default. `Config.get(key, cli=...)` resolves through the chain in order.
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from jobsearch_os.paths import CONFIG_DIR, DEFAULT_DB_PATH


@dataclass(frozen=True)
class Setting:
    key: str
    env: str
    type: str  # "str" | "bool" | "int" | "float" | "path"
    default: Any


SETTINGS: dict[str, Setting] = {
    s.key: s
    for s in [
        Setting("db_path", "JOBSEARCH_DB_PATH", "path", str(DEFAULT_DB_PATH)),
        Setting("budget_mode", "JOBSEARCH_BUDGET_MODE", "str", "normal"),
        Setting("claude_code_enabled", "CLAUDE_CODE_ENABLED", "bool", False),
        Setting("handoffs_enabled", "HANDOFFS_ENABLED", "bool", False),
        Setting("claude_chat_mode", "CLAUDE_CHAT_MODE", "str", "handoff_only"),
        Setting("claude_review_model", "CLAUDE_REVIEW_MODEL", "str", ""),
        Setting("dedupe_similarity_threshold", "JOBSEARCH_DEDUPE_THRESHOLD", "float", 0.85),
    ]
}


def _coerce(value: Any, type_: str) -> Any:
    if value is None:
        return None
    if type_ == "bool":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "on")
    if type_ == "int":
        return int(value)
    if type_ == "float":
        return float(value)
    return str(value)


class Config:
    """Resolves settings through the precedence chain. YAML values are loaded
    from config/*.yaml (flat top-level keys); DB values from a `settings` table
    if one exists on the supplied connection."""

    def __init__(self, conn: sqlite3.Connection | None = None,
                 yaml_values: dict | None = None):
        self._conn = conn
        self._yaml = yaml_values if yaml_values is not None else self._load_yaml()

    @staticmethod
    def _load_yaml() -> dict:
        merged: dict = {}
        if CONFIG_DIR.exists():
            for path in sorted(CONFIG_DIR.glob("*.yaml")):
                try:
                    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                except yaml.YAMLError:
                    continue
                if isinstance(data, dict):
                    # only shallow, top-level scalar keys participate in precedence
                    for k, v in data.items():
                        if not isinstance(v, (dict, list)):
                            merged.setdefault(k, v)
        return merged

    def _db_value(self, key: str) -> Any:
        if self._conn is None:
            return None
        try:
            row = self._conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
        except sqlite3.OperationalError:
            return None  # settings table not migrated yet
        if row is None:
            return None
        return row[0]

    def get(self, key: str, cli: Any = None) -> Any:
        if key not in SETTINGS:
            raise KeyError(f"Unknown setting: {key}")
        spec = SETTINGS[key]
        # 1. CLI
        if cli is not None:
            return _coerce(cli, spec.type)
        # 2. environment
        if spec.env in os.environ and os.environ[spec.env] != "":
            return _coerce(os.environ[spec.env], spec.type)
        # 3. YAML
        if key in self._yaml:
            return _coerce(self._yaml[key], spec.type)
        # 4. DB settings
        db_val = self._db_value(key)
        if db_val is not None:
            return _coerce(db_val, spec.type)
        # 5. default
        return _coerce(spec.default, spec.type)

    def db_path(self, cli: Any = None) -> Path:
        return Path(self.get("db_path", cli=cli))
