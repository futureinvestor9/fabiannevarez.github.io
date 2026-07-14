# Quickstart — jobsearch-os (v6 system, package `jobsearch_os`)

The v6 system is the rigorous, approval-gated build described in
`docs/MASTER_SPEC.md`. It is **Phase 1 complete**: usable end-to-end,
deterministic, zero API keys. (The earlier `jobsearch/` package is a separate
pre-v6 prototype — see `docs/ADR/ADR-0002`.)

## Install
```bash
cd jobsearch-os
pip install -e ".[dev]"          # or: pip install pyyaml pytest
python -m jobsearch_os.cli doctor
```
Windows: `powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1`

## The Phase-1 loop
```bash
# 1. create the DB + seed non-sensitive candidate facts
python -m jobsearch_os.cli init-db

# 2. ingest postings (CSV with columns company,title,description,url,location,posted_date)
python -m jobsearch_os.cli ingest --csv data/job_targets.csv
#    ...or one at a time:
python -m jobsearch_os.cli add-job --company "Acme" --title "Revenue Operations Analyst" \
    --url "https://boards.greenhouse.io/acme/jobs/123" --description-file jd.txt

# 3. score + build packets (deterministic)
python -m jobsearch_os.cli score

# 4. see what's waiting for review (packets + blocked sensitive questions)
python -m jobsearch_os.cli review-export

# 5. review a packet, then approve it (version + content-hash locked)
python -m jobsearch_os.cli submit-for-review --packet-id 1
python -m jobsearch_os.cli approve --type packet --id 1

# 6. apply MANUALLY on the job site, then record it (blocked until approved)
python -m jobsearch_os.cli mark-submitted --packet-id 1
```

## Sensitive answers (Invariant 7)
Unknown work-authorization / salary / sponsorship / relocation become **blocked
questions**, never guesses. Answer one to record a FACT:
```bash
python -m jobsearch_os.cli confirm-fact --question-id 1 --answer "Authorized to work in the US, no sponsorship"
```

## Acceptance
```bash
python -m jobsearch_os.cli accept-phase1     # isolated temp workspace + temp DB
python -m pytest tests/v6 -q                  # Phase-1-blocking test suite
```

## What Phase 1 does NOT do (by design)
No sending, submitting, connecting, or scraping. No LinkedIn automation. No
model/provider calls. `mark-submitted` records that *you* applied by hand.
Outreach, follow-ups, model providers, research, the dashboard, and the worker
loop are Phases 2–9 (deferred; see `docs/BUILD_PLAN.md`).
