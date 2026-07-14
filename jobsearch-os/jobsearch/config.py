"""Loads config.yaml and content/*.yaml once, exposed as module-level dicts."""
from __future__ import annotations

from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


CONFIG: dict = _load_yaml(ROOT / "config.yaml")
PROOF_POINTS: list = _load_yaml(CONTENT_DIR / "proof_points.yaml")["proof_points"]
APPROVED_SWAPS: list = _load_yaml(CONTENT_DIR / "approved_swaps.yaml")["swaps"]
MESSAGING_BANK: dict = _load_yaml(CONTENT_DIR / "messaging_bank.yaml")["categories"]
COVER_LETTER_CONTENT: dict = _load_yaml(CONTENT_DIR / "cover_letter_content.yaml")
STORY_BANK: dict = _load_yaml(CONTENT_DIR / "story_bank.yaml")

DB_PATH = ROOT / "data" / "jobsearch.db"
SCHEMA_PATH = ROOT / "schema.sql"

WEIGHTS: dict = CONFIG["scoring"]["weights"]
CATEGORY_THRESHOLDS: dict = CONFIG["scoring"]["categories"]
BANNED_PHRASES: list = CONFIG["banned_phrases"]
RISKY_FRAMINGS: list = CONFIG.get("risky_framings", [])
TOUCH_OFFSETS: list = CONFIG["outreach"]["touch_offsets_days"]
RECRUITER_TOUCH_OFFSETS: list = CONFIG["outreach"]["recruiter_touch_offsets_days"]
DAILY_CAPS: dict = CONFIG["daily_caps"]
CANDIDATE: dict = CONFIG["candidate"]
RESEARCH_WINDOW_DAYS: int = CONFIG["scoring"]["research_decision_window_days"]
STALE_AFTER_DAYS: int = CONFIG["outreach"]["stale_after_days"]
