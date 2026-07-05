"""B8 daily dashboard: a local Flask app, queue-ordered, server-rendered.

Every action route only ever writes a status change to the local SQLite
db — approve/edit/skip/mark-sent/log-response. No route sends an email,
posts to LinkedIn, or drives a browser. "Mark sent" exists because *you*
sent it by hand and are telling the system so it can schedule the next
touch and compute metrics.
"""
from __future__ import annotations

from flask import Flask, render_template, request, redirect, url_for

from jobsearch import pipeline
from jobsearch.db import get_db
from jobsearch.metrics import compute_weekly_metrics
from jobsearch.config import DAILY_CAPS


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        conn = get_db()
        data = {
            "due_today": pipeline.due_today(conn),
            "approval_queue": pipeline.approval_queue(conn),
            "new_today": pipeline.new_jobs_today(conn),
            "apply_queue": pipeline.apply_queue(conn),
            "responses": pipeline.responses(conn),
            "stale": pipeline.stale_applications(conn),
            "research_timers": pipeline.research_timers(conn),
            "skipped_today": pipeline.skipped_today(conn),
            "top_opportunities": pipeline.top_open_opportunities(conn),
            "daily_caps": DAILY_CAPS,
        }
        return render_template("dashboard.html", **data)

    @app.route("/weekly")
    def weekly():
        conn = get_db()
        metrics = compute_weekly_metrics(conn)
        return render_template("weekly.html", metrics=metrics)

    @app.route("/touch/<int:touch_id>/approve", methods=["POST"])
    def approve_touch(touch_id):
        conn = get_db()
        edited = request.form.get("draft_text") or None
        pipeline.approve_touch(conn, touch_id, edited_text=edited)
        return redirect(url_for("index"))

    @app.route("/touch/<int:touch_id>/skip", methods=["POST"])
    def skip_touch(touch_id):
        conn = get_db()
        pipeline.skip_touch(conn, touch_id)
        return redirect(url_for("index"))

    @app.route("/touch/<int:touch_id>/mark-sent", methods=["POST"])
    def mark_sent(touch_id):
        conn = get_db()
        pipeline.mark_touch_sent(conn, touch_id)
        return redirect(url_for("index"))

    @app.route("/touch/<int:touch_id>/respond", methods=["POST"])
    def respond(touch_id):
        conn = get_db()
        summary = request.form.get("summary", "")
        pipeline.log_response(conn, touch_id, summary)
        return redirect(url_for("index"))

    @app.route("/cover-letter/<int:cover_letter_id>/approve", methods=["POST"])
    def approve_cover_letter(cover_letter_id):
        conn = get_db()
        edited = request.form.get("body") or None
        pipeline.approve_cover_letter(conn, cover_letter_id, edited_body=edited)
        return redirect(url_for("index"))

    @app.route("/job/<int:job_id>/skip", methods=["POST"])
    def skip_job(job_id):
        conn = get_db()
        reason = request.form.get("reason", "manual skip from dashboard")
        pipeline.skip_job(conn, job_id, reason)
        return redirect(url_for("index"))

    @app.route("/job/<int:job_id>/mark-applied", methods=["POST"])
    def mark_applied(job_id):
        conn = get_db()
        method = request.form.get("method", "ATS")
        pipeline.mark_applied(conn, job_id, method=method)
        return redirect(url_for("index"))

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
