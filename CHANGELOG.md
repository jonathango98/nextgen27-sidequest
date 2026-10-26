# Changelog

Every change to this repo, newest first. Every PR adds one entry at the top, whether a human or an AI agent made it (ENG-100 to ENG-104, AI-070).

This file records what changed in the repo. It is not a runtime log, so SAFE-030 does not forbid it. Never put secrets, real attendee data, or hidden item locations here.

Entry format:

```markdown
## YYYY-MM-DD · <branch> · <Model name> / @<github-handle>

- What: one or two lines on what changed.
- Why: the issue or reason.
- Rule IDs: the rules this implements or touches.
- Status: Started, In progress, or Done (matches the README Project status).
- PR: #N, or "draft" until the PR exists.
```

Humans working without an AI agent sign as `Human / @<github-handle>`.

---

## 2026-10-26 · chore/improve-pick-task · Claude Opus 5.5 / @jonathango98

- What: Rewrote the `pick-task` skill around the feature tree. A new helper, `.claude/skills/pick-task/unlocked.py`, lists pieces as ready, in progress, waiting on other pieces, or waiting on a decision. The skill asks for the volunteer's Claude plan and prefers one-session pieces on Pro, shows what each piece unlocks, checks again for a claim right before pushing, fills in the full PR template, labels safety-review pieces, and assigns issues. Removed the out-of-date "no app yet" advice.
- Why: The old skill couldn't see what was half done, offered big features whole, and could let two people claim the same task. Needs #36 merged first.
- Rule IDs: ENG-101, ENG-105 to ENG-109, AI-003, AI-033, AI-043, AI-072
- Status: Done
- PR: #37

## 2026-10-26 · docs/feature-tree · Claude Opus 5.5 / @jonathango98

- What: Added `foundation/feature-tree.yaml`, which splits every Planned feature into 74 pieces of size S (one agent session) or M (about two), each with the pieces it needs first, its area, level, safety review, and rule IDs. 20 pieces stay locked until their OPEN rules are decided. `foundation/16-feature-tree.md` holds the rules (ENG-105 to ENG-109), the Core build backbone, and a features table. ENG-101 now claims one piece at a time. The README Planned table has a Tree column and three new rows: Staff accounts and roles, Mix look on player screens, and Game day readiness. Added a map of the tree: `scripts/feature_tree_map.py` writes `docs/feature-tree.md`, a test fails when it is out of date, and the new `Feature tree map` workflow publishes an interactive version to GitHub Pages on every merge to `main` (DEC-039, approved exception to AI-022).
- Why: Volunteers can't tell which tasks are ready or small enough to start. `/pick-task` will use the tree next to offer only unlocked pieces.
- Rule IDs: ENG-105, ENG-106, ENG-107, ENG-108, ENG-109, ENG-110, ENG-101, ENG-087, ENG-088, AI-003, DEC-038, DEC-039
- Status: Done
- PR: #36

## 2026-10-26 · feat/screen-skeleton · Claude Opus 5.5 / @jonathango98

- What: Every player screen in the `06-api-and-screens.md` screen list is now a plain page: Home, Scan, Icebreaker, Quests, Journal, new takeaway, Summary, Open Box, and Wrapped. The bottom bar is Home, My Code, Quests, and the current tab is marked. Scan opens from My Code and from Meet friends on Home. Players land on Home after joining or logging in. Pages show placeholders, and forms stay switched off until their features are built. No new routes, no final look, no game logic. PR preview environments (named `...-pr-<number>` by Railway) now start with Example Church A, B, and C when the church list is empty. Staging and production never get them.
- Why: Gives the January screen features pages to build on, following the Mix mockups' screens and links. PR previews start with an empty database, so nobody could pick a church and join to test them.
- Rule IDs: ARCH-017, SAFE-031, UI-030, UI-031, UI-035, UI-036, UI-037, UI-038, API-001, API-005, GAME-015, GAME-017, GAME-031, GAME-036, GAME-073, WRAP-002, AI-043, ENG-045
- Status: Done
- PR: #35

## 2026-10-25 · fix/webkit-https-tests · Claude Opus 5.5 / @jonathango98

- What: The browser test server serves HTTPS with a throwaway self-signed certificate, so the Join and Login browser tests pass in WebKit (Safari's engine) as well as Chromium.
- Why: WebKit drops `Secure` cookies on plain `http://`, so the `__Host-` CSRF and session cookies were never stored. The first POST got a 400 and Join stopped at step 1. Real phones use HTTPS, so players were not affected, but Safari was never really tested on these flows.
- Rule IDs: ENG-045, ARCH-038, AI-044, SAFE-030
- Status: Done
- PR: #34

## 2026-10-25 · feat/mix-tokens · Claude Opus 5.5 / @jonathango98

- What: Docs only. Writes the Mix vibe (UI-009) and the screen layouts from the Mix mockups into `07-design-system.md` 1.3.0: Home (UI-036), My Code with a Scan button (UI-037), and the shared takeaways page (UI-038). The scan, icebreaker, then points order is a note only, since GAME-016 is OPEN. Logged as DEC-037 (`13-decisions.md` 1.15.0). The earlier app changes on this branch were taken out. The app's look changes in a later PR.
- Why: Jonathan wants the design decisions written down before the app is restyled.
- Rule IDs: UI-009, UI-036, UI-037, UI-038, GAME-016, DEC-037, ENG-087
- Status: Done
- PR: #32

## 2026-10-25 · docs/ui-008-grain · Claude Opus 5.5 / @jonathango98

- What: UI-008 drops "no images", so the Mix film grain is allowed as a tiny texture generated in the CSS (`07-design-system.md` 1.2.0). Logged as DEC-036 (`13-decisions.md` 1.14.0).
- Why: UI-008 asked for film grain and for no images, which can't both hold. Jonathan kept the grain.
- Rule IDs: UI-008, UI-004, DEC-036, ENG-087
- Status: Done
- PR: #33

## 2026-10-24 · docs/mix-style · Claude Opus 5.5 / @jonathango98

- What: Writes the Mix look into `07-design-system.md` (1.1.0): new color, type, and radius tokens with checked contrast, the look itself (UI-008), frosted cards, a bottom bar of Home, My Code, Quests with Scan moved onto My Code and Home (UI-030), one black main button per screen (UI-035), and one-or-two-word labels (UI-057). Logged as DEC-035 (`13-decisions.md` 1.13.0). Docs only: `tokens.css` and the bottom bar in the app still use the old look.
- Why: Jonathan chose the Mix design for the player app.
- Rule IDs: UI-008, UI-030, UI-033, UI-034, UI-035, UI-057, DEC-035, ENG-087
- Status: Done
- PR: #31

## 2026-10-24 · docs/plan-screen-skeleton · Claude Opus 5.5 / @jonathango98

- What: Adds "Screen skeleton" to Planned in the README Project status: every player screen as a plain page, with all buttons and tabs linked, before each feature fills its screen in.
- Why: Lets the team click through the whole player flow early, and gives each later feature a page to build on.
- Rule IDs: UI-030, ENG-100, AI-070
- Status: Done
- PR: #30

## 2026-10-24 · fix/age-question-18-plus · Claude Opus 5.5 / @jonathango98

- What: The Join page asks "Are you 18 or older?" instead of "Are you under 18?". The form field is now `age_18_plus`, and a "no" is saved as `is_under_18`, so the table and existing players don't change. A form sent with the old `under_18` field is refused rather than guessed. SAFE-002 reworded as DEC-034 (`03-safety-privacy.md` 1.1.0, `06-api-and-screens.md` 1.2.1, `13-decisions.md` 1.12.0).
- Why: "Are you under 18?" was confusing, because a "yes" marks someone as a minor.
- Rule IDs: SAFE-002, SAFE-020, DEC-034, ENG-023, ENG-087, AI-042, AI-044, ENG-101
- Status: Done
- PR: #29

## 2026-10-23 · feat/25-join-login · Claude Opus 5.5 / @jonathango98

- What: Join, PIN set, and log in (replaces #26 and #27). So far: decided ARCH-033 as DEC-033 (one full name per church, 409 `NAME_TAKEN`, DATA-016; `04-architecture.md` 1.6.0, `05-data-model.md` 1.2.0, `06-api-and-screens.md` 1.2.0, `13-decisions.md` 1.11.0, after #23's DEC-031). Added `app/db.py` (foreign keys, WAL, busy timeout) and a migration runner that applies numbered `migrations/*.sql` at app start. `0001` creates the `church` and `player` tables. The app needs `SQ_DB_PATH`, which is set in Railway staging and production with a `/data` volume. Church list loader: `python -m app.services.churches <file.csv | ->` adds churches from a one-column `name` CSV kept outside the repo, refuses near duplicates, and writes nothing on any error. Join and PIN set: `GET`/`POST /join` in two steps (details, then PIN twice), working with or without JavaScript. PINs are hashed with scrypt (`app/auth/pin.py`). A signed `__Host-sq_session` cookie (`SQ_SESSION_KEY`, 400 days) logs the player in, and `get_current_player` now reads it, so `/code` works after joining. Every POST checks a CSRF token. Forms are read with the standard library, with no new dependency. No join points until the points service exists. Log in: `GET`/`POST /login` with full name, church, and PIN. Each try is taken before the PIN is checked, so guesses sent at once can't get past the lockout, which comes after `auth.pin_max_attempts` wrong PINs in a row (403 `PIN_LOCKED`). An unknown name and a wrong PIN get the same message and the same hashing work. Now that players can log in, My Code (#23) works end to end, so its row moves to Working too.
- Why: Next Core build piece. My Code (#23) waits on it. Issue #25.
- Rule IDs: SAFE-002, SAFE-004, SAFE-022, SAFE-023, API-021, SAFE-020, SAFE-021, SAFE-030, ARCH-020, ARCH-030, ARCH-034, ARCH-038, API-002, API-004, API-005, API-007, UI-003, UI-032, AI-041, ARCH-007, DEC-011, ARCH-032, ARCH-033, DATA-002, DATA-003, DATA-004, DATA-005, DATA-011, DATA-016, DATA-040, ENG-050, ARCH-001, ARCH-010, ARCH-013, API-021, DEC-033, ENG-087, ENG-088, ENG-101
- Status: Done
- PR: #28

## 2026-10-23 · feat/my-code · Claude Opus 5.5 / @jonathango98

- What: My Code page (`GET /code`) and its QR partial (`GET /code/qr`). `app/services/qr.py` makes `SQ1` payloads with a 6-digit time-based code from a per-player secret derived from `SQ_QR_SIGNING_KEY`, plus `verify()` for the scanner. The QR replaces itself when the 30 s window ends, and retries a failed refresh after `qr.poll_retry_seconds`. Responses are `no-store`. HTMX 2.0.11 is vendored and set to show 4xx error partials. Adds `segno==1.6.6`. Until Join exists, `get_current_player` always returns 401 `LOGIN_REQUIRED`. Protected changes: `qr.poll_retry_seconds: 3` in `game-config.yaml` (1.1.0) and DEC-031 in `13-decisions.md` (1.10.0, after #24's DEC-032).
- Why: Next Core build piece with no OPEN blockers. The Scanner builds on it.
- Rule IDs: GAME-001, ARCH-004, ARCH-020, ARCH-021, ARCH-022, ARCH-023, ARCH-074, API-002, API-003, API-005, API-006, API-030, UI-002, UI-030, DEC-031, ENG-087, AI-044, ENG-101
- Status: In progress
- PR: #23

## 2026-10-23 · docs/drop-screenshot-and-size-rules · Claude Opus 5.5 / @jonathango98

- What: Removed the PR size target (under 400 changed lines) and the 360px PR screenshot from AI-034 (`AGENTS.md` 1.4.0, `10-ai-agent-rules.md` 1.4.0), ENG-020 (`09-engineering-workflow.md` 1.7.0), `CONTRIBUTING.md` 1.4.0, and the PR template. Logged DEC-032 (`13-decisions.md` 1.9.0). The browser check (AI-044) and fake-data screenshots (SAFE-036) stay.
- Why: Jonathan's call. The browser check already covers 360px layout.
- Rule IDs: AI-034, ENG-020, DEC-032, ENG-085, ENG-087
- Status: Done
- PR: #24

## 2026-10-23 · docs/railway-status · Claude Opus 5.5 / @jonathango98

- What: Moved the Railway setup from In progress to Working. After #21 merged, staging was switched to deploy `main`, and commit `2830f7d` deployed with `/health` returning `ok` over HTTPS.
- Why: #21 merged with its row still under In progress (ENG-103). This PR also checks that PR preview environments work.
- Rule IDs: ENG-102, ENG-103, ARCH-017, DEC-030
- Status: Done
- PR: #22

## 2026-10-23 · chore/railway-config · Claude Opus 5.5 / @jonathango98

- What: Railway setup. Adds `.python-version` (3.14), ARCH-017 in `04-architecture.md`, and DEC-030 in `13-decisions.md`: staging auto-deploys `main`, production is deployed by hand, and each PR gets a preview environment. Service settings (start command, `/health` check, US West, 1 replica) are set in Railway and recorded in DEC-030, because `railway.json` stops working on 2026-12-01. Created the Railway project `nextgen27-sidequest` with `production` and `staging` environments, a `web` service in staging (Python 3.14.9, `pip install -r requirements.txt`, `/health` returns `ok` over HTTPS), and PR environments based on staging (bot PRs off). Staging tracks this branch until it merges, then `main`. Production has no service yet.
- Why: Jonathan wants to check every PR and `main` on Railway before production (ARCH-011).
- Rule IDs: ARCH-010, ARCH-011, ARCH-014, ARCH-017, DEC-028, DEC-029, DEC-030, ENG-087, ENG-101
- Status: In progress
- PR: #21

## 2026-10-23 · feat/app-skeleton · Claude Opus 5.5 / @jonathango98

- What: Claimed the app skeleton, design tokens in `tokens.css`, and the shared player page frame. Part 1 added: `pyproject.toml` with pinned FastAPI, Uvicorn, and PyYAML, pip-tools lock files, `app/config.py` (loads `game-config.yaml` with `safe_load`, checks `config_version`), and `app/main.py` (app factory, `GET /health`, FastAPI's built-in docs routes off). httpx2 is a new dev-only library: FastAPI's test client needs an HTTP client, and Starlette 1.9 deprecates httpx in favor of httpx2. Part 2 added: `tokens.css` with every token from `07` section 2, `player.css`, and `templates/player/base.html` with the score bar and the My Code, Scan, and Quests buttons. `/static` is served by the app. Jinja2 and pytest-playwright are pinned. Browser tests run at the config viewport width in Chromium and WebKit, using a test-only route.
- Why: There is no `app/` folder yet, and every Core build feature needs it. DEC-027 unblocked the stack. DEC-029 approved `/health`.
- Rule IDs: ARCH-001, ARCH-003, ARCH-004, ARCH-008, ARCH-010, ENG-030, ENG-031, ENG-057, API-001, DEC-027, DEC-029, UI-001, UI-002, UI-003, UI-030, UI-054, UI-055, AI-044, ENG-101
- Status: Done
- PR: #18

## 2026-10-23 · docs/health-route · Claude Opus 5.5 / @jonathango98

- What: Adds `GET /health` to `06-api-and-screens.md` in a new System section, and logs the decision in `13-decisions.md`.
- Why: Issue #19, approved by Jonathan. The app skeleton (#18) needs one route to prove the app starts, and Railway can use it as a health check.
- Rule IDs: API-001, ARCH-010, ENG-087, ENG-088
- Status: Done
- PR: #20

## 2026-10-23 · docs/simplify-working-status · Claude Opus 5.5 / @jonathango98

- What: Simplified the README Working table to two columns (What, Done) in plain words, and merged the 11 setup rows into one "Project setup" row. Planned and In progress are unchanged. The details of the merged rows stay in the entries below.
- Why: The Project status is for non-technical stakeholders to see where the project is. Technical readers use this file.
- Rule IDs: ENG-100, ENG-103, AI-070
- Status: Done
- PR: #17

## 2026-10-23 · docs/guardrails-tests-status · Claude Opus 5.5 / @jonathango98

- What: Ticked protection tests 3 and 4 in `15-repo-setup-checklist.md` section 4 and moved Repo guardrails to Working. Tests 1, 2, and 5 need a second account or a workflow, so they moved to issue #15.
- Why: PR #10 merged and the ruleset and secret scanning are live. In progress means an open branch (DEC-022), and #10's branch is gone.
- Rule IDs: ENG-080, ENG-081, ENG-087, ENG-102, ENG-103
- Status: Done
- PR: #16

## 2026-10-23 · docs/railway-hosting · Claude Opus 5.5 / @jonathango98

- What: Recorded Railway in US West as the only host in DEC-028. It replaces the two VMs and Caddy: Railway terminates HTTPS, the app serves its own static files, and SQLite sits on a Railway volume as a single replica. Added ARCH-016 (no production deploys during live game hours). Updated the stack table, diagram, ARCH-073, ENG-055, and the pre-event checklist. Removed the Caddy entries from `.gitignore`. ARCH-053 stays OPEN, now asking for an off-Railway copy.
- Why: Issue #13. Jonathan chose Railway as the only host.
- Rule IDs: ARCH-001, ARCH-002, ARCH-010, ARCH-011, ARCH-014, ARCH-016, ARCH-053, ARCH-073, ENG-055, ENG-087, ENG-088, DEC-028
- Status: Done
- PR: #14

## 2026-10-23 · docs/kickoff-stack-decisions · Claude Opus 5.5 / @jonathango98

- What: Recorded the kickoff stack as PROPOSED in DEC-027: Python 3.14 locked with pip-tools from `pyproject.toml`, PyYAML (`safe_load` only), segno for QR images, `barcode-detector` for the scanner (Safari and Chromium, served from our own server), and numbered plain SQL migrations. Removed those rows from the OPEN table. The Wrapped image stays OPEN (WRAP-033).
- Why: Every Core build feature needs the app skeleton, and the skeleton was blocked on these OPEN items.
- Rule IDs: ARCH-003, ARCH-004, DATA-040, ENG-050, ENG-057, ENG-087, ENG-088, DEC-027
- Status: Done
- PR: #12

## 2026-10-23 · chore/repo-docs-cleanup · Claude Opus 5.5 / @jonathango98

- What: Moved `CONTRIBUTING.md` and `SECURITY.md` into `.github/`, and `CLAUDE.md` into `.claude/` (imports now `@../`), and updated every reference. `AGENTS.md` stays at the root so Codex and other agents still find it. `SECURITY.md` now links to SAFE-030 to SAFE-037 instead of repeating them. Fixed the `AGENTS.md` line that listed `README.md` as protected. Removed the three now-covered CODEOWNERS lines. Ignored `.serena/`. Recorded DEC-026.
- Why: Fewer root files, one copy of each rule, and `AGENTS.md` matching ENG-080 and AI-070.
- Rule IDs: ENG-080, ENG-087, ENG-101, AI-070, SAFE-030 to SAFE-037, DEC-026
- Status: Done
- PR: #11

## 2026-10-23 · docs/status-guardrails-done · Claude Opus 5.5 / @jonathango98

- What: Finished the repo guardrails that PR #8 started. Added `.github/CODEOWNERS` for the protected paths, with a commented safety reviewer placeholder. Jonathan applied checklist steps 2 to 6 (squash-only merges, auto-delete branches, fork PR approval, Dependabot, private vulnerability reporting, labels, and the `main-protection` ruleset with an admin bypass for pull requests only). Marked layers 2 and 3 in `15-repo-setup-checklist.md`. Sorted the Working table newest first, with new Working and In progress rows added at the top.
- Why: Issue #7. PR #8 only dropped the local guard layers, and closed #7 by accident. Without CODEOWNERS and the ruleset, `main` had no review gate.
- Rule IDs: ENG-080, ENG-081, ENG-021, ENG-087, SAFE-016, DEC-024, ENG-100, ENG-102, ENG-103
- Status: In progress (protection tests in `15-repo-setup-checklist.md` section 4 not run yet)
- PR: #10

## 2026-10-23 · chore/pick-task-skill · Claude Opus 5.5 / @jonathango98

- What: Added the `/pick-task` Claude Code skill. It reads the Project status, open branches, PRs, and issues, asks two quick questions, offers 3 unclaimed options in plain words, and calls dibs on the pick. `CONTRIBUTING.md` points to it.
- Why: Volunteers asked for a "give me options" way to find work.
- Rule IDs: ENG-101, ENG-102, ENG-103, AI-003, AI-045, AI-071, AI-072
- Status: Done
- PR: #9

## 2026-10-23 · chore/7-repo-guardrails · Claude Opus 5.5 / @jonathango98

- What: Claimed the repo guardrails task. Dropped the local guard layers (Claude Code deny rules, hook, Codex rules, `foundation-guard` workflow), so protection is agent instructions, CODEOWNERS, and the ruleset on `main` (DEC-024). Cut process rules Jonathan picked in review: area folders, issue before every branch, commit message format, the Foundation Change Request issue (a protected file now changes in a PR he approves), stale approval dismissal, approval issues for new libraries, and the long PR template (DEC-025).
- Why: Issue #7. Volunteers should explore AI coding without fear or paperwork. Review before `main` still catches problems.
- Rule IDs: AI-002, AI-010, AI-011, AI-012, AI-021, AI-031, AI-032, AI-034, AI-051, AI-060, ARCH-002, ARCH-004, ENG-002, ENG-004, ENG-010, ENG-020, ENG-021, ENG-048, ENG-057, ENG-080, ENG-081, ENG-085 to ENG-087, ENG-090, ENG-091, PRD-051, DEC-024, DEC-025
- Status: In progress
- PR: #8

## 2026-10-22 · chore/browser-check-skill · Claude Opus 5.5 / @jonathango98

- What: Added the `browser-check` skill (Playwright for Python, adapted from anthropics/skills webapp-testing). Checks now run before every commit instead of before push, and page changes also get the browser check. Playwright joins the stack as PROPOSED (DEC-023).
- Why: Contributors should have Claude check their changes in a real browser at 360px before committing.
- Rule IDs: AI-033, AI-044, ENG-012, ENG-045, ENG-049, ARCH-002, DEC-023
- Status: Done
- PR: #5

## 2026-10-20 · docs/agent-changelog-status · Claude Opus 5.5 / @jonathango98

- What: Added this change log and a Project status section in `README.md`. Removed `README.md` from the protected paths. Added ENG-100 to ENG-104 and AI-070 to AI-073, recorded DEC-022, and pointed `CONTRIBUTING.md` to the new rules.
- Why: One page should show what works, what is being built, and what is next, so two people don't build the same thing.
- Rule IDs: ENG-080, ENG-100 to ENG-104, AI-012, AI-070 to AI-073, DEC-022
- Status: Done
- PR: #4

## 2026-10-19 · chore/add-task-observer-skill · No AI record / @jonathango98

- What: Added the shared task-observer skill for Claude Code in `.claude/skills/task-observer/`. Backfilled from git history.
- Why: Shared skill for spotting reusable workflows.
- Rule IDs: AI-022
- Status: Done
- PR: #3

## 2026-10-19 · chore/1-add-gitignore · No AI record / @jonathango98

- What: Added `.gitignore` for secrets, databases, Python, Caddy, and editor files. Backfilled from git history.
- Why: Keep forbidden files out of the public repo.
- Rule IDs: ENG-056, ARCH-007, ENG-061
- Status: Done
- PR: #2

## 2026-10-19 · main · No AI record / @jonathango98

- What: Added the Side Quest foundation v1 (`foundation/`, root docs, PR template). Backfilled from git history.
- Why: Repo setup.
- Rule IDs: all foundation rules
- Status: Done
- PR: none (initial commit)
