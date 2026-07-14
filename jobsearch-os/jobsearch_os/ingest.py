"""Ingestion (Section K) — CSV, manual URL+description, folder markdown/JSON.
Creates a job (stable identity) + immutable job_version v1, computes dedupe
keys, links duplicates to their canonical record. Never deletes duplicates."""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

from jobsearch_os import events
from jobsearch_os.dedupe import find_duplicate
from jobsearch_os.normalize import (
    canonical_url, extract_ats_job_id, description_hash, extract_requirements,
)

_COLUMN_ALIASES = {
    "company": "company", "employer": "company",
    "title": "title", "role": "title", "position": "title",
    "location": "location", "loc": "location",
    "remote_status": "remote_status", "remote": "remote_status",
    "employment_type": "employment_type", "type": "employment_type",
    "salary": "salary_text", "salary_text": "salary_text", "comp": "salary_text",
    "posted_date": "posted_date", "date": "posted_date",
    "url": "url", "link": "url",
    "description": "description", "jd": "description", "job_description": "description",
    "source": "source",
}


def _canonical_record(raw: dict) -> dict:
    rec: dict = {}
    for k, v in raw.items():
        if k is None:
            continue
        canon = _COLUMN_ALIASES.get(str(k).strip().lower())
        if canon:
            rec[canon] = (v or "").strip() if isinstance(v, str) else v
    rec.setdefault("company", "")
    rec.setdefault("title", "")
    rec.setdefault("description", "")
    rec.setdefault("url", "")
    return rec


class IngestError(ValueError):
    pass


def ingest_one(conn: sqlite3.Connection, raw: dict, rules: dict, source: str = "manual") -> dict:
    rec = _canonical_record(raw)
    company, title, description = rec["company"], rec["title"], rec["description"]
    if not company or not title or len((description or "").strip()) < 30:
        raise IngestError("Malformed posting: need company, title, and a description of >=30 chars.")

    curl = canonical_url(rec.get("url", ""))
    ats = extract_ats_job_id(rec.get("url", ""))
    dhash = description_hash(description)
    requirements = extract_requirements(description)

    dup_id, reason = find_duplicate(
        conn, curl, ats, dhash, company, title, rec.get("location", ""), description,
        threshold=float(rules["dedupe_similarity_threshold"]),
    )

    conn.execute("BEGIN")
    try:
        cur = conn.execute(
            "INSERT INTO jobs (status, source, canonical_url, ats_job_id, description_hash, "
            "dedupe_of, dedupe_version) VALUES ('new', ?, ?, ?, ?, ?, ?)",
            (source, curl or None, ats, dhash, dup_id, rules["dedupe_version"]),
        )
        job_id = cur.lastrowid
        vcur = conn.execute(
            "INSERT INTO job_versions (job_id, version_number, company, title, location, "
            "remote_status, employment_type, salary_text, posted_date, source, description, "
            "normalized_requirements, normalized_responsibilities, content_hash) "
            "VALUES (?,1,?,?,?,?,?,?,?,?,?,?,?,?)",
            (job_id, company, title, rec.get("location", ""), rec.get("remote_status", ""),
             rec.get("employment_type", ""), rec.get("salary_text", ""), rec.get("posted_date", ""),
             source, description, json.dumps(requirements), json.dumps([]), dhash),
        )
        version_id = vcur.lastrowid
        conn.execute("UPDATE jobs SET current_version_id = ? WHERE job_id = ?", (version_id, job_id))
        events.record(conn, "ingested", "job", job_id, actor_type="user", actor_id="cli",
                      payload={"source": source, "duplicate_of": dup_id, "dedupe_reason": reason})
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return {"job_id": job_id, "duplicate_of": dup_id, "dedupe_reason": reason}


def ingest_csv(conn: sqlite3.Connection, path: Path, rules: dict) -> list[dict]:
    results = []
    with Path(path).open(newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            try:
                results.append(ingest_one(conn, raw, rules, source="csv"))
            except IngestError as e:
                results.append({"error": str(e), "raw_company": raw.get("company")})
    return results
