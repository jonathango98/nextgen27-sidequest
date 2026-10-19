# CLAUDE.md

- Status: LOCKED
- Owner: Jonathan (@jonathango98)
- Version: 1.0.0
- Last updated: 2026-10-19

> Protected file. AI agents: read only. To propose a change, open a Foundation Change Request issue.

@AGENTS.md
@foundation/README.md

## Claude Code notes

- The rules above apply in full. This section adds only Claude-specific notes.
- Read the foundation docs your task needs with the Read tool before planning. Do not load every doc at once.
- For any task with more than one step, show a short plan with rule IDs before editing files.
- Protected paths will be guarded by deny rules and a hook (planned, see `foundation/15-repo-setup-checklist.md`). If a tool call is blocked, do not retry with another tool or a shell command. Draft a Foundation Change Request instead (AI-060).
- Do not change `.claude/` settings or hooks, and do not create `.claude/settings.local.json` entries that loosen permissions or turn hooks off (AI-022).
