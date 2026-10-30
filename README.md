# Side Quest

- Status: Active
- Owner: Jonathan (@jonathango98)
- Version: 1.1.0
- Last updated: 2026-10-20

> Not protected. Every PR keeps the Project status section below accurate and adds an entry to [CHANGELOG.md](CHANGELOG.md) (ENG-100 to ENG-104, AI-070). Only edit the Project status section. The rest of this file changes through a Foundation Change Request.

Side Quest is an optional phone game for NextGen Conference 2027, a conference for youth leaders. Its goal is simple: help youth leaders meet people from other churches. Players join by scanning one QR code. It runs in the phone's browser, with nothing to install. Players earn points by meeting people, exploring the venue, and writing takeaways after sessions.

The app is built by a small volunteer team. It is not built yet. This repo currently holds the foundation: the rules everything else is built from.

## Start here

- [foundation/README.md](foundation/README.md): the source of truth for the product, rules, safety, architecture, and design
- [CONTRIBUTING.md](.github/CONTRIBUTING.md): how to set up, make your first PR, and work with AI coding agents
- [SECURITY.md](.github/SECURITY.md): how to report a vulnerability, and what never goes in this repo
- [AGENTS.md](AGENTS.md): rules for AI coding agents
- [CHANGELOG.md](CHANGELOG.md): every change, newest first, with who made it and when

## Project status

Status last updated: 2026-10-29 by Claude Opus 5.5 / @OwenTjandra

**Before you start anything**, check that nobody else is on it. A branch only shows up here after it merges, so also run:

```bash
git fetch --prune
git branch -r              # every open branch
gh pr list --state open    # every open PR, including drafts
```

### Working

What the app can do today, grouped by area, in plain words for anyone to read. When your piece works end to end, update its area's row (or add one): set today's date, add the piece ID in backticks to Pieces, and say what people can now do (ENG-108). Who built it, the rule IDs, and the details go in [CHANGELOG.md](CHANGELOG.md).

| Updated | Pieces | Area | What works today |
|---|---|---|---|
| 2026-10-28 | `auth.join-login` `ready.logout` | Joining and logging in | Players join with their name, church, a PIN, and an "Are you 18 or older?" question. They can log in again on another phone. Too many wrong PINs lock the account. A settings gear on Home has Log out, which asks to confirm, then signs out that phone only, so the next person who picks it up can't play as them |
| 2026-10-23 | `code.my-code` | Personal QR code | Each player has their own QR code on the My Code screen. It keeps changing, so a screenshot can't be passed around |
| 2026-10-26 | `screens.skeleton` | Player screens | Every player screen exists as a plain page, and every button and tab leads to the right next screen. The bottom bar has Home, My Code, and Quests. The final look and the game itself come next |
| 2026-10-27 | | Game rules | The full game rules are written down, and most open game questions are answered. Prizes and what goes inside the blind boxes are still to be decided |
| 2026-10-28 | `app.foundation` `infra.hosting` | Behind the scenes | A private test site updates with every change, and each proposed change gets its own preview link. Automatic tests check pages on the iPhone browser engine too. Game numbers live in one settings file, so they're easy to tune after playtests. Volunteers get a map of what's ready to build and a `/pick-task` helper to claim work. Every feature has a due week so all of them are done by January 15, before Playtest 1, and `/pick-task` offers what's due soonest |
| 2026-10-29 | `connections.table` | Meeting people | The game has a place to remember who met whom. The same two people can only ever be saved as a pair once, whoever scans whom, and nobody can connect with themselves. It also remembers which new churches each player has met, so the new church bonus pays once. Scanning comes next |
| 2026-10-28 | `points.audit-log` | Audit log | The game has a notebook of important actions, saying who did what, to which record, why, and when. Once written, an entry can't be changed or erased, and it never holds PINs or names. Point awards and admin tools will write to it as they are built |
| 2026-10-29 | `ready.retention` | Protecting players after the event | A cleanup command deletes every player's personal data once the keep-until date has passed. That date is a set number of days after the event ends, and both live in the game settings file. Before that date it refuses and removes nothing. It shows what it would remove first, and only deletes when confirmed. Deleted data can't be recovered from the database file afterwards. Then it lists the steps to do by hand on the same day: Railway backups, server logs, the real data folder, and staff accounts |
| 2026-10-29 | `game-state.core` | Game on, paused, or off | The game is always on, paused, or off. While it is paused or off, anything that earns points is refused with a friendly message, and the change applies to the very next tap. Admin buttons to switch it and the pause banner come next |
| 2026-10-29 | `connections.scanner-camera` | Scanner | The Scan page opens the phone's back camera and reads QR codes, on iPhone Safari too. A Side Quest code shows "Got it!", any other code says it isn't a Side Quest code, and a blocked camera says so with a Try again button. Saving who met whom comes next |
| 2026-10-29 | `staff.accounts` | Staff accounts | The game has a safe place for usher and admin accounts. Each person gets their own, with a password that is stored so nobody can read it, and an account can be switched off. A setup command makes the very first admin from a password kept on the server; running it again changes nothing. Logging in as staff comes next |

### In progress

Has an open branch. Newest first: add your row at the top in the first commit on your branch, push, and open a draft PR right away (ENG-101).

| Feature | Branch | PR | Started | By |
|---|---|---|---|---|

### Planned

In the foundation, no branch yet. Order follows `foundation/12-team-timeline.md`. Each feature is split into pieces in `foundation/feature-tree.yaml`. See what's ready in the [feature tree map](docs/feature-tree.md) ([interactive](https://jonathango98.github.io/nextgen27-sidequest/)). Claim one piece at a time, and remove the feature's row when its last piece is Working (ENG-108).

| Feature | Tree | Spec | Milestone |
|---|---|---|---|
| Staff accounts and roles | `staff` | ARCH-035, ARCH-036 | Core build |
| Scanner and connections, with icebreaker | `connections` | ARCH-025, GAME-017 | Core build |
| Points service | `points` | ARCH-040 | Core build |
| Game states and pause | `game-state` | `02-game-rules.md` section 9, UI-033 | Core build |
| Mix look on player screens | `look` | UI-008, UI-009, DEC-037 | January build |
| Home and Quests pages | `home` | GAME-070, `06-api-and-screens.md` | January build |
| Session check-in | `checkin` | GAME-020 | January build |
| Explore | `explore` | `02-game-rules.md` section 5 | January build |
| Journal and Summary page | `journal` | GAME-031, SAFE-009, SAFE-017 | January build |
| Blind boxes (Open Box) | `blind-box` | GAME-072, GAME-073, GAME-076 | January build |
| Leaderboards and church score | `leaderboards` | `02-game-rules.md` section 7, UI-041 | January build |
| Usher console | `usher` | GAME-112 | January build |
| Admin console | `admin` | GAME-110 | January build |
| Main screen views (leaderboards, takeaway wall, check-in QR, paused) | `screen` | UI-040, UI-041, SAFE-018, GAME-020 | January build |
| Wrapped cards | `wrapped` | WRAP-010 | January build |
| Conference recap screen | `recap` | WRAP-020 | January build |
| Game day readiness: log out, rate limits, backups, load test, data cleanup | `ready` | ARCH-031, ARCH-053, ARCH-071, SAFE-014 | January build |

## License

MIT. See [LICENSE](LICENSE). The license covers the code and docs in this repo. It does not cover sticker artwork or real event content, which are not stored here.
