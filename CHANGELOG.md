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

## 2026-10-23 · chore/7-repo-guardrails · Claude Opus 5.5 / @jonathango98

- What: Claimed the repo guardrails task: deny rules, hook, Codex rules, CODEOWNERS, CI guard, and repo settings.
- Why: Issue #7. Protected paths need guards before app code starts.
- Rule IDs: ENG-090, ENG-091, ENG-101, DEC-018, AI-060
- Status: Started
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
