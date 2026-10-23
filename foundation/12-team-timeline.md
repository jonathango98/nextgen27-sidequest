# 12 Team and Timeline

- Status: Active (dates are approximate until the event date is confirmed, PRD-022)
- Owner: Jonathan (@jonathango98)
- Version: 1.1.0
- Last updated: 2026-10-23

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

This file lists the roles, which folders each role owns, the milestones, and what is frozen when. It names roles, not people.

## 1. Roles

| Role | How many | Responsibilities |
|---|---|---|
| Project lead | 1 (Jonathan) | Owns the foundation, the repo, and final decisions. Point of contact |
| Game director | 1 | Rules and point values, icebreaker questions, sticker milestones, prizes, both playtests |
| Backend developer | 1 | Server, points service, QR codes, auth, database |
| Player app developer | 1 | Player pages, scanner, Journal, Wrapped cards |
| Admin and screens developer | 1 | Usher console, admin console, main screen views |
| Infra and QA developer | 1 (optional) | Hosting, deployment, backups, load tests, testing |
| Sticker and UI designer | 1 | Sticker set, app look, leaderboard screens, design tokens |
| Ushers | 5 to 10 (game day only) | Game booth and sticker line, booth scans, helping people join, dead phones |
| Safety reviewer | 1 (to be named) | Second-person review of safety-sensitive changes (SAFE-016) |

- **PRD-050** [LOCKED] The midday challenge is not part of anyone's v1 duties (conflict C1).

## 2. Folder ownership

- **PRD-051** [PROPOSED] Each developer role owns the folders for its area label (ENG-041). Changes in other areas are fine (DEC-025).

| Role | Area label | Folders (PROPOSED layout, ARCH-008) |
|---|---|---|
| Backend developer | `area:backend` | `app/main.py`, `app/config.py`, `app/services/`, `app/auth/`, `app/models/`, `migrations/` |
| Player app developer | `area:player-app` | `app/routes/player/`, `app/templates/player/`, `app/templates/partials/`, `app/static/js/` |
| Admin and screens developer | `area:admin-screens` | `app/routes/usher/`, `app/routes/admin/`, `app/routes/screen/`, and their templates |
| Designer | `area:design` | `app/static/css/`, `app/static/icons/` |
| Infra and QA developer | (none yet) | Deployment docs and load test scripts, location decided at kickoff |
| Project lead | (protected) | All protected paths (ENG-080) |

## 3. Milestones

| When | Milestone | What it means |
|---|---|---|
| Early November | Leadership approval | Game and safety rules approved, budget approved |
| Mid November | Kickoff | Plan locked, repo set up, roles claimed, PROPOSED items confirmed or changed |
| Late November to December 18 | Core build | Joining, personal codes, scanning, points, game pause |
| December 21 to January 3 | Holiday break | Nothing critical. Bonus work only (ENG-072) |
| January | Build continues | Remaining features, including Wrapped (WRAP-005) |
| Late January | Feature complete (gate) | Every feature works end to end. Nothing new after this (ENG-070) |
| Late January | Playtest 1 | 20 to 30 people from a youth group. Point values reviewed after |
| Early February | Stickers ordered | Final sticker list locked for printing. Order size recalculated (GAME-080) |
| Mid February | Playtest 2 and venue walkthrough | Hotel Wi-Fi load test of the join moment (OPS-030). Ends with a test Wrapped |
| Late February | Code freeze (gate) | Polish only, usher training, intro slides (ENG-071) |
| Early March | NextGen Conference 2027 | Game runs Day 1 evening and Day 2. Results Sunday |

- **PRD-052** [LOCKED] Two gates: feature complete (late January) and code freeze (late February). Both are firm, so the team keeps about two weeks of buffer before the event.

## 4. What is frozen when

| From | Frozen |
|---|---|
| Kickoff | The foundation (changes only through Foundation Change Requests) |
| Feature complete | The feature list. No new features |
| After Playtest 1 | Point values, once the game director updates `game-config.yaml` |
| Stickers ordered | The sticker list and the order size |
| Code freeze | All code except bug fixes with an approved issue |

## 5. Leadership asks

Budget amounts are not written in this repo.

| Ask | What | When |
|---|---|---|
| Approval | Game and safety rules | Early November |
| Ushers | 5 to 10 on game day plus short training | Confirmed late January, trained in February |
| Wi-Fi | Handles about 300 phones joining at once, tested at a walkthrough | Mid-February walkthrough |
| Stage time | Day 1 evening intro, Day 2 reminders, Sunday results | When the program schedule is set |
| Budget | Server hosting, hardware and printed materials, sticker printing. Amount set after the design locks | Early November for approval. Stickers ordered early February |

- **PRD-053** [OPEN] Prizes are not in the budget ask yet. Leadership confirms whether prizes come from this budget or another (GAME-092).
