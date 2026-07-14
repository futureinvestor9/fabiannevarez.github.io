"""B9 weekly metrics: volume, outcomes, conversion rates, learning signals.

Some B9 fields (industry performance, exact week-of-status-change outcome
counts) would need schema fields the spec's B10 tables don't carry (no
`jobs.industry`, no status-change history). Rather than fabricate numbers
from data that isn't there, this module computes everything it honestly
can from the schema and returns an explicit empty/None with a note for the
rest — see NOT_TRACKED below.
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3

NOT_TRACKED = "not tracked in v1 — schema has no jobs.industry / status-change history field"


def _week_bounds(week_start: dt.date | None) -> tuple[str, str]:
    if week_start is None:
        today = dt.date.today()
        week_start = today - dt.timedelta(days=today.weekday())
    week_end = week_start + dt.timedelta(days=7)
    return week_start.isoformat(), week_end.isoformat()


def _scalar(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> int:
    row = conn.execute(sql, params).fetchone()
    return row[0] if row and row[0] is not None else 0


def compute_weekly_metrics(conn: sqlite3.Connection, week_start: dt.date | None = None) -> dict:
    start, end = _week_bounds(week_start)

    jobs_sourced = _scalar(conn, "SELECT COUNT(*) FROM jobs WHERE date_found >= ? AND date_found < ?", (start, end))
    jobs_scored = _scalar(conn, "SELECT COUNT(*) FROM scores WHERE scored_date >= ? AND scored_date < ?", (start, end))
    strong_applies_found = _scalar(
        conn,
        "SELECT COUNT(*) FROM scores WHERE category='strong' AND scored_date >= ? AND scored_date < ?",
        (start, end),
    )
    jobs_applied = _scalar(
        conn, "SELECT COUNT(*) FROM applications WHERE date_applied >= ? AND date_applied < ?", (start, end)
    )
    cover_letters_generated = _scalar(
        conn, "SELECT COUNT(*) FROM cover_letters WHERE substr(created_at,1,10) >= ? AND substr(created_at,1,10) < ?",
        (start, end),
    )
    contacts_identified = _scalar(
        conn, "SELECT COUNT(*) FROM contacts WHERE substr(created_at,1,10) >= ? AND substr(created_at,1,10) < ?",
        (start, end),
    )
    t1_sent = _scalar(
        conn,
        "SELECT COUNT(*) FROM touches WHERE touch_number=1 AND date_sent >= ? AND date_sent < ?",
        (start, end),
    )
    total_touches_sent = _scalar(
        conn, "SELECT COUNT(*) FROM touches WHERE date_sent >= ? AND date_sent < ?", (start, end)
    )
    emails_sent = _scalar(
        conn,
        "SELECT COUNT(*) FROM touches WHERE channel='email' AND date_sent >= ? AND date_sent < ?",
        (start, end),
    )
    responses_received = _scalar(
        conn, "SELECT COUNT(*) FROM touches WHERE date_responded >= ? AND date_responded < ?", (start, end)
    )

    positive_keywords = ["yes", "interested", "sure", "let's", "schedule", "call", "sounds good", "happy to"]
    responded_rows = conn.execute(
        "SELECT response_summary FROM touches WHERE date_responded >= ? AND date_responded < ?", (start, end)
    ).fetchall()
    positive_responses = sum(
        1 for r in responded_rows
        if r["response_summary"] and any(k in r["response_summary"].lower() for k in positive_keywords)
    )

    calls_booked = _scalar(conn, "SELECT COUNT(*) FROM applications WHERE status='screen'")
    interviews_booked = _scalar(conn, "SELECT COUNT(*) FROM applications WHERE status='interview'")
    rejections = _scalar(conn, "SELECT COUNT(*) FROM applications WHERE status='rejected'")
    ghosts = _scalar(conn, "SELECT COUNT(*) FROM applications WHERE status='ghost'")

    response_rate_by_touch = {}
    for n in (1, 2, 3, 4):
        sent = _scalar(conn, "SELECT COUNT(*) FROM touches WHERE touch_number=? AND date_sent IS NOT NULL", (n,))
        responded = _scalar(
            conn, "SELECT COUNT(*) FROM touches WHERE touch_number=? AND status='responded'", (n,)
        )
        response_rate_by_touch[n] = round(responded / sent, 3) if sent else None

    response_rate_by_class = {}
    for row in conn.execute("SELECT DISTINCT classification FROM contacts").fetchall():
        cls = row["classification"]
        total = _scalar(conn, "SELECT COUNT(*) FROM contacts WHERE classification=?", (cls,))
        responded = _scalar(
            conn, "SELECT COUNT(*) FROM contacts WHERE classification=? AND status='responded'", (cls,)
        )
        response_rate_by_class[cls or "unknown"] = round(responded / total, 3) if total else None

    total_apps = _scalar(conn, "SELECT COUNT(*) FROM applications")
    apps_interviewed = _scalar(
        conn, "SELECT COUNT(*) FROM applications WHERE status IN ('interview','offer')"
    )
    application_to_interview_rate = round(apps_interviewed / total_apps, 3) if total_apps else None

    strong_jobs = _scalar(conn, "SELECT COUNT(*) FROM scores WHERE category='strong'")
    strong_jobs_interviewed = _scalar(
        conn,
        "SELECT COUNT(DISTINCT a.job_id) FROM applications a JOIN scores s ON s.job_id=a.job_id "
        "WHERE s.category='strong' AND a.status IN ('interview','offer')",
    )
    strong_apply_to_interview_rate = round(strong_jobs_interviewed / strong_jobs, 3) if strong_jobs else None

    best_titles_rows = conn.execute(
        "SELECT j.title, COUNT(DISTINCT c.contact_id) AS n, "
        "SUM(CASE WHEN c.status='responded' THEN 1 ELSE 0 END) AS responded "
        "FROM jobs j JOIN contacts c ON c.job_id=j.job_id GROUP BY j.title HAVING n >= 1"
    ).fetchall()
    best_titles = sorted(
        [
            {"title": r["title"], "n": r["n"], "response_rate": round(r["responded"] / r["n"], 3)}
            for r in best_titles_rows
        ],
        key=lambda x: x["response_rate"],
        reverse=True,
    )

    template_rows = conn.execute(
        "SELECT template_id, times_used, responses FROM templates WHERE retired=0 AND times_used >= 5"
    ).fetchall()
    best_template = None
    if template_rows:
        ranked = sorted(template_rows, key=lambda r: r["responses"] / r["times_used"], reverse=True)
        top = ranked[0]
        best_template = {
            "template_id": top["template_id"],
            "times_used": top["times_used"],
            "responses": top["responses"],
            "response_rate": round(top["responses"] / top["times_used"], 3),
        }

    skip_rows = conn.execute(
        "SELECT skip_reason, COUNT(*) AS n FROM jobs WHERE status='skipped' "
        "AND date_found >= ? AND date_found < ? AND skip_reason IS NOT NULL "
        "GROUP BY skip_reason ORDER BY n DESC",
        (start, end),
    ).fetchall()
    top_skip_reasons = [{"reason": r["skip_reason"], "n": r["n"]} for r in skip_rows]

    avg_responded = conn.execute(
        "SELECT AVG(s.total) FROM scores s WHERE s.job_id IN "
        "(SELECT j.job_id FROM jobs j JOIN contacts c ON c.job_id=j.job_id WHERE c.status='responded')"
    ).fetchone()[0]
    avg_no_response = conn.execute(
        "SELECT AVG(s.total) FROM scores s WHERE s.job_id IN "
        "(SELECT j.job_id FROM jobs j JOIN contacts c ON c.job_id=j.job_id WHERE c.status!='responded')"
    ).fetchone()[0]

    metrics = {
        "week_start": start,
        "jobs_sourced": jobs_sourced,
        "jobs_scored": jobs_scored,
        "strong_applies_found": strong_applies_found,
        "jobs_applied": jobs_applied,
        "cover_letters_generated": cover_letters_generated,
        "contacts_identified": contacts_identified,
        "t1_sent": t1_sent,
        "total_touches_sent": total_touches_sent,
        "emails_sent": emails_sent,
        "responses_received": responses_received,
        "positive_responses": positive_responses,
        "calls_booked": calls_booked,
        "interviews_booked": interviews_booked,
        "rejections": rejections,
        "ghosts": ghosts,
        "response_rate_by_touch": response_rate_by_touch,
        "response_rate_by_class": response_rate_by_class,
        "application_to_interview_rate": application_to_interview_rate,
        "strong_apply_to_interview_rate": strong_apply_to_interview_rate,
        "best_titles": best_titles,
        "best_industries": NOT_TRACKED,
        "best_template": best_template,
        "top_skip_reasons": top_skip_reasons,
        "avg_score_responded": round(avg_responded, 1) if avg_responded is not None else None,
        "avg_score_no_response": round(avg_no_response, 1) if avg_no_response is not None else None,
    }

    conn.execute(
        "INSERT INTO weekly_metrics (week_start, jobs_sourced, jobs_scored, strong_applies_found, "
        "jobs_applied, cover_letters_generated, contacts_identified, t1_sent, total_touches_sent, "
        "emails_sent, responses_received, positive_responses, calls_booked, interviews_booked, "
        "rejections, ghosts, response_rate_by_touch, response_rate_by_class, "
        "application_to_interview_rate, strong_apply_to_interview_rate, best_titles, best_industries, "
        "best_template, top_skip_reasons, avg_score_responded, avg_score_no_response) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(week_start) DO UPDATE SET "
        "jobs_sourced=excluded.jobs_sourced, jobs_scored=excluded.jobs_scored, "
        "strong_applies_found=excluded.strong_applies_found, jobs_applied=excluded.jobs_applied, "
        "cover_letters_generated=excluded.cover_letters_generated, "
        "contacts_identified=excluded.contacts_identified, t1_sent=excluded.t1_sent, "
        "total_touches_sent=excluded.total_touches_sent, emails_sent=excluded.emails_sent, "
        "responses_received=excluded.responses_received, positive_responses=excluded.positive_responses, "
        "calls_booked=excluded.calls_booked, interviews_booked=excluded.interviews_booked, "
        "rejections=excluded.rejections, ghosts=excluded.ghosts, "
        "response_rate_by_touch=excluded.response_rate_by_touch, "
        "response_rate_by_class=excluded.response_rate_by_class, "
        "application_to_interview_rate=excluded.application_to_interview_rate, "
        "strong_apply_to_interview_rate=excluded.strong_apply_to_interview_rate, "
        "best_titles=excluded.best_titles, best_industries=excluded.best_industries, "
        "best_template=excluded.best_template, top_skip_reasons=excluded.top_skip_reasons, "
        "avg_score_responded=excluded.avg_score_responded, "
        "avg_score_no_response=excluded.avg_score_no_response, computed_at=datetime('now')",
        (
            metrics["week_start"], metrics["jobs_sourced"], metrics["jobs_scored"],
            metrics["strong_applies_found"], metrics["jobs_applied"], metrics["cover_letters_generated"],
            metrics["contacts_identified"], metrics["t1_sent"], metrics["total_touches_sent"],
            metrics["emails_sent"], metrics["responses_received"], metrics["positive_responses"],
            metrics["calls_booked"], metrics["interviews_booked"], metrics["rejections"], metrics["ghosts"],
            json.dumps(metrics["response_rate_by_touch"]), json.dumps(metrics["response_rate_by_class"]),
            metrics["application_to_interview_rate"], metrics["strong_apply_to_interview_rate"],
            json.dumps(metrics["best_titles"]), json.dumps(metrics["best_industries"]),
            json.dumps(metrics["best_template"]), json.dumps(metrics["top_skip_reasons"]),
            metrics["avg_score_responded"], metrics["avg_score_no_response"],
        ),
    )
    conn.commit()
    return metrics
