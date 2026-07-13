# Job-Search Operating System

A local, single-user tool that diagnoses a job posting's likely business
problem before you touch the application, scores it 1–100 against an
honest skillset, and — for the roles worth pursuing — drafts a cover
letter, a contact research checklist, and a 4-touch outreach sequence into
an approval queue. **Nothing is ever sent automatically.** The system
drafts; you approve, edit, copy-paste, and send by hand, then tell it
"sent" or "responded" so it can schedule the next step and compute
metrics.

This implements the spec in [`docs/spec.md`](docs/spec.md) (Parts A + B of
the original Codex source file): Part A is the content layer (proof
points, banned phrases, messaging bank — see `content/*.yaml`); Part B is
the system layer this code implements.

## Setup

```bash
cd jobsearch-os
pip install -r requirements.txt
python -m jobsearch.cli init-db
```

This creates `data/jobsearch.db` (SQLite, gitignored — it's your personal
job-search data, not source code).

## The fast path: one command each morning

If you'd rather run the whole thing as a batch "agent" instead of one job at
a time: paste every posting you found into an intake file, then run one
command. See [`intake.example.md`](intake.example.md) for the paste format
(`## Company | Title | url`, then the JD text under it — as many blocks as
you want). A `.csv` with `company,title,jd_text,url` columns works too.

```bash
python -m jobsearch.cli run --file intake.example.md
```

That single command batch-ingests every posting (skipping duplicates seen
in the last 30 days), diagnoses + scores each one, drafts a cover letter
for anything worth applying to, and prints your **morning queue**: a
ranked, copy-paste-ready list of what to do today. You review each entry,
click Apply on LinkedIn yourself, paste the letter, and submit. Re-print
the queue any time with `python -m jobsearch.cli queue`.

This is as close to "apply on my behalf" as the system goes on purpose: the
agent does all the reading, scoring, and writing; **you** do the login, the
CAPTCHA, the click, and the send — every time. There is no code path that
submits an application or sends a message, and a test enforces it.

## The daily 60-minute loop

1. **Ingest today's postings.** For each job you found:
   ```bash
   python -m jobsearch.cli intake --company "Acme SaaS" \
     --title "Revenue Operations Analyst" --file jd.txt --location "Chicago"
   ```
   (`--file` reads a text file with the JD; omit it to pipe JD text via stdin.)

2. **Process them** — this diagnoses, scores, routes, and (for
   Strong/Tailored Apply) drafts a cover letter:
   ```bash
   python -m jobsearch.cli process
   ```

3. **Open the dashboard** and work the queues top to bottom (Due Today →
   Approval Queue → New Today → Apply Queue → Responses → Stale →
   Research Timers → Skipped Today → Top 5 Opportunities):
   ```bash
   python -m jobsearch.cli dashboard
   ```
   Then visit http://127.0.0.1:5000.

4. **For a job worth pursuing**, do the 5-minute manual contact lookup
   using the printed research checklist (LinkedIn search strings — this
   tool never scrapes LinkedIn), then add each contact:
   ```bash
   python -m jobsearch.cli add-contact --job-id 1 --name "Jamie Rivera" \
     --title "RevOps Manager" --classification decision_maker \
     --why "Hiring manager for the role"
   ```
   This generates all 4 touch drafts into the approval queue.

5. **Approve, copy, send.** In the dashboard, edit/approve each draft,
   then paste it into LinkedIn/Gmail yourself and click "Mark sent."

6. **End of week:**
   ```bash
   python -m jobsearch.cli weekly-metrics
   ```
   or visit `/weekly` in the dashboard.

## Other commands

```bash
python -m jobsearch.cli sweep              # due-today / stale / research-timer counts
python -m jobsearch.cli mark-applied --job-id 1 --method ATS
python -m jobsearch.cli log-response 3 "Said she'd forward it to the hiring manager."
python -m jobsearch.cli interview-prep --question-type ai_workflow
```

## Design notes

- **Diagnosis and scoring are deterministic and offline** (keyword/regex
  signal detection in `jobsearch/signals.py`), not an LLM call — see B11's
  "design so the LLM layer is a swappable module." This keeps the system
  runnable with zero API keys and fully testable. If you want richer,
  LLM-generated diagnoses later, swap `jobsearch/diagnosis.py`'s rule-based
  reads for an API call; the output shape (the `Diagnosis` dataclass) is
  the seam to plug into.
- **Scoring weight normalization:** the source spec's Section B4 lists 12
  dimension weights and claims they "sum to 10, so max = 100," but the
  listed weights actually sum to 11.0. `scoring.py` normalizes by the
  *actual* weight sum so the scale is always 0–100 regardless — see the
  comment in `config.yaml`.
- **Known metric approximations** (`jobsearch/metrics.py`): the schema has
  no `jobs.industry` field and no status-change history, so
  "best-performing industries" and week-scoped interview/rejection counts
  aren't fabricated — they're reported honestly as unavailable or as
  all-time snapshots. Add those columns if you want them tracked properly.
- **Non-goals, enforced:** no LinkedIn scraping, no auto-send, no browser
  automation. `tests/test_acceptance.py` includes a static source-scan
  test asserting no such code path exists.

## Tests

```bash
python -m pytest
```

Covers the 5 acceptance criteria from the spec: the worked B12 example
scoring Strong Apply end-to-end, RCM/healthcare auto-skip, Salesforce-Admin-cert
one-tier downgrade, banned-phrase validation, and the no-send/no-automation
source scan.
