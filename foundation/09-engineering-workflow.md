# 09 Engineering Workflow

- Status: Active (each rule has its own status)
- Owner: Jonathan (@jonathango98)
- Version: 1.0.0
- Last updated: 2026-10-19

> Protected file. AI agents: read only. To propose a change, open a Foundation Change Request issue.

This file says how we use Git and GitHub, how work gets reviewed, and when a change is done. It applies to humans and AI agents. The agent version is in `10-ai-agent-rules.md`.

## 1. Branches

- **ENG-001** [LOCKED] Nobody commits or pushes to `main` directly. Every change goes through a pull request (PR). The only exception was the first commit that created this foundation (decision DEC-005).
- **ENG-002** [LOCKED] One issue, one branch, one PR.
- **ENG-003** [LOCKED] Start every task from an up-to-date `main`:

```bash
git switch main
git pull --ff-only
git switch -c feat/42-join-form
```

- **ENG-004** [LOCKED] Branch names are `<type>/<issue-number>-<short-slug>`. Types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`. Example: `fix/57-pin-lockout-count`.

## 2. Commits

- **ENG-010** [LOCKED] Commit messages follow Conventional Commits, in the imperative mood ("add", not "added"), and reference the issue. Cite rule IDs when the change implements a rule.

```
feat(auth): lock account after 5 wrong PINs (#57)

Implements SAFE-022. Counts wrong tries per player and sets locked_at.
```

- **ENG-011** [LOCKED] Keep commits small. Each commit should pass the tests on its own.
- **ENG-012** [LOCKED] Before every push: run the formatter, the linter, and the tests. Then check `git status` and `git diff --staged` for anything that must not be committed (SAFE-030). All must pass.
- **ENG-013** [LOCKED] Never run `git add -A` or `git add .` without first reading the list of files it will add. Prefer `git add <file>`.

## 3. Pull requests

- **ENG-020** [LOCKED] Open a draft PR early. Keep PRs small: aim for under 400 changed lines. Fill in the PR template fully: `Closes #N`, rule IDs, how to test, and screenshots at 360px wide for UI changes (fake data only, SAFE-036).
- **ENG-021** [LOCKED] Merging to `main` needs:
  - 1 approving review
  - a code owner review where CODEOWNERS applies
  - all conversations resolved
  - required checks passing (once CI exists, ENG-048)

  Approvals are dismissed when new commits are pushed. Merges are squash merges only, which keeps history linear.
- **ENG-022** [LOCKED] Nobody approves their own PR. AI agents never approve or merge any PR.
- **ENG-023** [LOCKED] A PR that touches sign-up, PIN or login, roles, admin controls, or minors' data gets the `safety-review` label and a second-person review before merge (SAFE-016).
- **ENG-024** [LOCKED] Stay current by rebasing your branch on `main`. After a rebase, `git push --force-with-lease` is allowed on your own branch only. Plain `git push --force` is never allowed.
- **ENG-025** [LOCKED] Resolve merge conflicts only in files your PR changed. If a conflict touches someone else's work or a protected path (ENG-080), stop and ask.
- **ENG-026** [LOCKED] Never use `--no-verify`. Never rewrite `main`'s history. Ask before `git reset --hard` or `git clean`. Never delete a branch you did not create.

## 4. Config and game numbers

- **ENG-030** [LOCKED] `foundation/game-config.yaml` is the only home for tunable numbers and flags. Keep its format simple: plain nested maps, numbers, strings, true or false, null, and flat lists. No anchors and no multi-line strings.
- **ENG-031** [LOCKED] Code reads game numbers from config (through `app/config.py`). Never hardcode one. Changing a game number is a one-line config change, made only by Jonathan.

## 5. Labels

- **ENG-040** [LOCKED] These labels are used on issues and PRs:

| Label | Meaning |
|---|---|
| `safety-review` | Needs a second-person safety review before merge (SAFE-016) |
| `foundation-change-request` | A proposed change to a protected file. Only Jonathan acts on it |
| `needs-decision` | Blocked on an OPEN decision (see `13-decisions.md`) |
| `blocked` | Cannot move for another reason. Say why in a comment |
| `good-first-issue` | Small, clear, good for a new contributor |
| `area:backend` | Server, services, auth, data |
| `area:player-app` | Player pages and the scanner |
| `area:admin-screens` | Usher, admin, and main screen pages |
| `area:design` | Look and feel, tokens, icons, copy |

- **ENG-041** [PROPOSED] Area labels map to folders (the layout is PROPOSED in ARCH-008):

| Area label | Folders |
|---|---|
| `area:backend` | `app/main.py`, `app/config.py`, `app/services/`, `app/auth/`, `app/models/`, `migrations/` |
| `area:player-app` | `app/routes/player/`, `app/templates/player/`, `app/templates/partials/`, `app/static/js/` |
| `area:admin-screens` | `app/routes/usher/`, `app/routes/admin/`, `app/routes/screen/`, `app/templates/usher/`, `app/templates/admin/`, `app/templates/screen/` |
| `area:design` | `app/static/css/`, `app/static/icons/` |

Tests in `tests/` follow the area of the code they test.

## 6. Testing and Definition of Done

- **ENG-045** [LOCKED] Definition of Done. A change is done only when all of these are true:
  - tests pass
  - rule IDs are cited in the PR and commits
  - the PR template is complete
  - every changed screen works at 360px wide
  - there are no browser console errors
  - no forbidden files (SAFE-030)
  - it is reviewed
  - safety review is done when it applies (ENG-023)
- **ENG-046** [LOCKED] Every implemented rule has tests, and test names include the rule ID, including the worked examples in `02-game-rules.md` section 12. Example: `test_game_013_same_pair_counts_once`.
- **ENG-047** [LOCKED] Test and seed data is obviously fake (SAFE-031).
- **ENG-048** [PROPOSED] CI runs on every PR. The required checks will be named `ci` and `foundation-guard`. CI is planned for the guardrails phase and does not exist yet.
- **ENG-049** [PROPOSED] Tests use pytest and lint uses ruff (ARCH-001).

## 7. Database migrations

- **ENG-050** [OPEN] Migrations are numbered plain SQL files, for example `migrations/0001_create_players.sql`. This is the PROPOSED default. Developers confirm the tool and format at kickoff (DATA-040).
- **ENG-051** [PROPOSED] Never edit a migration that is already merged. Add a new one.
- **ENG-052** [LOCKED] A migration that touches player, takeaway, or connection tables needs safety review (SAFE-016).

## 8. Environments, secrets, and dependencies

- **ENG-055** [PROPOSED] Three environments: local (your laptop, fake data), staging VM, production VM.
- **ENG-056** [LOCKED] Secrets come only from environment variables on the server (SAFE-032). The repo may hold a `.env.example` with placeholder values only. Never put a real value in it.
- **ENG-057** [LOCKED] A new dependency needs an issue that explicitly approves it (ARCH-002). Pin versions.
- **ENG-058** [PROPOSED] Dependabot opens PRs for GitHub Actions updates. The config file is planned for the guardrails phase.

## 9. Public repo

- **ENG-060** [LOCKED] Follow the public repo rules (SAFE-030 to SAFE-037) on every commit, issue, and PR comment.
- **ENG-061** [PROPOSED] CI fails if any tracked file matches a forbidden pattern: `.env` files (except `.env.example`), `*.db`, `*.sqlite*`, `*-wal`, `*-shm`, and anything in `data/`, `exports/`, or `backups/`. Planned for the guardrails phase.
- **ENG-062** [LOCKED] If you commit a secret or real data by mistake, follow SAFE-034: stop, tell Jonathan, rotate the secret, and do not rewrite history yourself.

## 10. Timeline rules

- **ENG-070** [LOCKED] After the feature complete gate (late January), nothing new is added. Only fixes and polish.
- **ENG-071** [LOCKED] Code freeze (late February): only bug fixes with an approved issue. Nothing new.
- **ENG-072** [LOCKED] Holiday break (December 21 to January 3): nothing critical is scheduled. Bonus work only.

## 11. Protected paths

- **ENG-080** [LOCKED] Only Jonathan changes these paths. Everyone else, human or agent, opens a Foundation Change Request issue:
  - `foundation/**`
  - root `README.md`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`
  - `.claude/**`
  - `.codex/**`
  - `.github/**`
  - `.gitignore`, `.editorconfig`, `.env.example`
- **ENG-081** [LOCKED] Protection has five layers. The status of each layer is in `15-repo-setup-checklist.md`.
  1. Agent instructions
  2. Claude Code deny rules
  3. A Claude Code hook
  4. CODEOWNERS and a CI guard
  5. GitHub repository settings

  No layer is perfect on its own. Code owner review on GitHub is the gate that counts.
