"""CLI entry point. Run as `python -m jobsearch.cli <command> ...` from jobsearch-os/.

No command in this file ever sends an email, posts to LinkedIn, or drives a
browser — approve/send/mark-sent all record that a human did that step
themselves (see spec Section B14 NON-GOALS).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jobsearch import pipeline
from jobsearch.db import get_db
from jobsearch.metrics import compute_weekly_metrics
from jobsearch.config import STORY_BANK
from jobsearch.intake import load_intake_file
from jobsearch.digest import build_digest


def cmd_init_db(args):
    conn = get_db()
    print(f"Database ready at {conn.execute('PRAGMA database_list').fetchone()[2]}")


def cmd_intake(args):
    conn = get_db()
    jd_text = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    job_id = pipeline.ingest_job(
        conn, company=args.company, title=args.title, jd_text=jd_text,
        url=args.url or "", location=args.location or "", comp_range=args.comp or "",
        source=args.source or "manual",
    )
    print(f"Ingested job_id={job_id}: {args.title} @ {args.company}")


def _process_new_jobs(conn, job_ids=None, verbose=True):
    if job_ids is None:
        job_ids = [r["job_id"] for r in conn.execute("SELECT job_id FROM jobs WHERE status='new'").fetchall()]
    for job_id in job_ids:
        result = pipeline.process_job(conn, job_id)
        if not verbose:
            continue
        job = pipeline.get_job(conn, job_id)
        print(f"\n=== job_id={job_id}: {job['title']} @ {job['company']} ===")
        print(f"Score: {result['score'].total} ({result['score'].category})"
              + (f"  [raw: {result['score'].raw_category}]" if result['score'].raw_category != result['score'].category else ""))
        if result["score"].downgrade_reasons:
            for r in result["score"].downgrade_reasons:
                print(f"  - {r}")
        print(f"Diagnosis: {result['diagnosis'].recommendation}")
        if result["cover_letter"]:
            print(f"Cover letter drafted (cover_letter_id={result['cover_letter']['cover_letter_id']}), "
                  f"{result['cover_letter']['word_count']} words — awaiting approval.")
    return job_ids


def cmd_process(args):
    conn = get_db()
    job_ids = [args.job_id] if args.job_id else None
    if job_ids is None and not conn.execute("SELECT 1 FROM jobs WHERE status='new' LIMIT 1").fetchone():
        print("No new jobs to process.")
        return
    _process_new_jobs(conn, job_ids)


def cmd_intake_batch(args):
    conn = get_db()
    rows = load_intake_file(args.file)
    result = pipeline.ingest_batch(conn, rows, source=args.source or "batch")
    print(f"Ingested {len(result['ingested'])} new posting(s): job_ids {result['ingested']}")
    if result["duplicates"]:
        print(f"Skipped {len(result['duplicates'])} duplicate(s) (same company+title within 30 days):")
        for d in result["duplicates"]:
            print(f"  - row {d['row']}: {d['title']} @ {d['company']} (already job_id={d['existing_job_id']})")
    if result["malformed"]:
        print(f"Flagged {len(result['malformed'])} malformed row(s) for manual review:")
        for m in result["malformed"]:
            print(f"  - row {m['row']}: {m['reason']}")


def cmd_queue(args):
    conn = get_db()
    print(build_digest(conn))


def cmd_run(args):
    """One-shot morning agent run: batch-intake (optional) -> process all new -> print queue."""
    conn = get_db()
    if args.file:
        rows = load_intake_file(args.file)
        result = pipeline.ingest_batch(conn, rows, source="batch")
        print(f"Ingested {len(result['ingested'])} new, skipped {len(result['duplicates'])} dup, "
              f"{len(result['malformed'])} malformed.")
    n_new = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='new'").fetchone()[0]
    if n_new:
        _process_new_jobs(conn, verbose=False)
        print(f"Processed {n_new} new posting(s).\n")
    print(build_digest(conn))


def cmd_add_contact(args):
    conn = get_db()
    contact_id = pipeline.add_contact(
        conn, job_id=args.job_id, name=args.name, title=args.title or "",
        linkedin_url=args.linkedin or "", email=args.email or "",
        email_source=args.email_source, classification=args.classification,
        why_selected=args.why or "", audience=args.audience,
    )
    print(f"Added contact_id={contact_id} ({args.name}) — 4 touch drafts queued for approval.")


def cmd_approve_touch(args):
    conn = get_db()
    pipeline.approve_touch(conn, args.touch_id, edited_text=args.text)
    print(f"Touch {args.touch_id} approved.")


def cmd_mark_sent(args):
    conn = get_db()
    pipeline.mark_touch_sent(conn, args.touch_id)
    print(f"Touch {args.touch_id} marked sent.")


def cmd_log_response(args):
    conn = get_db()
    pipeline.log_response(conn, args.touch_id, args.summary)
    print(f"Response logged for touch {args.touch_id}; remaining sequence for that contact paused.")


def cmd_mark_applied(args):
    conn = get_db()
    app_id = pipeline.mark_applied(conn, args.job_id, method=args.method,
                                    resume_version=args.resume or "", cover_letter_file=args.cover_letter or "")
    print(f"application_id={app_id} recorded for job_id={args.job_id}.")


def cmd_skip(args):
    conn = get_db()
    pipeline.skip_job(conn, args.job_id, args.reason)
    print(f"job_id={args.job_id} marked skipped: {args.reason}")


def cmd_sweep(args):
    conn = get_db()
    due = pipeline.due_today(conn)
    stale = pipeline.stale_applications(conn)
    research = pipeline.research_timers(conn)
    print(f"Due today: {len(due)}")
    print(f"Stale applications (>= stale threshold): {len(stale)}")
    print(f"Research timers open: {len(research)}")
    for r in research:
        print(f"  - job_id={r['job_id']} {r['company']} / {r['title']}: {r['days_left']} days left")


def cmd_weekly_metrics(args):
    conn = get_db()
    metrics = compute_weekly_metrics(conn)
    print(json.dumps(metrics, indent=2, default=str))


def cmd_dashboard(args):
    from jobsearch.dashboard import create_app
    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)


def cmd_interview_prep(args):
    stories = STORY_BANK["stories"]
    if args.question_type:
        story_id = STORY_BANK["question_type_mapping"].get(args.question_type)
        stories = [s for s in stories if s["id"] == story_id] or stories
    for s in stories:
        print(f"\n=== {s['title']} ===")
        print(f"Situation: {s['situation']}")
        print(f"Task: {s['task']}")
        print(f"Action: {s['action']}")
        print(f"Result: {s['result']}")
        print(f"Proves: {', '.join(s['proves'])}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jobsearch", description="Job-Search Operating System CLI")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("init-db", help="Create/verify the SQLite schema.")
    sp.set_defaults(func=cmd_init_db)

    sp = sub.add_parser("intake", help="Ingest one job posting.")
    sp.add_argument("--company", required=True)
    sp.add_argument("--title", required=True)
    sp.add_argument("--file", help="Path to a text file with the JD. Reads stdin if omitted.")
    sp.add_argument("--url")
    sp.add_argument("--location")
    sp.add_argument("--comp")
    sp.add_argument("--source", default="manual")
    sp.set_defaults(func=cmd_intake)

    sp = sub.add_parser("intake-batch",
                        help="Ingest MANY postings at once from a .csv or .md/.txt file.")
    sp.add_argument("file", help="Path to intake.csv (columns: company,title,jd_text,url,location,comp) "
                                  "or a markdown/text file with '## Company | Title' headers.")
    sp.add_argument("--source", default="batch")
    sp.set_defaults(func=cmd_intake_batch)

    sp = sub.add_parser("process", help="Diagnose + score (+ route) new jobs.")
    sp.add_argument("--job-id", type=int, dest="job_id", help="Process one job; omit to process all status='new'.")
    sp.set_defaults(func=cmd_process)

    sp = sub.add_parser("queue", help="Print the morning queue: everything prepared and waiting on you.")
    sp.set_defaults(func=cmd_queue)

    sp = sub.add_parser("run", help="One-shot morning run: [batch-intake] -> process all new -> print queue.")
    sp.add_argument("--file", help="Optional intake file to batch-ingest first.")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("add-contact", help="Add a contact + generate 4 touch drafts.")
    sp.add_argument("--job-id", type=int, required=True, dest="job_id")
    sp.add_argument("--name", required=True)
    sp.add_argument("--title")
    sp.add_argument("--linkedin")
    sp.add_argument("--email")
    sp.add_argument("--email-source", dest="email_source",
                     choices=["published", "pattern-guess", "given"])
    sp.add_argument("--classification", default="influencer",
                     choices=["decision_maker", "influencer", "same_role", "adjacent",
                              "recruiter", "referral_path", "low_priority"])
    sp.add_argument("--why")
    sp.add_argument("--audience", choices=["crm_manager", "sales_ops", "revops", "ops_ba", "alumni", "other"])
    sp.set_defaults(func=cmd_add_contact)

    sp = sub.add_parser("approve-touch", help="Approve a drafted touch (optionally with edited text).")
    sp.add_argument("touch_id", type=int)
    sp.add_argument("--text", help="Replace the draft text with this edited version.")
    sp.set_defaults(func=cmd_approve_touch)

    sp = sub.add_parser("mark-sent", help="Mark an approved touch as sent (you sent it manually).")
    sp.add_argument("touch_id", type=int)
    sp.set_defaults(func=cmd_mark_sent)

    sp = sub.add_parser("log-response", help="Log a response to a touch; pauses the rest of that contact's sequence.")
    sp.add_argument("touch_id", type=int)
    sp.add_argument("summary")
    sp.set_defaults(func=cmd_log_response)

    sp = sub.add_parser("mark-applied", help="Record that you submitted an application.")
    sp.add_argument("--job-id", type=int, required=True, dest="job_id")
    sp.add_argument("--method", default="ATS", choices=["ATS", "email", "easy-apply"])
    sp.add_argument("--resume")
    sp.add_argument("--cover-letter", dest="cover_letter")
    sp.set_defaults(func=cmd_mark_applied)

    sp = sub.add_parser("skip", help="Manually skip a job with a reason.")
    sp.add_argument("--job-id", type=int, required=True, dest="job_id")
    sp.add_argument("--reason", required=True)
    sp.set_defaults(func=cmd_skip)

    sp = sub.add_parser("sweep", help="Nightly sweep: due-today / stale / research-timer counts.")
    sp.set_defaults(func=cmd_sweep)

    sp = sub.add_parser("weekly-metrics", help="Compute and store this week's B9 metrics.")
    sp.set_defaults(func=cmd_weekly_metrics)

    sp = sub.add_parser("dashboard", help="Run the local Flask dashboard.")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=5000)
    sp.add_argument("--debug", action="store_true")
    sp.set_defaults(func=cmd_dashboard)

    sp = sub.add_parser("interview-prep", help="Print STAR stories (optionally filtered by question type).")
    sp.add_argument("--question-type", dest="question_type",
                     choices=list(STORY_BANK["question_type_mapping"].keys()))
    sp.set_defaults(func=cmd_interview_prep)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
