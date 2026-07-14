"""Parse a batch-intake file into a list of posting dicts.

Two formats, picked by extension:

1. CSV (.csv) — header row with any of: company, title, jd_text, url,
   location, comp/comp_range. jd_text may contain newlines if quoted.

2. Markdown/text (.md, .txt) — the friendly paste format. Each posting is
   a block introduced by a header line:

       ## Company Name | Job Title | optional-url

   Everything until the next '## ' header (or EOF) is that posting's JD
   text. This lets you paste a whole morning's worth of postings into one
   file without wrestling with CSV quoting.
"""
from __future__ import annotations

import csv
from pathlib import Path

_CSV_ALIASES = {
    "company": "company", "employer": "company",
    "title": "title", "role": "title", "position": "title",
    "jd_text": "jd_text", "jd": "jd_text", "description": "jd_text", "job_description": "jd_text",
    "url": "url", "link": "url",
    "location": "location", "loc": "location",
    "comp": "comp_range", "comp_range": "comp_range", "salary": "comp_range",
}


def _parse_csv(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            row: dict = {}
            for key, val in raw.items():
                if key is None:
                    continue
                canon = _CSV_ALIASES.get(key.strip().lower())
                if canon:
                    row[canon] = (val or "").strip()
            rows.append(row)
    return rows


def _parse_markdown(path: Path) -> list[dict]:
    rows: list[dict] = []
    current: dict | None = None
    body: list[str] = []

    def flush():
        if current is not None:
            current["jd_text"] = "\n".join(body).strip()
            rows.append(current)

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            flush()
            body = []
            parts = [p.strip() for p in line[3:].split("|")]
            current = {
                "company": parts[0] if len(parts) > 0 else "",
                "title": parts[1] if len(parts) > 1 else "",
                "url": parts[2] if len(parts) > 2 else "",
            }
        elif current is not None:
            body.append(line)
    flush()
    return rows


def load_intake_file(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Intake file not found: {path}")
    if path.suffix.lower() == ".csv":
        return _parse_csv(path)
    return _parse_markdown(path)
