# Security Policy

- Status: Active
- Owner: Jonathan (@jonathango98)
- Version: 1.0.1
- Last updated: 2026-10-23

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

Side Quest is used by youth leaders, some of whom are under 18. We take security and privacy reports seriously.

## Reporting a vulnerability

Please report privately. Do not open a public issue, PR, or discussion.

1. Go to this repo's **Security** tab.
2. Click **Report a vulnerability** (GitHub private vulnerability reporting).
3. Describe what you found, how to reproduce it, and what could happen. Use fake data in your report.

Only the repo owner sees private reports. You will get a reply as soon as the owner can.

Please do not test against the live event server, and never access, change, or download other people's data.

## What never goes in this repo

This repo is public. These never belong in it, in issues, or in PR comments (SAFE-030):

- secrets, API keys, `.env` files, QR or TOTP signing keys, session keys, admin passwords, admin URLs with tokens
- SQLite database files, including `-wal` and `-shm` files
- backups, exports, logs
- real attendee data of any kind: names, churches, under-18 answers, PINs, icebreaker answers, takeaways
- playtest data, and screenshots or photos showing real people
- hidden item locations or the hidden item list
- volunteer contact details

## If a secret or real data was committed by mistake

1. **Stop.** Don't push more commits about it.
2. **Tell Jonathan immediately** (@jonathango98), privately.
3. **Rotate the secret.** Treat any committed secret as already stolen. Deleting the commit does not make it safe. Jonathan or the developer on call replaces it on the server.
4. **Do not try to rewrite git history yourself.** History rewrites on a shared repo can break everyone's work and do not remove copies others already have. Jonathan decides what cleanup is needed.

## How security works here

Side Quest assumes attackers can read all of its source code. Security depends only on server-side secrets, server-side checks, and authenticated roles. See the threat model in [foundation/04-architecture.md](foundation/04-architecture.md).
