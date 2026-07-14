-- 0001_core.sql — Phase 1 core tables (Section G / Section I).
-- No semicolons inside statements other than the terminators.

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL DEFAULT 'new',
    source TEXT,
    canonical_url TEXT,
    ats_job_id TEXT,
    description_hash TEXT,
    current_version_id INTEGER,
    dedupe_of INTEGER REFERENCES jobs(job_id) ON DELETE SET NULL,
    dedupe_version TEXT,
    skip_reason TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE job_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    company TEXT,
    title TEXT,
    location TEXT,
    remote_status TEXT,
    employment_type TEXT,
    salary_text TEXT,
    posted_date TEXT,
    source TEXT,
    description TEXT NOT NULL,
    normalized_requirements TEXT,
    normalized_responsibilities TEXT,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE (job_id, version_number)
);

CREATE TABLE artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_type TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    parent_artifact_id INTEGER REFERENCES artifacts(id) ON DELETE SET NULL,
    prompt_version TEXT,
    provider TEXT,
    model TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE application_packets (
    packet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'drafting',
    artifact_id INTEGER REFERENCES artifacts(id) ON DELETE SET NULL,
    score_total REAL,
    scoring_version TEXT,
    content_hash TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE (job_id, version_number)
);

CREATE TABLE approvals (
    approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_type TEXT NOT NULL,
    subject_id INTEGER NOT NULL,
    artifact_id INTEGER NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
    artifact_version INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    invalidated_at TEXT,
    invalidation_reason TEXT
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id INTEGER NOT NULL,
    idempotency_key TEXT NOT NULL DEFAULT '',
    priority INTEGER NOT NULL DEFAULT 50,
    status TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    available_at TEXT,
    locked_by TEXT,
    locked_until TEXT,
    input_json TEXT,
    output_artifact_id INTEGER REFERENCES artifacts(id) ON DELETE SET NULL,
    error_code TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE (task_type, subject_type, subject_id, idempotency_key)
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id INTEGER NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_events_subject ON events(subject_type, subject_id);
CREATE INDEX idx_artifacts_subject ON artifacts(subject_type, subject_id);
CREATE INDEX idx_approvals_subject ON approvals(subject_type, subject_id, invalidated_at);
