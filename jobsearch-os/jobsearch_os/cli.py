"""CLI (Section R). Run: `python -m jobsearch_os.cli <command> ...`

No command performs an external action. approve/mark-submitted only record
that the human acted (Invariants 1, 5).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jobsearch_os import (
    db, migrations, ingest, flow, scoring, packet, profile, review_service, doctor, events,
)
from jobsearch_os.config import Config


def _open_db(cli_db_path: str | None = None):
    cfg = Config()
    path = Path(cli_db_path) if cli_db_path else cfg.db_path()
    conn = db.connect(path)
    migrations.migrate(conn)
    return conn


def cmd_doctor(args):
    conn = _open_db(args.db)
    profile.seed_facts(conn)
    env = doctor.environment_report(conn)
    print(json.dumps(env, indent=2))
    if args.repair_artifacts:
        result = doctor.repair_artifacts(conn, apply=args.apply)
        print("\n--repair-artifacts (%s):" % ("APPLY" if args.apply else "report-only"))
        print(json.dumps(result, indent=2))
    return 0


def cmd_init_db(args):
    conn = _open_db(args.db)
    n = profile.seed_facts(conn)
    print(f"Database ready. Seeded {n} candidate fact(s).")
    return 0


def cmd_migrate(args):
    conn = _open_db(args.db)
    applied = migrations.migrate(conn)
    print("Applied:", applied or "nothing pending")
    return 0


def cmd_ingest(args):
    conn = _open_db(args.db)
    rules = scoring.load_rules()
    results = ingest.ingest_csv(conn, Path(args.csv), rules)
    ok = [r for r in results if "job_id" in r]
    errs = [r for r in results if "error" in r]
    print(f"Ingested {len(ok)} posting(s); {len(errs)} malformed.")
    for r in ok:
        note = f" (duplicate of {r['duplicate_of']} via {r['dedupe_reason']})" if r["duplicate_of"] else ""
        print(f"  job_id={r['job_id']}{note}")
    for e in errs:
        print(f"  malformed: {e['error']}")
    return 0


def cmd_add_job(args):
    conn = _open_db(args.db)
    rules = scoring.load_rules()
    description = Path(args.description_file).read_text(encoding="utf-8")
    res = ingest.ingest_one(conn, {"company": args.company, "title": args.title,
                                    "description": description, "url": args.url,
                                    "location": args.location or ""}, rules, source="manual")
    print(f"Ingested job_id={res['job_id']}"
          + (f" (duplicate of {res['duplicate_of']})" if res["duplicate_of"] else ""))
    return 0


def cmd_score(args):
    conn = _open_db(args.db)
    rules = scoring.load_rules()
    new_jobs = [r["job_id"] for r in conn.execute("SELECT job_id FROM jobs WHERE status='new'").fetchall()]
    if args.limit:
        new_jobs = new_jobs[: args.limit]
    for job_id in new_jobs:
        res = flow.process_job(conn, job_id, rules)
        if res["status"] == "scored":
            pres = packet.build_packet(conn, job_id, rules)
            print(f"job_id={job_id}: score {res['score']} ({res['band']}) -> packet {pres.status}"
                  + (f" packet_id={pres.packet_id}" if pres.packet_id else f" (gate: {pres.gate_failures})"))
        else:
            print(f"job_id={job_id}: {res['status']}")
    return 0


def cmd_review_export(args):
    conn = _open_db(args.db)
    rows = conn.execute(
        "SELECT p.packet_id, p.job_id, p.version_number, p.status, p.score_total, "
        "v.company, v.title FROM application_packets p "
        "JOIN jobs j ON j.job_id=p.job_id JOIN job_versions v ON v.version_id=j.current_version_id "
        "WHERE p.status IN ('packet_ready','approval_pending') ORDER BY p.score_total DESC"
    ).fetchall()
    export = [dict(r) for r in rows]
    blocked = [dict(q) for q in profile.open_blocked_questions(conn)]
    out = {"packets_for_review": export, "open_blocked_questions": blocked}
    print(json.dumps(out, indent=2))
    return 0


def _resolve_packet(conn, args):
    if args.type != "packet":
        raise SystemExit("Phase 1 only supports --type packet")
    return args.id


def cmd_submit_for_review(args):
    conn = _open_db(args.db)
    review_service.submit_for_review(conn, args.id)
    print(f"packet {args.id} submitted for review.")
    return 0


def cmd_approve(args):
    conn = _open_db(args.db)
    pid = _resolve_packet(conn, args)
    approval_id = review_service.approve(conn, pid, expected_content_hash=args.expect_hash)
    print(f"packet {pid} approved (approval_id={approval_id}). "
          f"Apply manually, then `mark-submitted --packet-id {pid}`.")
    return 0


def cmd_revise(args):
    conn = _open_db(args.db)
    pid = _resolve_packet(conn, args)
    review_service.revise(conn, pid, note=args.note or "")
    print(f"packet {pid} sent back to drafting; any approval invalidated.")
    return 0


def cmd_reject(args):
    conn = _open_db(args.db)
    pid = _resolve_packet(conn, args)
    review_service.reject(conn, pid, note=args.note or "")
    print(f"packet {pid} rejected and closed.")
    return 0


def cmd_mark_submitted(args):
    conn = _open_db(args.db)
    try:
        review_service.mark_submitted(conn, args.packet_id)
    except review_service.ApprovalRequired as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        return 2
    print(f"packet {args.packet_id} marked submitted (you did this manually).")
    return 0


def cmd_confirm_fact(args):
    conn = _open_db(args.db)
    fact_id = profile.confirm_fact(conn, args.question_id, args.answer)
    print(f"Recorded {fact_id} for question {args.question_id}.")
    return 0


def cmd_accept_phase1(args):
    from jobsearch_os import accept_phase1
    passed, workspace, report = accept_phase1.run(keep_temp=args.keep_temp)
    print(json.dumps(report, indent=2))
    print("\nRESULT:", "PASS" if passed else "FAIL")
    if not passed:
        print(f"Workspace preserved for inspection: {workspace}", file=sys.stderr)
    return 0 if passed else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jobsearch-os", description="Job-Search OS (v6) — Phase 1 CLI")
    p.add_argument("--db", help="Override the database path (highest precedence).")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("doctor", help="Environment + artifact health report.")
    sp.add_argument("--repair-artifacts", action="store_true", dest="repair_artifacts")
    sp.add_argument("--apply", action="store_true", help="Apply repairs (default report-only).")
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("init-db", help="Create/verify schema; seed candidate facts.")
    sp.set_defaults(func=cmd_init_db)

    sp = sub.add_parser("migrate", help="Apply pending migrations.")
    sp.set_defaults(func=cmd_migrate)

    sp = sub.add_parser("ingest", help="Ingest a CSV of postings.")
    sp.add_argument("--csv", required=True)
    sp.set_defaults(func=cmd_ingest)

    sp = sub.add_parser("add-job", help="Ingest one posting (URL + description file).")
    sp.add_argument("--company", required=True)
    sp.add_argument("--title", required=True)
    sp.add_argument("--url", default="")
    sp.add_argument("--location", default="")
    sp.add_argument("--description-file", required=True, dest="description_file")
    sp.set_defaults(func=cmd_add_job)

    sp = sub.add_parser("score", help="Process new jobs: score + build packets.")
    sp.add_argument("--limit", type=int)
    sp.set_defaults(func=cmd_score)

    sp = sub.add_parser("review-export", help="Dump packets awaiting review + blocked questions.")
    sp.set_defaults(func=cmd_review_export)

    sp = sub.add_parser("submit-for-review", help="Move a packet_ready packet into the review queue.")
    sp.add_argument("--packet-id", type=int, required=True, dest="id")
    sp.set_defaults(func=cmd_submit_for_review)

    for name, func, helptext in (
        ("approve", cmd_approve, "Approve a packet (version+hash locked)."),
        ("revise", cmd_revise, "Send a packet back to drafting (invalidates approval)."),
        ("reject", cmd_reject, "Reject and close a packet."),
    ):
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("--type", default="packet", choices=["packet"])
        sp.add_argument("--id", type=int, required=True)
        sp.add_argument("--note")
        if name == "approve":
            sp.add_argument("--expect-hash", dest="expect_hash",
                            help="Content hash you reviewed; approval refuses if it changed.")
        sp.set_defaults(func=func)

    sp = sub.add_parser("mark-submitted", help="Record that YOU submitted manually (blocked pre-approval).")
    sp.add_argument("--packet-id", type=int, required=True, dest="packet_id")
    sp.set_defaults(func=cmd_mark_submitted)

    sp = sub.add_parser("confirm-fact", help="Answer a blocked sensitive question -> records a FACT.")
    sp.add_argument("--question-id", type=int, required=True, dest="question_id")
    sp.add_argument("--answer", required=True)
    sp.set_defaults(func=cmd_confirm_fact)

    sp = sub.add_parser("accept-phase1", help="Isolated end-to-end Phase-1 acceptance run.")
    sp.add_argument("--keep-temp", action="store_true", dest="keep_temp")
    sp.set_defaults(func=cmd_accept_phase1)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
