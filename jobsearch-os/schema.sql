-- Job-Search Operating System schema (see docs/spec.md Section B10)
-- SQLite dialect.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS jobs (
    job_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date_found      TEXT NOT NULL DEFAULT (date('now')),
    source          TEXT,
    company         TEXT NOT NULL,
    title           TEXT NOT NULL,
    url             TEXT,
    location        TEXT,
    comp_range      TEXT,
    jd_text         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'new'
                    CHECK (status IN ('new','diagnosed','scored','applied',
                                       'interviewing','closed','skipped')),
    skip_reason     TEXT
);

CREATE TABLE IF NOT EXISTS diagnoses (
    diagnosis_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id               INTEGER NOT NULL REFERENCES jobs(job_id),
    likely_struggle      TEXT,
    role_problem         TEXT,
    messy_systems        TEXT,
    success_90d          TEXT,
    success_6mo          TEXT,
    matching_background  TEXT,
    proof_points         TEXT,   -- JSON list, max 3 proof point ids
    language_to_avoid    TEXT,
    value_prop_paragraph TEXT,
    recommendation       TEXT,   -- Apply / Tailored Apply / Research More / Skip
    flags                TEXT,   -- JSON list: PIPELINE_LEAKAGE / RCM_HEALTHCARE / ADMIN_CERT_REQUIRED / SENIOR_SCOPE
    created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scores (
    score_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id               INTEGER NOT NULL REFERENCES jobs(job_id),
    d1 REAL, d2 REAL, d3 REAL, d4 REAL, d5 REAL, d6 REAL,
    d7 REAL, d8 REAL, d9 REAL, d10 REAL, d11 REAL, d12 REAL,
    total                REAL NOT NULL,
    category             TEXT NOT NULL CHECK (category IN
                           ('strong','tailored','research','skip')),
    raw_category         TEXT,   -- category before flag-based downgrade
    downgrade_reason     TEXT,
    scored_date          TEXT NOT NULL DEFAULT (date('now')),
    research_deadline    TEXT
);

CREATE TABLE IF NOT EXISTS cover_letters (
    cover_letter_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id            INTEGER NOT NULL REFERENCES jobs(job_id),
    opening_sentence  TEXT NOT NULL,
    body              TEXT NOT NULL,
    pasted_version    TEXT NOT NULL,
    approved          INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS applications (
    app_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id               INTEGER NOT NULL REFERENCES jobs(job_id),
    date_applied         TEXT NOT NULL DEFAULT (date('now')),
    method               TEXT CHECK (method IN ('ATS','email','easy-apply')),
    resume_version       TEXT,
    cover_letter_file    TEXT,
    pasted_version_used  INTEGER DEFAULT 0,
    status               TEXT NOT NULL DEFAULT 'submitted'
                          CHECK (status IN ('submitted','screen','interview',
                                              'offer','rejected','ghost','withdrawn'))
);

CREATE TABLE IF NOT EXISTS contacts (
    contact_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id            INTEGER NOT NULL REFERENCES jobs(job_id),
    company           TEXT,
    name              TEXT NOT NULL,
    title             TEXT,
    linkedin_url      TEXT,
    email             TEXT,
    email_source      TEXT CHECK (email_source IN
                        ('published','pattern-guess','given') OR email_source IS NULL),
    classification    TEXT CHECK (classification IN
                        ('decision_maker','influencer','same_role','adjacent',
                         'recruiter','referral_path','low_priority')),
    why_selected      TEXT,
    status            TEXT NOT NULL DEFAULT 'active'
                       CHECK (status IN ('active','responded','closed_polite','paused')),
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS touches (
    touch_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id      INTEGER NOT NULL REFERENCES contacts(contact_id),
    touch_number    INTEGER NOT NULL CHECK (touch_number BETWEEN 1 AND 4),
    channel         TEXT NOT NULL CHECK (channel IN
                      ('linkedin_cr','linkedin_msg','email')),
    draft_text      TEXT NOT NULL,
    template_id     TEXT,
    status          TEXT NOT NULL DEFAULT 'draft'
                     CHECK (status IN ('draft','approved','sent','responded','skipped','closed')),
    date_due        TEXT,
    date_sent       TEXT,
    date_responded  TEXT,
    response_summary TEXT
);

CREATE TABLE IF NOT EXISTS templates (
    template_id   TEXT PRIMARY KEY,
    touch_number  INTEGER,
    audience_class TEXT,
    body          TEXT,
    times_used    INTEGER NOT NULL DEFAULT 0,
    responses     INTEGER NOT NULL DEFAULT 0,
    retired       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS weekly_metrics (
    week_start                TEXT PRIMARY KEY,
    jobs_sourced              INTEGER,
    jobs_scored               INTEGER,
    strong_applies_found      INTEGER,
    jobs_applied              INTEGER,
    cover_letters_generated   INTEGER,
    contacts_identified       INTEGER,
    t1_sent                   INTEGER,
    total_touches_sent        INTEGER,
    emails_sent               INTEGER,
    responses_received        INTEGER,
    positive_responses        INTEGER,
    calls_booked              INTEGER,
    interviews_booked         INTEGER,
    rejections                INTEGER,
    ghosts                    INTEGER,
    response_rate_by_touch    TEXT,  -- JSON
    response_rate_by_class    TEXT,  -- JSON
    application_to_interview_rate REAL,
    strong_apply_to_interview_rate REAL,
    best_titles               TEXT,  -- JSON
    best_industries           TEXT,  -- JSON
    best_template             TEXT,
    top_skip_reasons          TEXT,  -- JSON
    avg_score_responded       REAL,
    avg_score_no_response      REAL,
    computed_at               TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Views -----------------------------------------------------------------

CREATE VIEW IF NOT EXISTS approval_queue_touches AS
    SELECT touch_id, contact_id, touch_number, channel, draft_text, date_due
    FROM touches
    WHERE status = 'draft';

CREATE VIEW IF NOT EXISTS approval_queue_letters AS
    SELECT cover_letter_id, job_id, opening_sentence, body
    FROM cover_letters
    WHERE approved = 0;

CREATE VIEW IF NOT EXISTS due_today AS
    SELECT touch_id, contact_id, touch_number, channel, draft_text, date_due
    FROM touches
    WHERE status = 'approved' AND date_due <= date('now');
