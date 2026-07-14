# Safety Invariants — single source of truth

These override everything else in this repository. Every phase, module, and
test must respect them. (Section B of the v6 master spec, verbatim.)

1. **No autonomous external actions.** An *external action* is a
   user-representing write to an employer, contact, job board, email system,
   calendar, or similar external destination (sending a message, submitting an
   application, posting, connecting). The MVP contains no code path that
   performs an external action. `mark-submitted` / `mark-sent` record that the
   user did it manually. Bounded model calls, vendor CLI invocations, and
   permitted fetches of public pages are NOT external actions.
2. **No LinkedIn scraping, auto-connecting, or auto-messaging.** Draft and
   track only. No automated LinkedIn discovery of contacts.
3. **No bypassing** CAPTCHAs, login walls, anti-bot systems, rate limits, or
   job-board restrictions — ever, in any phase.
4. **No credential access.** Never read, copy, print, locate, parse, or
   persist cookies, session files, OAuth tokens, passwords, 2FA data,
   `~/.claude`, `%USERPROFILE%\.claude`, or browser storage. Project code MAY
   invoke an authenticated vendor CLI (e.g., `claude`) through its supported
   interface; it may never inspect or expose that CLI's credential storage.
   The user authenticates tools himself.
5. **Approval gate is absolute.** No object reaches a submitted/sent state
   without a recorded, version-locked approval transaction. Editing an
   artifact after approval invalidates the approval.
6. **No invented claims.** Every externally visible claim maps to evidence
   (Section C) or is blocked.
7. **Never infer sensitive answers.** Work authorization, sponsorship,
   compensation expectations, relocation, demographic, disability,
   veteran-status, and criminal-history answers must never be inferred or
   model-generated. Use a confirmed `FACT-*` candidate fact or create a
   blocked review item.
8. **Deterministic-first.** Use Python and cached data before any model call.
   Every model call is a bounded model call.
9. **Idempotent tasks.** Every task is idempotent or carries an idempotency
   key with an enforced uniqueness constraint.
10. **No open-ended agent conversations.** Agent collaboration (optional,
    Phase 7+) uses bounded task packets with max review rounds. Two coding
    agents never edit the same checkout concurrently.
11. **Windows-friendly.** All paths, scripts, and setup must work on a clean
    Windows machine.
12. **When uncertain, block.** Create a blocked decision record instead of
    taking an irreversible action.
13. **Protect pre-existing user work.** Never reset, discard, stash, stage,
    overwrite, or commit pre-existing user changes without explicit approval.
14. **Technical enforcement, not just instructions:** `.gitignore` for secrets
    and local DBs; secret-pattern scanner in tests; redaction utility; command
    allowlists in agent wrappers; timeouts; path restrictions; never
    interpolate model output into shell commands; no `danger-full-access`.

Any future post-approval executor is a separate optional module behind its own
feature flag, with per-item approval, its own tests, and never via a
site-restriction bypass.
