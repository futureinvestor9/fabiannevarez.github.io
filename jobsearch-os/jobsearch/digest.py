"""The 'morning queue': one ranked, copy-paste-ready digest of everything the
agent has prepared and is waiting on you to send.

This is the closest thing to 'apply on my behalf' that stays inside the
spec's hard gates (B13): the agent has already diagnosed, scored, and
written every artifact. The digest lays them out in priority order so the
human step is reduced to review + click Apply + paste + send. Nothing here
sends anything — it only reads the db and prints.
"""
from __future__ import annotations

import json
import sqlite3

from jobsearch import pipeline


def _latest_score(conn: sqlite3.Connection, job_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM scores WHERE job_id=? ORDER BY score_id DESC LIMIT 1", (job_id,)
    ).fetchone()
    return dict(row) if row else None


def _latest_diagnosis_row(conn: sqlite3.Connection, job_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM diagnoses WHERE job_id=? ORDER BY diagnosis_id DESC LIMIT 1", (job_id,)
    ).fetchone()
    return dict(row) if row else None


def _cover_letter(conn: sqlite3.Connection, job_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM cover_letters WHERE job_id=? ORDER BY cover_letter_id DESC LIMIT 1", (job_id,)
    ).fetchone()
    return dict(row) if row else None


def build_digest(conn: sqlite3.Connection) -> str:
    """Return the full morning-queue digest as plain text."""
    lines: list[str] = []
    out = lines.append

    out("=" * 70)
    out("  MORNING QUEUE — everything prepared and waiting on you")
    out("=" * 70)

    # --- Section 1: Apply queue (ranked Strong/Tailored, not yet applied) ---
    apply_jobs = pipeline.apply_queue(conn)
    out("")
    out(f"### 1. READY TO APPLY ({len(apply_jobs)}) — review, click Apply, paste, submit")
    if not apply_jobs:
        out("    (nothing waiting — ingest + process some postings first)")
    for j in apply_jobs:
        diag = _latest_diagnosis_row(conn, j["job_id"]) or {}
        cl = _cover_letter(conn, j["job_id"])
        age = j.get("age_days", 0)
        overdue = "  <-- >3 days old, prioritize" if age and age > 3 else ""
        out("")
        out(f"  [{j['total']} · {j['category'].upper()}] {j['title']} @ {j['company']}"
            f"  (job_id={j['job_id']}, {age}d old){overdue}")
        if j.get("url"):
            out(f"    Link: {j['url']}")
        if diag.get("recommendation"):
            out(f"    Why: {diag['recommendation']}")
        if diag.get("flags") and diag["flags"] != "[]":
            out(f"    Flags: {', '.join(json.loads(diag['flags']))}")
        if diag.get("language_to_avoid"):
            avoid = json.loads(diag["language_to_avoid"])
            if avoid:
                out(f"    Avoid in interview/letter: {avoid[0]}")
        if cl:
            out("    --- COVER LETTER (paste-ready) " + "-" * 30)
            for para in cl["pasted_version"].split("\n"):
                out(f"    {para}")
            out("    " + "-" * 62)
        out("    Contact research (do the 5-min lookup, then `add-contact`):")
        for c in pipeline.research_checklist_for_job(conn, j["job_id"])[:4]:
            out(f"      - {c}")

    # --- Section 2: Outreach messages ready/ due to send ---
    due = pipeline.due_today(conn)
    drafts = pipeline.approval_queue(conn)["touches"]
    out("")
    out(f"### 2. MESSAGES TO SEND ({len(due)} due, {len(drafts)} awaiting your approval)")
    if due:
        out("  DUE NOW (already approved — copy into LinkedIn/Gmail, send, then `mark-sent`):")
        for t in due:
            out(f"    * Touch {t['touch_number']} -> {t['contact_name']} @ {t['company']} "
                f"({t['channel']}, touch_id={t['touch_id']})")
            for para in t["draft_text"].split("\n"):
                out(f"      {para}")
    if drafts:
        out("  AWAITING APPROVAL (review in dashboard or `approve-touch`):")
        for t in drafts:
            out(f"    * Touch {t['touch_number']} -> {t['contact_name']} @ {t['company']} "
                f"(due {t['date_due']}, touch_id={t['touch_id']})")
    if not due and not drafts:
        out("    (no messages queued — add contacts to Strong/Tailored jobs to generate them)")

    # --- Section 3: Responses needing a reply ---
    resp = pipeline.responses(conn)
    if resp:
        out("")
        out(f"### 3. RESPONSES — reply today ({len(resp)})")
        for r in resp:
            out(f"    * {r['contact_name']} @ {r['company']}: {r['response_summary']}")

    # --- Section 4: Research timers running out ---
    timers = pipeline.research_timers(conn)
    if timers:
        out("")
        out(f"### 4. RESEARCH TIMERS — decide before they expire ({len(timers)})")
        for t in timers:
            out(f"    * {t['title']} @ {t['company']} (score {t['total']}) — {t['days_left']}d left")

    # --- Section 5: Skipped, for the audit trail ---
    skipped = pipeline.skipped_today(conn)
    if skipped:
        out("")
        out(f"### 5. SKIPPED TODAY ({len(skipped)}) — agent filtered these out")
        for s in skipped:
            out(f"    * {s['title']} @ {s['company']}: {s['skip_reason']}")

    out("")
    out("=" * 70)
    out("  Reminder: the agent drafts. You click Apply, solve any CAPTCHA,")
    out("  and hit Send yourself — every time. Then log it with mark-applied /")
    out("  mark-sent so tomorrow's queue and your metrics stay accurate.")
    out("=" * 70)
    return "\n".join(lines)
