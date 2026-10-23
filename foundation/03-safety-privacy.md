# 03 Safety and Privacy

- Status: Active (each rule has its own status)
- Owner: Jonathan (@jonathango98)
- Version: 1.0.1
- Last updated: 2026-10-23

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

Some players are under 18. This file comes first whenever a feature touches people's data. If a feature request conflicts with this file, this file wins. Stop and ask Jonathan.

## 1. Non-negotiables

These are LOCKED. No feature, playtest, or deadline changes them without a Foundation Change Request approved by Jonathan.

- **SAFE-001** [LOCKED] Collect as little as possible and show as little as possible.
- **SAFE-002** [LOCKED] Sign-up collects exactly these fields and nothing else: first name, last name, church (picked from a preloaded church list), "Are you under 18?" (yes or no), and a 4-digit PIN.
- **SAFE-003** [LOCKED] No email address and no phone number are collected, for anyone, for any reason (conflict C3).
- **SAFE-004** [LOCKED] Other players see only a player's first name and church. Last names are visible to admins and ushers only.
- **SAFE-005** [LOCKED] There is no messaging between players of any kind: no chat, no comments, no replies, no direct messages.
- **SAFE-006** [LOCKED] Icebreaker answers are visible only to the two people in that connection. No admin, usher, or main screen view shows them. Wrapped may count them for the two people only (WRAP-012).
- **SAFE-007** [LOCKED] Shared takeaways are reviewed before anyone else can see them.
- **SAFE-009** [LOCKED] "Anonymous" means anonymous to other players only. Admins can still see who wrote an anonymous post, so a concerning post can be followed up. The Journal form says this in plain words next to the choice (UI-031).
- **SAFE-011** [LOCKED] No money anywhere. Points cannot be bought. The blind box is a free mystery pack earned through play.
- **SAFE-013** [LOCKED] The game never competes with the program. It is paused during every session (GAME-101), and the main screen shows game content only between sessions (UI-040).
- **SAFE-024** [LOCKED] The main screen never shows a photo of a minor without consent.

## 2. Minors

- **SAFE-019** [LOCKED] Under-18 players appear on leaderboards and the takeaway wall the same way as everyone else: first name and church only.
- **SAFE-020** [PROPOSED] The under-18 answer is visible to admins only. Players, ushers, and the main screen never see it.
- **SAFE-025** [PROPOSED] v1 has no photo upload of any kind. This keeps SAFE-024 simple: the app holds no photos. The photobooth is a physical booth, and the app only records the visit.
- **SAFE-026** [LOCKED] Hidden items stay in conference areas only. Never guest floors, restrooms, stairwells, or parking. See SAFE-010.
- **SAFE-015** [LOCKED] Leadership checks these rules against the organization's child safety policy as part of approval.
- **SAFE-027** [OPEN] Whether the game is off overnight and outside set hours. Leadership decides (GAME-106). Until decided, admins set the game to off at the end of each game day by hand.

## 3. Who can see what

Legend: Yes = can see. No = cannot see. Own = only their own record.

| Field | The player | Other players | Usher | Admin | Main screen |
|---|---|---|---|---|---|
| First name | Own | Yes | Yes | Yes | Yes (leaderboard, named takeaways) |
| Last name | Own | No | Yes | Yes | No |
| Church | Own | Yes | Yes | Yes | Yes |
| Under-18 answer | Own | No | No | Yes | No |
| PIN | No (only the person knows it) | No | No | No (stored hashed, never shown) | No |
| Score | Own | OPEN (GAME-085) | Yes | Yes | Yes (top of leaderboard) |
| Stickers earned and claimed | Own | No | Yes (at claim time) | Yes | No |
| People you connected with | Own (first name and church) | No | No | Yes (pairs only, for fixing scores) | No |
| Icebreaker answers | Own pairs only | Only the other person in that pair | No | No | No |
| Private takeaway | Own | No | No | Yes (for review of junk and concerns) | No |
| Shared named takeaway, after approval | Own | Yes (with first name and church) | No | Yes | Yes (takeaway wall) |
| Shared anonymous takeaway, after approval | Own | Yes (as "Anonymous") | No | Yes (with author) | Yes (as "Anonymous") |
| Check-ins, booth visits, hidden items | Own | No | Yes (the ones they record) | Yes | No |
| Login attempts and lockout | No | No | No | Yes | No |
| Audit log | No | No | No | Yes | No |

- **SAFE-028** [LOCKED] If a screen, export, or log would show a field to a role marked "No" above, it is a bug. Fix it before anything else.
- **SAFE-029** [PROPOSED] Admin views of private takeaways exist only for moderation. The admin console does not list private takeaways by default. An admin opens one only from a specific report or a junk-entry check, and that view writes an audit row.

## 4. Anonymity and moderation

- **SAFE-008** [PROPOSED] Review scope. Until leadership decides, every shared post is reviewed (the stricter option). The other option is to review only posts from under-18 players. Config: `journal.review_scope`.
- **SAFE-040** [LOCKED] Review outcomes: approve (the post becomes visible) or reject (the post stays hidden from everyone but the writer and admins). Rejecting a post does not remove its points. Removing points is a separate admin revocation with a reason (GAME-111).
- **SAFE-041** [PROPOSED] An admin can hide an approved post at any time. Hiding writes an audit row.
- **SAFE-042** [LOCKED] A concerning post (for example, one that suggests someone may be at risk) is followed up by organizers in person, following the organization's child safety policy. The app's job is only to let admins see the author. Nobody follows up inside the app.
- **SAFE-043** [PROPOSED] Icebreaker questions never ask for contact details, social media handles, room numbers, or where someone is staying. Free-text answers could otherwise become a way to message (SAFE-005). The game director checks the question pool for this.

## 5. Accounts and login

- **SAFE-021** [LOCKED] The PIN is 4 digits. It is stored only as a slow hash (ARCH-030). It is never shown, logged, or sent back to the phone. Config: `auth.pin_digits`.
- **SAFE-022** [LOCKED] After 5 wrong PIN tries in a row, the account locks. Config: `auth.pin_max_attempts`.
- **SAFE-023** [LOCKED] Only an admin can reset a locked PIN. This replaces the Blueprint's "until an usher resets it" (decision DEC-004). Config: `auth.pin_reset_role`.
- **SAFE-044** [PROPOSED] Before resetting a PIN, the admin checks the person's name badge in person. The player then sets a new PIN on their phone.

## 6. Other rules

- **SAFE-010** [LOCKED] The hidden item list and item locations never appear in the repo, in issues, or in screenshots. They live with the real event data (OPS-040).
- **SAFE-012** [LOCKED] Prizes are claimed in person on Sunday (GAME-090).
- **SAFE-014** [OPEN] How long names, icebreaker answers, and takeaways are kept after the event. Leadership decides. It must be at least as long as Wrapped stays open (WRAP-004). After that date, all player data is deleted from the server and from backups. Config: `data.retention_days_after_event`.
- **SAFE-017** [LOCKED] The summary page (shared takeaways) is visible to signed-in players only. It is not a public web page.
- **SAFE-018** [LOCKED] The main screen shows a takeaway wall with approved shared takeaways only, between sessions only. Named posts show first name and church. Anonymous posts show "Anonymous".

## 7. Second-person review

- **SAFE-016** [LOCKED] A second person reviews anything on this list before it goes live. The PR gets the `safety-review` label. The second reviewer is the safety reviewer (to be named, see CODEOWNERS placeholder `SAFETY_REVIEWER`) or Jonathan if no reviewer is named yet.

Review list:

| Area | Examples |
|---|---|
| Sign-up | The sign-up form, the fields saved, the church list |
| PIN and login | Hashing, lockout, reset, session cookies, rate limits |
| Roles and admin controls | Any admin or usher route, role checks, manual awards and revocations |
| Minors' data | Anything that saves, shows, or exports the under-18 answer |
| Takeaways | Visibility choices, review queue, anonymous author display, the takeaway wall |
| Main screen | Anything new shown on the main screen |
| Data lifecycle | Exports, backups, retention, deletion |
| Database schema | Migrations that touch player, takeaway, or connection tables |
| Logging | What gets written to logs |

## 8. Public repo rules

This repo is public. Anyone on the internet can read every file, every issue, every PR, and the full commit history.

- **SAFE-030** [LOCKED] Never commit any of these: secrets, API keys, `.env` files, QR or TOTP signing keys, session keys, admin passwords, admin URLs that contain tokens, SQLite database files (including `-wal` and `-shm` files), backups, exports, logs, real attendee data of any kind (names, churches, under-18 answers, PINs, icebreaker answers, takeaways), playtest data, screenshots or photos showing real people, hidden item locations or the hidden item list, volunteer contact details.
- **SAFE-031** [LOCKED] Test and seed data is obviously fake. Use names like "Test Player 1" and "Example Church A". Never use a real person's name, even as a joke.
- **SAFE-032** [LOCKED] Secrets come only from environment variables on the server. The repo may ship a `.env.example` file with placeholder values only.
- **SAFE-033** [LOCKED] Assume attackers read the source. Security never depends on hidden code. See the threat model in `04-architecture.md` (ARCH-060).
- **SAFE-034** [LOCKED] If a secret or real data is committed by mistake: stop, tell Jonathan right away, and rotate the secret. Do not try to rewrite git history yourself. Jonathan handles cleanup.
- **SAFE-035** [PROPOSED] CI runs a forbidden-files check that fails if any tracked file matches the patterns in SAFE-030 (ENG-061). This check is planned for the guardrails phase and does not exist yet.
- **SAFE-036** [LOCKED] Screenshots in issues and PRs use fake data only. No real names, no real faces, no venue photos that show where items are hidden.
- **SAFE-037** [LOCKED] Docs in this repo contain no personal contact details, no volunteer or attendee names, no budget amounts, no hidden item locations, and no room-level schedule tied to where minors will be.
