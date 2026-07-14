"""Artifact lifecycle (Section I): write to a temp file, `os.replace` into an
immutable permanent path under artifacts/, THEN register in the DB. Registered
artifacts never move; their review status lives in SQLite, never in the folder.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import tempfile
from pathlib import Path

from jobsearch_os.paths import ARTIFACTS_DIR


class ArtifactImmutabilityError(RuntimeError):
    pass


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        os.replace(tmp_name, path)  # atomic within the same filesystem
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def write_and_register(
    conn: sqlite3.Connection,
    artifact_type: str,
    subject_type: str,
    subject_id: int,
    path: Path,
    content: str,
    parent_artifact_id: int | None = None,
    prompt_version: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> tuple[int, str]:
    """Write immutably and register. Returns (artifact_id, content_hash).

    Idempotent for identical content at the same path. Writing DIFFERENT content
    to an already-registered path raises (immutability) — new versions must use
    a new path."""
    path = Path(path)
    chash = content_hash(content)

    existing = conn.execute(
        "SELECT id, content_hash FROM artifacts WHERE path = ?", (str(path),)
    ).fetchone()
    if existing is not None:
        if existing["content_hash"] != chash:
            raise ArtifactImmutabilityError(
                f"Refusing to overwrite registered artifact {path} with different content. "
                "Registered artifacts are immutable; write a new version to a new path."
            )
        return existing["id"], chash

    _atomic_write(path, content)
    cur = conn.execute(
        "INSERT INTO artifacts (artifact_type, subject_type, subject_id, path, content_hash, "
        "parent_artifact_id, prompt_version, provider, model) VALUES (?,?,?,?,?,?,?,?,?)",
        (artifact_type, subject_type, subject_id, str(path), chash,
         parent_artifact_id, prompt_version, provider, model),
    )
    return cur.lastrowid, chash


def audit(conn: sqlite3.Connection, artifacts_root: Path | None = None) -> dict[str, list[str]]:
    """Report-only artifact health (doctor --repair-artifacts). Categories:
    orphaned_file, missing_file, hash_mismatch, unregistered_temp_file,
    duplicate_artifact_row."""
    root = artifacts_root or ARTIFACTS_DIR
    report: dict[str, list[str]] = {
        "orphaned_file": [], "missing_file": [], "hash_mismatch": [],
        "unregistered_temp_file": [], "duplicate_artifact_row": [],
    }
    rows = conn.execute("SELECT id, path, content_hash FROM artifacts").fetchall()
    registered_paths = {}
    seen_path_counts: dict[str, int] = {}
    for r in rows:
        seen_path_counts[r["path"]] = seen_path_counts.get(r["path"], 0) + 1
        registered_paths[r["path"]] = r["content_hash"]
        p = Path(r["path"])
        if not p.exists():
            report["missing_file"].append(r["path"])
        else:
            if content_hash(p.read_text(encoding="utf-8")) != r["content_hash"]:
                report["hash_mismatch"].append(r["path"])
    for path, count in seen_path_counts.items():
        if count > 1:
            report["duplicate_artifact_row"].append(path)

    if root.exists():
        for f in root.rglob("*"):
            if f.is_dir():
                continue
            if f.name == ".gitkeep":
                continue
            if f.suffix == ".tmp":
                report["unregistered_temp_file"].append(str(f))
            elif str(f) not in registered_paths:
                report["orphaned_file"].append(str(f))
    return report
