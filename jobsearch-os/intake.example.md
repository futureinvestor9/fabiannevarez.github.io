# Batch intake — paste your postings here

Each posting is a block that starts with a header line:

    ## Company Name | Job Title | optional-url

Everything under it (until the next `## `) is the job description. Paste as
many as you like, then run:

    python -m jobsearch.cli run --file intake.example.md

The agent ingests all of them, diagnoses + scores each, drafts a cover
letter for anything worth applying to, and prints your morning queue. You
review, click Apply on LinkedIn yourself, paste, and submit.

---

## Acme SaaS | Revenue Operations Analyst | https://example.com/jobs/revops-1
We're looking for a RevOps Analyst to support our growing sales org. You'll
own CRM data hygiene in Salesforce, improve lead routing and follow-up
processes, build pipeline reports for leadership, and document our sales
processes as we scale. 1-3 years experience. Excel required; SQL a plus.
You'll work cross-functionally with Sales, Marketing, and CS.

## Northwind Health | Revenue Cycle Analyst | https://example.com/jobs/rcm-2
Seeking a Revenue Cycle Analyst for our hospital finance team. Analyze
claims processing, resolve denials, work with payer billing and patient
accounts, ensure HIPAA compliance and correct CPT/ICD-10 coding across the
hospital system.

## Brightwave | CRM Operations Analyst | https://example.com/jobs/crm-3
Own our CRM data quality and follow-up cadences in Follow Up Boss and
Salesforce. Build Smart Lists, clean up records, track response rates by
channel, and keep the pipeline honest for a fast-growing services team.
Excel and Google Sheets daily. 1-3 years experience.
