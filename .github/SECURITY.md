# Security Policy

- Status: Active
- Owner: Jonathan (@jonathango98)
- Version: 1.1.0
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

This repo is public. The full list of what never goes in it, in issues, or in PR comments is in [Public repo rules](../foundation/03-safety-privacy.md#8-public-repo-rules) (SAFE-030 to SAFE-037).

If a secret or real data was committed by mistake: stop, tell Jonathan (@jonathango98) privately right away, and rotate the secret. Do not rewrite git history yourself (SAFE-034).

## How security works here

Side Quest assumes attackers can read all of its source code. Security depends only on server-side secrets, server-side checks, and authenticated roles. See the threat model in [foundation/04-architecture.md](../foundation/04-architecture.md).
