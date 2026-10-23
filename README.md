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
- [CONTRIBUTING.md](CONTRIBUTING.md): how to set up, make your first PR, and work with AI coding agents
- [SECURITY.md](SECURITY.md): how to report a vulnerability, and what never goes in this repo
- [AGENTS.md](AGENTS.md): rules for AI coding agents
- [CHANGELOG.md](CHANGELOG.md): every change, newest first, with who made it and when

## Project status

Status last updated: 2026-10-23 by Claude Opus 5.5 / @jonathango98

**Before you start anything**, check that nobody else is on it. A branch only shows up here after it merges, so also run:

```bash
git fetch --prune
git branch -r              # every open branch
gh pr list --state open    # every open PR, including drafts
```

### Working

Merged to `main` and works end to end.

| Feature | Spec | Done | By |
|---|---|---|---|
| Foundation docs v1 | `foundation/` | 2026-10-19 | @jonathango98 |
| Agent rules | `AGENTS.md`, `CLAUDE.md`, `foundation/10-ai-agent-rules.md` | 2026-10-19 | @jonathango98 |
| `.gitignore` | ENG-056, ARCH-007 | 2026-10-19 | @jonathango98 |
| Shared task-observer skill | `.claude/skills/task-observer/` | 2026-10-19 | @jonathango98 |
| Change log and project status rules | ENG-100 to ENG-104, AI-070 to AI-073 | 2026-10-21 | Claude Opus 5.5 / @jonathango98 |
| Browser check skill and check-before-commit rule | `.claude/skills/browser-check/`, AI-033, AI-044 | 2026-10-22 | Claude Opus 5.5 / @jonathango98 |

### In progress

Has an open branch. Add your row in the first commit on your branch, push, and open a draft PR right away (ENG-101).

| Feature | Branch | PR | Started | By |
|---|---|---|---|---|
| Repo guardrails (CODEOWNERS, repo settings) | `chore/7-repo-guardrails` | #8 | 2026-10-23 | Claude Opus 5.5 / @jonathango98 |

### Planned

In the foundation, no branch yet. Order follows `foundation/12-team-timeline.md`.

| Feature | Spec | Milestone |
|---|---|---|
| Join, PIN set, and log in | SAFE-002, SAFE-021, ARCH-032 | Core build |
| My Code (rotating QR) | GAME-001 | Core build |
| Scanner and connections, with icebreaker | ARCH-025, GAME-017 | Core build |
| Points service | ARCH-040 | Core build |
| Game states and pause | `02-game-rules.md` section 9, UI-033 | Core build |
| Home and Quests pages | GAME-070, `06-api-and-screens.md` | January build |
| Session check-in | GAME-020 | January build |
| Explore | `02-game-rules.md` section 5 | January build |
| Journal and Summary page | GAME-031, SAFE-009, SAFE-017 | January build |
| Stickers (Open Box) | GAME-073, GAME-076 | January build |
| Leaderboards and church score | `02-game-rules.md` section 7, UI-041 | January build |
| Usher console | GAME-112 | January build |
| Admin console | GAME-110 | January build |
| Main screen views (leaderboards, takeaway wall, check-in QR, paused) | UI-040, UI-041, SAFE-018, GAME-020 | January build |
| Wrapped cards | WRAP-010 | January build |
| Conference recap screen | WRAP-020 | January build |

## License

MIT. See [LICENSE](LICENSE). The license covers the code and docs in this repo. It does not cover sticker artwork or real event content, which are not stored here.
