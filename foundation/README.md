# Side Quest Foundation

- Status: Active
- Owner: Jonathan (@jonathango98)
- Version: 1.1.1
- Last updated: 2026-10-23

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

This folder is the single source of truth for Side Quest: the product, the game rules, safety, architecture, design, and how we work. If code and the foundation disagree, the foundation wins until a Foundation Change Request changes it.

## 1. Files

| File | What it covers | Rule prefix |
|---|---|---|
| [01-product.md](01-product.md) | What Side Quest is, goals, metrics, the three days, non-goals | PRD |
| [02-game-rules.md](02-game-rules.md) | Every quest, point value, limit, sticker milestone, leaderboard, pause rule, worked examples | GAME |
| [03-safety-privacy.md](03-safety-privacy.md) | Minors, who sees what, moderation, retention, second-person review, public repo rules | SAFE |
| [04-architecture.md](04-architecture.md) | Stack, one-repo decision, app layout, QR format, login, roles, performance, threat model | ARCH |
| [05-data-model.md](05-data-model.md) | Tables, fields, and database constraints | DATA |
| [06-api-and-screens.md](06-api-and-screens.md) | Routes, HTMX conventions, error codes, screen list | API |
| [07-design-system.md](07-design-system.md) | Tokens, components, phone and main screen rules, copy voice, accessibility | UI |
| [08-wrapped.md](08-wrapped.md) | Side Quest Wrapped | WRAP |
| [09-engineering-workflow.md](09-engineering-workflow.md) | Git, GitHub, PRs, labels, testing, Definition of Done, migrations, freeze | ENG |
| [10-ai-agent-rules.md](10-ai-agent-rules.md) | Full rules for AI coding agents | AI |
| [11-operations-runbook.md](11-operations-runbook.md) | Game day tasks, failure playbook, checklists, where real data lives | OPS |
| [12-team-timeline.md](12-team-timeline.md) | Roles, folder ownership, milestones, gates | PRD |
| [13-decisions.md](13-decisions.md) | Decision log, resolved conflicts, every OPEN item | DEC |
| [14-glossary.md](14-glossary.md) | Every term | |
| [15-repo-setup-checklist.md](15-repo-setup-checklist.md) | GitHub settings for the repo owner, protection layers | ENG |
| [game-config.yaml](game-config.yaml) | Every tunable number and flag (the canonical values) | |

## 2. Reading order by role

Everyone reads this file, then `AGENTS.md` (or `.github/CONTRIBUTING.md` for humans), then `14-glossary.md`.

| Role | Read these, in order |
|---|---|
| Backend developer | 02, 03, 04, 05, 06, `game-config.yaml`, 09 |
| Player app developer | 02, 03, 06, 07, 08, 09 |
| Admin and screens developer | 02, 03, 06, 07, 11, 09 |
| Designer | 01, 07, 06 (screen list), 08, 03 (who sees what) |
| Game director | 01, 02, `game-config.yaml`, 13, 11, 08 |

## 3. Source precedence

When sources disagree, the higher one wins:

1. Jonathan's answers in the foundation setup session (2026-10-19)
2. Resolved conflicts in `13-decisions.md`
3. Blueprint (last updated 2026-10-19)
4. Leadership deck speaker notes
5. Project brief

If it is still unclear, the item is marked OPEN. Nobody invents numbers, names, dates, or rules.

## 4. Rule IDs

- Every rule has an ID: a prefix, a dash, and three digits. Example: `GAME-013`.
- Prefixes: PRD (product), GAME (game rules), SAFE (safety and privacy), ARCH (architecture), DATA (data model), API (routes), UI (design), WRAP (Wrapped), ENG (engineering), AI (agent rules), OPS (operations). Decisions use DEC.
- IDs are never reused or renumbered. A removed rule keeps its ID, marked as removed.
- Gaps in numbering are on purpose. They leave room to add rules next to related ones.
- A rule is defined once, in bold: `**GAME-013** [LOCKED] ...`. Everywhere else it is mentioned in plain text: `GAME-013`.
- Issues, PRs, code comments, and test names cite rule IDs. Example test name: `test_game_013_same_pair_counts_once`.

## 5. Status words

| Status | Meaning | What to do |
|---|---|---|
| LOCKED | Decided | Build it as written |
| PROPOSED | The current default. May change after a playtest or at kickoff | Build against it. Read any number from `game-config.yaml`, so a change is one line |
| OPEN | Not decided | Do not build behavior that depends on it. Use the config placeholder (null) and leave its feature flag off. Ask if you are blocked |

Each file also has a status at the top. A file marked "Active" mixes statuses. Read the status on each rule.

## 6. How the foundation changes

- **ENG-085** [LOCKED] Anyone may propose a change to the foundation or another protected path in a PR. It merges only with Jonathan's approval (ENG-080).
- **ENG-086** [REMOVED] Was: propose a change through a Foundation Change Request issue first. A PR is enough now (DEC-025).
- **ENG-087** [LOCKED] A PR that changes a protected file raises the file's version (patch for wording, minor for a changed rule, major for a changed structure), updates "Last updated", and logs a decision in `13-decisions.md` if a rule changed.
- **ENG-088** [LOCKED] An OPEN item becomes LOCKED or PROPOSED only through a decision in `13-decisions.md`.
