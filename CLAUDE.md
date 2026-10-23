# CLAUDE.md

- Status: LOCKED
- Owner: Jonathan (@jonathango98)
- Version: 1.0.1
- Last updated: 2026-10-23

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

@AGENTS.md
@foundation/README.md

## Claude Code notes

- The rules above apply in full. This section adds only Claude-specific notes.
- Read the foundation docs your task needs with the Read tool before planning. Do not load every doc at once.
- For any task with more than one step, show a short plan with rule IDs before editing files.
- Protected paths are guarded by code owner review on GitHub, not by local blocks (DEC-024). If a tool call is blocked, do not retry with another tool or a shell command. Tell the human what was blocked (AI-060).
- Do not change `.claude/` settings or hooks, and do not create `.claude/settings.local.json` entries that loosen permissions or turn hooks off (AI-022).
