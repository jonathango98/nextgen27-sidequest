# 12 Team and Timeline

- Status: Active (dates are approximate until the event date is confirmed, PRD-022)
- Owner: Jonathan (@jonathango98)
- Version: 1.3.0
- Last updated: 2026-10-28

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

This file lists the roles, which folders each role owns, the milestones, and what is frozen when. It names roles, not people.

## 1. Roles

| Role | How many | Responsibilities |
|---|---|---|
| Project lead | 1 (Jonathan) | Owns the foundation, the repo, and final decisions. Point of contact |
| Game director | 1 | Rules and point values, icebreaker questions, blind box milestones and contents, prizes, both playtests |
| Backend developer | 1 | Server, points service, QR codes, auth, database |
| Player app developer | 1 | Player pages, scanner, Journal, Wrapped cards |
| Admin and screens developer | 1 | Usher console, admin console, main screen views |
| Infra and QA developer | 1 (optional) | Hosting, deployment, backups, load tests, testing |
| UI designer | 1 | App look, leaderboard screens, design tokens |
| Ushers | 5 to 10 (game day only) | Game booth and blind box line, booth scans, helping people join, dead phones |
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
| November 2 to December 18 | Core build | Joining, personal codes, scanning, points, game pause. Build weeks 1 to 7 |
| December 21 to January 3 | Holiday break | Nothing critical. Bonus work only (ENG-072) |
| January 4 to 15 | Build continues | Remaining features, including Wrapped (WRAP-005). Build weeks 8 and 9 |
| Friday January 15 | Every feature done (target) | Every feature works end to end, about a week before the gate (PRD-054) |
| Late January | Feature complete (gate) | Every feature works end to end. Nothing new after this (ENG-070) |
| Late January | Playtest 1 | 20 to 30 people from a youth group. Point values reviewed after |
| Early February | Blind boxes ordered | Contents decided (GAME-068). Order size recalculated (GAME-080) |
| Mid February | Playtest 2 and venue walkthrough | Hotel Wi-Fi load test of the join moment (OPS-030). Ends with a test Wrapped |
| Late February | Final prep | Polish continues, usher training, intro slides |
| 5 to 7 March 2027 | NextGen Conference 2027 | Game runs Day 1 evening and Day 2. Results Sunday |

- **PRD-052** [LOCKED] One gate: feature complete (late January). There is no code freeze: polish and fixes continue up to the event, and ARCH-016 still bars production deploys during live game hours (DEC-053).

### Build weeks

- **PRD-054** [PROPOSED] Every feature is done by Friday 2027-01-15, about a week before the feature complete gate and Playtest 1, so late January is for fixes, not building. Each feature has a `due` Friday in `feature-tree.yaml`. A piece that other pieces need is due by the earliest due date among them, so blockers come first. `/pick-task` offers the pieces due soonest and flags late ones (DEC-056).

The weeks follow the order pieces need each other (`16-feature-tree.md`), spread evenly. They do not count how many people are free: the plan is about 106 sessions of work (S is one session, M is two), so about 12 sessions a week across the team. A feature's milestone says which group it belongs to, and its due date says when it is done, so a January build feature can be due in December. If Playtest 1's date moves, shift the `due` dates in one PR.

| Week | Dates | Features due that Friday |
|---|---|---|
| 1 | November 2 to 6 | None. Start the backbone pieces (`16-feature-tree.md` section 2) |
| 2 | November 9 to 13 | None. Backbone continues |
| 3 | November 16 to 20 | `staff` Staff accounts and roles, `points` Points service |
| 4 | November 23 to 27 | `look` Mix look on player screens |
| 5 | November 30 to December 4 | `game-state` Game states and pause, `connections` Scanner and connections, `usher` Usher console |
| 6 | December 7 to 11 | `home` Home and Quests pages, `checkin` Session check-in, `admin` Admin console |
| 7 | December 14 to 18 | `explore` Explore, `blind-box` Blind boxes, `leaderboards` Leaderboards and church score |
| Break | December 21 to January 3 | Nothing due. Bonus work only (ENG-072) |
| 8 | January 4 to 8 | `journal` Journal and Summary page, `ready` Game day readiness |
| 9 | January 11 to 15 | `screen` Main screen views, `wrapped` Wrapped cards, `recap` Conference recap screen |
| Buffer | January 18 to feature complete | Fixes and late pieces only |

## 4. What is frozen when

| From | Frozen |
|---|---|
| Kickoff | The foundation (changes only through Foundation Change Requests) |
| Feature complete | The feature list. No new features |
| After Playtest 1 | Point values, once the game director updates `game-config.yaml` |
| Blind boxes ordered | The contents and the order size |

## 5. Leadership asks

Budget amounts are not written in this repo.

| Ask | What | When |
|---|---|---|
| Approval | Game and safety rules | Early November |
| Ushers | 5 to 10 on game day plus short training | Confirmed late January, trained in February |
| Wi-Fi | Handles about 300 phones joining at once, tested at a walkthrough | Mid-February walkthrough |
| Stage time | Day 1 evening intro, Day 2 reminders, Sunday results | When the program schedule is set |
| Budget | Server hosting, hardware and printed materials, blind box contents. Amount set after the design locks | Early November for approval. Blind boxes ordered early February |

- **PRD-053** [OPEN] Prizes are not in the budget ask yet. Leadership confirms whether prizes come from this budget or another (GAME-092).
