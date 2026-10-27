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

Status last updated: 2026-10-26 by Claude Opus 5.5 / @jonathango98

**Before you start anything**, check that nobody else is on it. A branch only shows up here after it merges, so also run:

```bash
git fetch --prune
git branch -r              # every open branch
gh pr list --state open    # every open PR, including drafts
```

### Working

Done and live. Newest first: add your row at the top, in plain words. Who built it, the rule IDs, and the details go in [CHANGELOG.md](CHANGELOG.md).

| What | Done |
|---|---|
| `/pick-task` now offers only work that's ready to start, sized to fit the volunteer's Claude plan, and double-checks nobody else claimed it before calling dibs | 2026-10-26 |
| Feature tree: every feature is split into small pieces, each saying what it needs first, so volunteers can see what's ready to start. Pieces that wait on an undecided rule stay locked. A map of the tree updates itself after every merge | 2026-10-26 |
| Screen skeleton: every player screen is a plain page, and every button and tab goes to the right next screen. The bottom bar is now Home, My Code, and Quests, and players land on Home after joining or logging in. No final look and no game logic yet | 2026-10-26 |
| Automatic browser tests now check joining and logging in on Safari's engine too. They used to fail there because the test site had no HTTPS. Real players were never affected | 2026-10-25 |
| Joining asks "Are you 18 or older?" instead of "Are you under 18?", which was confusing | 2026-10-24 |
| Joining and logging in: players join with their name, church, and a PIN, land on their own code, and can log in on another phone. Too many wrong PINs lock the account. Unlocking comes with the Admin console | 2026-10-23 |
| My Code: each player has their own QR code that keeps changing, so a screenshot can't be passed around | 2026-10-23 |
| Test server online: every change to the main code goes live on a private test site, and each proposed change gets its own preview link | 2026-10-23 |
| App foundation: the app starts, reads the game settings, and every player page shares one look (score on top; My Code, Scan, and Quests buttons at the bottom) | 2026-10-23 |
| Health check added to the route list, so the host can tell the app is running | 2026-10-23 |
| Project setup: game rules and plans written, hosting chosen, repo safety checks, and AI helper tools for volunteers | 2026-10-23 |

### In progress

Has an open branch. Newest first: add your row at the top in the first commit on your branch, push, and open a draft PR right away (ENG-101).

| Feature | Branch | PR | Started | By |
|---|---|---|---|---|
| Answer most of the open game questions (connection points, church score, check-in, stickers, Wrapped, data retention) | `docs/resolve-open-decisions` | draft | 2026-10-26 | Claude Opus 5.5 / @jonathango98 |

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
| Stickers (Open Box) | `stickers` | GAME-073, GAME-076 | January build |
| Leaderboards and church score | `leaderboards` | `02-game-rules.md` section 7, UI-041 | January build |
| Usher console | `usher` | GAME-112 | January build |
| Admin console | `admin` | GAME-110 | January build |
| Main screen views (leaderboards, takeaway wall, check-in QR, paused) | `screen` | UI-040, UI-041, SAFE-018, GAME-020 | January build |
| Wrapped cards | `wrapped` | WRAP-010 | January build |
| Conference recap screen | `recap` | WRAP-020 | January build |
| Game day readiness: log out, rate limits, backups, load test, data cleanup | `ready` | ARCH-031, ARCH-053, ARCH-071, SAFE-014 | Before Playtest 2 |

## License

MIT. See [LICENSE](LICENSE). The license covers the code and docs in this repo. It does not cover sticker artwork or real event content, which are not stored here.
