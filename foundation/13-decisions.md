# 13 Decisions

- Status: Active
- Owner: Jonathan (@jonathango98)
- Version: 1.16.0
- Last updated: 2026-10-26

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

This file has three parts: the decision log (what was decided and why), the resolved conflicts between source documents, and the table of every OPEN item. Every rule marked OPEN anywhere in the foundation appears in section 3.

Sources, in order of precedence:
1. Jonathan's answers in the foundation setup session (2026-10-19)
2. Resolved conflicts (section 2)
3. Blueprint (last updated 2026-10-19)
4. Leadership deck speaker notes
5. Project brief

## 1. Decision log

| ID | Date | Decision | Why | Source |
|---|---|---|---|---|
| DEC-001 | 2026-10-19 | One repo for server and front end (ARCH-005, ARCH-006) | Pages are server-rendered, so templates and routes change together. Revisit only if the front end becomes a separate JavaScript app with a JSON API | Jonathan (conflict C7) |
| DEC-002 | 2026-10-19 | No coins. Score is the only currency. One sticker unlocks every 300 points of score, up to 3. Nothing is spent or reset; stickers earned is computed from score (GAME-003, GAME-070 to GAME-074) | One currency is simpler to explain and to build | Jonathan |
| DEC-003 | 2026-10-19 | No "boxes left" counter on the main screen or in the app (GAME-077) | Simpler. Stock is still enforced by the server (GAME-076) | Jonathan |
| DEC-004 | 2026-10-19 | Only an admin resets a locked PIN (SAFE-023) | Overrides the Blueprint's "until an usher resets it". Keeps account recovery with fewer people | Jonathan |
| DEC-005 | 2026-10-19 | The foundation is the first commit on `main`, made directly with no PR (ENG-001) | The repo was empty, so there was no `main` to open a PR against | Jonathan |
| DEC-006 | 2026-10-19 | License: MIT | Other churches and future events may reuse the app | Jonathan (resolves the Blueprint's license question) |
| DEC-007 | 2026-10-19 | The summary page is for signed-in players only (SAFE-017) | It holds takeaways from minors. The Blueprint's "anyone can read" is read as "any player" | Jonathan |
| DEC-008 | 2026-10-19 | The main screen shows a takeaway wall of approved shared posts (SAFE-018) | Adds to the Blueprint's leaderboards | Jonathan |
| DEC-009 | 2026-10-19 | Each hidden item can be claimed once in total (GAME-043) | Items are physical and kept at the booth after turn-in | Jonathan |
| DEC-010 | 2026-10-19 | Join points are given once, on any day. The quest is renamed "Join the game" (GAME-040) | Late arrivals are not left out | Jonathan |
| DEC-011 | 2026-10-19 | Church is picked from a preloaded church list (SAFE-002) | Clean church scores, no typos, and a place to hold region data | Jonathan |
| DEC-012 | 2026-10-19 | Log in with full name, church, and PIN (ARCH-032) | No email or phone exists to log in with | Jonathan |
| DEC-013 | 2026-10-19 | The session check-in code is shown on a screen in the hall and rotates every 30 seconds (GAME-020) | A photo of a printed code could be shared outside the hall | Jonathan |
| DEC-014 | 2026-10-19 | Takeaways cannot be submitted while paused (GAME-033) | Consistent with "no earning during sessions" | Jonathan |
| DEC-015 | 2026-10-19 | Under-18 players appear on leaderboards like everyone else, first name and church only (SAFE-019) | Equal treatment. Only first name and church are shown anyway | Jonathan |
| DEC-016 | 2026-10-19 | Admin revocation is the only way score goes down. Claimed stickers stay with the player (GAME-004, GAME-074) | Physical stickers cannot be taken back | Jonathan |
| DEC-017 | 2026-10-19 | Protected paths also include `.gitignore`, `.editorconfig`, `.env.example`, `.claude/**`, and `.codex/**` (ENG-080) | Weakening `.gitignore` or agent settings would bypass other protections | Jonathan |
| DEC-018 | 2026-10-19 | Add an experimental Codex rules layer, a Dependabot config for GitHub Actions, and pin Actions by commit SHA. All three are built in the guardrails phase | Extra protection and safer dependency updates | Jonathan |
| DEC-019 | 2026-10-19 | This phase writes rules and Markdown only (plus `game-config.yaml` and `LICENSE`). Guardrail code, CI, hooks, and GitHub config files come later | Jonathan's instruction | Jonathan |
| DEC-020 | 2026-10-19 | `CLAUDE.md` imports `AGENTS.md` and `foundation/README.md`. The schema and routes live in `05-data-model.md` and `06-api-and-screens.md`, not in `CLAUDE.md` | One source of truth. The brief said `CLAUDE.md` would hold the schema, routes, and rules | Jonathan |
| DEC-021 | 2026-10-19 | Phone numbers and email addresses are not collected (SAFE-003) | Conflict C3 | Jonathan |
| DEC-022 | 2026-10-20 | Root `README.md` gets a Project status section (Working, In progress, Planned) that every PR updates, and `CHANGELOG.md` gets one signed, dated entry per PR. `README.md` comes off the protected list. In progress means "has an open branch" (ENG-080, ENG-100 to ENG-104, AI-070 to AI-073) | One page shows where the project is, and claiming work early stops two people building the same thing | Jonathan |
| DEC-023 | 2026-10-22 | Playwright for Python (pytest-playwright) joins the stack as PROPOSED, for dev and test only. Checks run before every commit, not only before push, and page changes also get the `browser-check` skill at 360px (ARCH-002, ENG-012, ENG-049, AI-033, AI-044). Versions are pinned in `pyproject.toml` at kickoff (ENG-057). Enforced by the rules only, with no git hook | Contributors have Claude check their changes in a real browser before committing. A hook was left out to keep commits fast and setup simple | Jonathan |
| DEC-024 | 2026-10-23 | Drop the local guard layers: Claude Code deny rules, the Claude Code hook, the Codex rules (replaces that part of DEC-018), and the `foundation-guard` workflow. Protection is agent instructions, CODEOWNERS, and the ruleset on `main`. ENG-090 and ENG-091 are removed (ENG-081, AI-060) | Volunteers should explore AI coding without fear. A branch cannot hurt `main`, and code owner review was already the real gate. The local layers blocked Jonathan too and could be bypassed anyway | Jonathan |
| DEC-025 | 2026-10-23 | Fewer process rules. Removed: stay in your area folders (AI-011), an issue before every branch (ENG-002, ENG-004), the commit message format and rule IDs in commits (ENG-010, AI-032, AI-002), the Foundation Change Request issue (ENG-086, AI-051; a protected file now changes in a PR that Jonathan approves), dismissing stale approvals and requiring resolved conversations (ENG-021), approval issues for new libraries (ARCH-002, ENG-057, AI-021; services and infrastructure still need one), and the long PR template (ENG-020, AI-034). Kept: checks before every commit (DEC-023) and stop and ask (AI-050) | Volunteers should explore AI coding without fear or paperwork. Review before `main` still catches problems | Jonathan |
| DEC-026 | 2026-10-23 | Move `CONTRIBUTING.md` and `SECURITY.md` from the root into `.github/`, and `CLAUDE.md` into `.claude/`. They stay protected under `.github/**` and `.claude/**`. `AGENTS.md` stays at the root because Codex and other agents only look for it there. `SECURITY.md` links to SAFE-030 to SAFE-037 instead of repeating them (ENG-080) | Fewer root files and one copy of each rule. GitHub still finds both files in `.github/` | Jonathan |
| DEC-027 | 2026-10-23 | Kickoff stack, all PROPOSED: Python 3.14, locked with pip-tools from `pyproject.toml` (ARCH-003). PyYAML with `safe_load` only, segno for QR images, and `barcode-detector` for the in-app scanner, served from our own server (ARCH-004). Migrations are numbered plain SQL files with a small built-in runner (DATA-040, ENG-050). The Wrapped image stays OPEN (WRAP-033) | Unblocks the app skeleton and every Core build feature. Python 3.14 has a year of library support, while 3.15 came out on 2026-10-09. pip-tools keeps plain `requirements.txt` files, which volunteers and the host already understand. `barcode-detector` works in Safari and Chromium, matching the browser tests (DEC-023). Plain SQL needs no extra library | Jonathan |
| DEC-028 | 2026-10-23 | Host on Railway only, in US West, with one production and one staging environment (ARCH-014). Railway replaces the two VMs and Caddy: it terminates HTTPS, the app serves its own static files, and SQLite sits on a Railway volume as a single replica (ARCH-001, ARCH-010, ARCH-011, ENG-055). No production deploys during live game hours (ARCH-016). ARCH-053 stays OPEN | Less to run than VMs plus Caddy, for a volunteer team. Pages are server-rendered, so no separate static host is needed. US West adds only a small delay for a Houston venue, and the load test (ARCH-071) checks it | Jonathan (issue #13) |
| DEC-029 | 2026-10-23 | Add `GET /health` to `06-api-and-screens.md` in a new System section. It returns 200 with plain text `ok`, with no database check and no version or environment details (API-001) | The app skeleton needs one route to prove the app starts, and Railway can use it as a health check (ARCH-010). Leaving out version and environment details gives attackers nothing to read | Jonathan (issue #19) |
| DEC-030 | 2026-10-23 | Staging auto-deploys `main`, production is deployed by hand, and every PR gets a temporary Railway preview environment copied from staging (ARCH-017). Service settings live in Railway, not in a config file: start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check `/health` (DEC-029), region US West (`us-west2`), 1 replica (ARCH-010). `.python-version` pins Python 3.14 for the build | Lets the team check each PR and `main` on a real HTTPS URL before production. Railway's `railway.json` stops being read on 2026-12-01, and its replacement (`.railway/railway.ts`) needs Node in a Python repo, so the settings are set once in Railway and recorded here. Railway's builder defaults to Python 3.13, so the version file is needed. Railway skips PRs from people outside the workspace, which keeps the public repo safe | Jonathan |
| DEC-031 | 2026-10-23 | If a My Code refresh fails (no connection, server error), the page tries again after `qr.poll_retry_seconds`, PROPOSED at 3 seconds (ARCH-074, API-030). HTMX shows 4xx error partials and does not swap 5xx responses (API-006) | Without a retry, one failed request on hotel Wi-Fi stops the code from changing until the player reloads, and a stale code gets refused (ARCH-022). ARCH-074 keeps polling intervals in config | Jonathan (PR #23) |
| DEC-032 | 2026-10-23 | Drop the PR size target (under 400 changed lines) and the 360px PR screenshot from AI-034, ENG-020, `CONTRIBUTING.md`, and the PR template. The browser check still runs before commits, including looking at 360px screenshots (AI-044). Any screenshot that is posted still uses fake data only (SAFE-036) | Jonathan's call: the line target and the PR screenshot slowed PRs down without adding much, because the browser check already covers 360px layout | Jonathan |
| DEC-033 | 2026-10-23 | Two players from the same church cannot share a full name (ARCH-033 LOCKED). Sign-up refuses a repeat with 409 `NAME_TAKEN` and sends the player to an usher (API-021). The database enforces it with a unique index on church and full name, ignoring case (DATA-016) | Login uses full name, church, and PIN (ARCH-032), so each combination must point to one player. Rare enough at one conference to handle in person | Jonathan (issue #25) |
| DEC-034 | 2026-10-24 | Sign-up asks "Are you 18 or older?" (yes or no) instead of "Are you under 18?" (SAFE-002). A "no" is saved as under 18. The stored field stays `is_under_18` (Player table in `05-data-model.md` unchanged), and who can see it does not change (SAFE-020) | Jonathan's call: "Are you under 18?" was confusing, since a "yes" there marks someone as a minor. Keeping the stored field avoids a schema change, and existing players stay correct | Jonathan |
| DEC-035 | 2026-10-24 | The phone look is "Mix" (UI-008): cream with blurred superbloom streaks, black serif titles and buttons, and frosted white cards, with new tokens in `07-design-system.md` section 2. The bottom bar becomes Home, My Code, Quests, and Scan moves onto My Code and Home (UI-030). One black main button per screen (UI-035). Buttons and labels are one or two words (UI-057), and the UI-033 and UI-034 examples are shortened to match. The main screen keeps the dark screen tokens (UI-042) | Jonathan picked Mix from the four looks in the design canvas (Bloom, Soft Focus, Film Garden, Mix) and asked for the Home tab, Scan inside My Code, and short copy | Jonathan |
| DEC-036 | 2026-10-25 | UI-008 drops "no images". The film grain is a tiny noise texture generated inside the CSS, with no image file to download. The bloom streaks stay CSS gradients | UI-008 asked for both film grain and no images, which can't both hold. Jonathan chose to keep the grain | Jonathan |
| DEC-037 | 2026-10-25 | The Mix vibe (UI-009) and the screen layouts from the Mix mockups go into `07-design-system.md`: Home (UI-036), My Code with a Scan button (UI-037), and the shared takeaways page (UI-038). The scan, icebreaker, then points order stays a note until GAME-016 is decided | Jonathan wants the design decisions written down first, with the app changes in a later PR | Jonathan |
| DEC-038 | 2026-10-26 | Add a feature tree: `feature-tree.yaml` splits every Planned feature into pieces of size S or M, each with the pieces it needs and the OPEN rules that lock it, and `16-feature-tree.md` holds its rules (ENG-105 to ENG-109). Live status stays in the README Project status. ENG-101 now claims one piece at a time, and the In progress and Working rows start with the piece ID. New Planned rows: Staff accounts and roles, Mix look on player screens, and Game day readiness | Volunteers could not tell which tasks were ready or small enough for one session. A tree lets `/pick-task` offer only unlocked pieces, and finishing one piece unlocks the next. Keeping status out of the foundation means finishing a piece never needs Jonathan's approval | Jonathan |

## 2. Resolved conflicts

| ID | Conflict | Result | Rules |
|---|---|---|---|
| C1 | Midday challenge: the brief lists it as a quest; the Blueprint says it is on hold | Not in v1. Parked design kept as OPEN. Removed from usher and game director v1 duties | GAME-120, PRD-050 |
| C2 | Golden QR drops on the main screen: in the brief only | OPEN. Not in v1 until Jonathan confirms | GAME-121 |
| C3 | Phone and email: the brief says "unless opted in"; the Blueprint says neither is collected | Not collected. LOCKED | SAFE-003 |
| C4 | Church score denominator: "per registered player" or "per player" | OPEN. The minimum players to appear on the board is also OPEN | GAME-089, GAME-082 |
| C5 | Icebreaker answers: the brief says the scanner types; the Blueprint says both earn; Wrapped counts answers "collected from the people you met" | OPEN | GAME-015, WRAP-012 |
| C6 | The sticker distribution table assumes 15 points per connection and a +10 bonus, but current values are 10 and +5 | The table is indicative only. Recalculate the sticker order after Playtest 1 | GAME-080 |
| C7 | Repo structure | One repo for server and front end. LOCKED | ARCH-005, DEC-001 |
| C8 | PIN reset: the Blueprint says an usher resets | Admin only | SAFE-023, DEC-004 |
| C9 | The Blueprint says "no milestone stickers"; Jonathan chose score milestones | Milestones unlock the blind box. The blind box stays the only source of stickers | GAME-072, DEC-002 |
| C10 | The Blueprint shows a live "boxes left" counter | No counter anywhere | GAME-077, DEC-003 |
| C11 | The Blueprint says "anyone can read" the summary page | Signed-in players only | SAFE-017, DEC-007 |
| C12 | The Blueprint's main screen shows leaderboards only; the setup brief adds a takeaway wall | Takeaway wall included | SAFE-018, DEC-008 |

## 3. Open decisions

Every OPEN rule in the foundation. Until an item is decided, do not build behavior that depends on it. Config values stay null and flags stay off. The "needed by" column is a suggestion.

| Rule | Question | Options | Owner | Needed by |
|---|---|---|---|---|
| PRD-011 | Target numbers for success metrics | Set from Playtest 1 results | Jonathan | After Playtest 1 |
| PRD-022 | Exact event dates | | Organizers | As soon as possible |
| PRD-053 | Whether prizes come from the game budget | This budget or another | Leadership | Early November |
| GAME-015 | Who types icebreaker answers (C5) | Each person types the other's answer, or only the scanner types | Game director | Kickoff |
| GAME-016 | When connection points are given | On scan, or after the answer is typed | Game director | Kickoff |
| GAME-019 | Icebreaker question pool and answer categories | | Game director | Before core build ends |
| GAME-024 | How long check-in stays live after a session | A set number of minutes, or manual close only | Game director | Before Playtest 1 |
| GAME-035 | Must a player check in before writing a takeaway? Is there a deadline? | Yes or no, and a deadline or none | Game director | Before core build ends |
| GAME-044 | Join points during a pause (Day 1 intro) | Give them, or hold them until the game is on | Game director | Kickoff |
| GAME-045 | Does the game booth count as a booth? | Yes or no | Game director | Before Playtest 1 |
| GAME-069 | Number of sticker packs | From the final order | Game director | Early February |
| GAME-078 | Sticker redemption window | Day 1 evening and Day 2 breaks, or also Sunday before the service | Game director | Before Playtest 1 |
| GAME-079 | Sticker trading | Swap Spot with no points, or no trading | Game director | Before Playtest 1 |
| GAME-089 | Church score denominator (C4) | All registered players, or players with at least 1 point | Game director | Kickoff |
| GAME-082 | Minimum players for a church to appear on the board | A number | Game director | Before Playtest 1 |
| GAME-083 | Rows on each main screen leaderboard | A number | Designer, game director | Before Playtest 2 |
| GAME-084 | Tie-breaks on boards and for prizes | For example, earlier to reach the score wins | Game director | Before Playtest 1 |
| GAME-085 | Leaderboard or own rank on the phone | Show or not | Game director | Before core build ends |
| GAME-088 | Two players with the same first name and church on a board | For example, last initial, or a number | Game director, safety reviewer | Before Playtest 1 |
| GAME-091 | Raffle with entries from points | Yes or no | Game director, leadership | Before Playtest 1 |
| GAME-092 | Final prize list | | Game director, leadership | Before Playtest 2 |
| GAME-105 | Venue timezone | IANA timezone name | Organizers | When the venue is confirmed |
| GAME-106 | Daily game hours, off overnight | A time window, or manual | Leadership | Before Playtest 1 |
| GAME-107 | Automatic pause schedule | Load the timetable, or manual only | Developers | Before feature complete |
| GAME-120 | Midday challenge (C1) | Return or not; then format, length, team forming | Game director | Not v1 |
| GAME-121 | Golden QR drops (C2) | In or out | Jonathan | Not v1 unless confirmed |
| GAME-122 | Players without a phone | Usher-created account, usher-only participation, or not supported | Game director, safety reviewer | Before Playtest 1 |
| SAFE-014 | Data retention after the event | A number of days, at least until Wrapped closes | Leadership | Before Playtest 2 |
| SAFE-027 | Game off overnight and outside set hours | Same as GAME-106 | Leadership | Before Playtest 1 |
| ARCH-031 | Login and sign-up rate limits per IP | Numbers per time window | Developers, safety reviewer | Before core build ends |
| ARCH-053 | Backup frequency and off-Railway copy | | Developers | Before Playtest 2 |
| ARCH-072 | Load test profile | Sign-ups per second, duration | Developers | Before Playtest 2 |
| API-031 | Main screen refresh interval | Seconds | Developers | Before Playtest 1 |
| DATA-010 | Where church region data comes from | Added to the church list by an admin | Jonathan, game director | Before Wrapped build |
| WRAP-011 | Regions on card 2 | Depends on DATA-010 | Jonathan | Before Wrapped build |
| WRAP-012 | Card 3 counts and verse matching | Depends on GAME-015 and GAME-019 | Game director, developers | Before Wrapped build |
| WRAP-017 | Play style tie-break | A fixed order, or show both | Game director | Before Wrapped build |
| WRAP-030 | Church recap for youth pastors | Build with a new login, or skip | Jonathan, leadership | Before feature complete |
| WRAP-033 | How the Wrapped image is made | In the browser or on the server | Developers | Before Wrapped build |
| OPS-040 | Where real event data lives | A private Google Drive folder (planned default) or another place | Jonathan | Before any real data exists |

## 4. PROPOSED values to review after Playtest 1

These are built as written, then reviewed with playtest data.

| Rule | Value now | Question | Owner |
|---|---|---|---|
| GAME-010, GAME-011 | 10 per connection, +5 bonus | Keep, or raise to 15 and +10 so meeting people stays the top earner | Game director |
| GAME-022 | Check-in tiers 25, 20, 15, 10, 5 | Keep or change | Game director |
| GAME-070, GAME-071 | Sticker every 300 points, max 3 | Keep or change, then recalculate the sticker order (GAME-080) | Game director |
| SAFE-008 | Review every shared post | Every shared post, or only posts from under-18 players | Leadership |
