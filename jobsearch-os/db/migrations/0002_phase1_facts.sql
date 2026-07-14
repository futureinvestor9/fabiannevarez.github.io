-- 0002_phase1_facts.sql — FACT-* confirmation + blocked questions (Invariant 7).
-- Phase 1 needs these for the sensitive-answer flow: unknown answers become
-- blocked questions; confirm-fact records a FACT-* the packet can then use.

CREATE TABLE candidate_facts (
    fact_id TEXT PRIMARY KEY,             -- FACT-### (namespace enforced in code)
    key TEXT NOT NULL,                    -- e.g. work_authorization, salary_minimum
    value TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'user_confirmed',
    question_id INTEGER,
    confirmed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE blocked_questions (
    question_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_type TEXT NOT NULL,
    subject_id INTEGER NOT NULL,
    field TEXT NOT NULL,                  -- the sensitive field needing an answer
    prompt TEXT NOT NULL,
    sensitive INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'open',  -- open | answered
    answered_fact_id TEXT REFERENCES candidate_facts(fact_id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX idx_blocked_questions_status ON blocked_questions(status);
CREATE INDEX idx_candidate_facts_key ON candidate_facts(key);
