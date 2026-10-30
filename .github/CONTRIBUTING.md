# Contributing to Side Quest

- Status: Active
- Owner: Jonathan (@jonathango98)
- Version: 1.5.0
- Last updated: 2026-10-30

> Protected file. Changes go in a PR that Jonathan approves (ENG-080).

Welcome! This guide is for volunteers on the Side Quest team. You don't need to be an expert. You need to read the rules, work in small steps, and ask when unsure.

## 1. Before you start

1. Read [foundation/README.md](../foundation/README.md), then the docs listed for your role in its "Reading order" table.
2. Read [AGENTS.md](../AGENTS.md). Those rules apply to you too, not just to AI agents.
3. Skim [foundation/14-glossary.md](../foundation/14-glossary.md) so words like "My Code" and "check-in" mean the same thing to everyone.

## 2. Setup

The app does not exist yet. App setup steps (Python version, installing packages, running the server) will be added after kickoff (ARCH-003).

For now:

```bash
# Tools: git, the GitHub CLI (gh), and Python 3
gh auth login
gh repo clone jonathango98/nextgen27-sidequest
cd nextgen27-sidequest
```

Set your Git name and email if you haven't:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Tip: GitHub can give you a private "noreply" email so your real email is not in public commits. See GitHub's email settings.

## 3. Your first PR, step by step

Example: you want to add the join form.

1. **Call dibs.** If there's an issue for it, comment on it. Check the README Project status, `git branch -r`, and `gh pr list --state open` first. Every PR also adds a signed entry to `CHANGELOG.md` and keeps the README Project status accurate (ENG-100 to ENG-104).
2. **Start from an updated main:**

   ```bash
   git switch main
   git pull --ff-only
   git switch -c feat/join-form
   ```

3. **Read the rules for the task.** For a join form: SAFE-002 (exactly which fields), GAME-040 (join points), and the Join screen in `foundation/06-api-and-screens.md`.
4. **Make a small change.** Touch only the files the task needs.
5. **Check before you commit:**

   ```bash
   git status            # what changed?
   git add app/routes/player/join.py app/templates/player/join.html
   git diff --staged     # read every line you are about to commit
   ```

   Never commit `.env` files, `.db` files, or anything with real people's data.
6. **Run the checks before you commit** (ENG-012): the formatter, linter, and tests (commands added after kickoff). If you changed a page, ask Claude Code to run the browser check: type `/browser-check`, or say "run the browser check on the screens I changed". Everything must pass.
7. **Commit with a clear message.** Any style works. Your commits get squashed into one when the PR merges.

   ```bash
   git commit -m "add join form fields"
   ```
8. **Push and open a draft PR:**

   ```bash
   git push -u origin feat/join-form
   gh pr create --draft --fill
   ```

9. **Fill in the short PR template:** what and why (with rule IDs) and how to test. Give the PR a title like `feat(player): add join form`.
10. **Try it by hand, then mark it ready for review.** Open the PR's preview link and run every step under How to test (your piece's `try_it` steps), on a real phone for player pages. Tick each step as it passes (ENG-112). Someone else reviews and merges. You never merge your own PR.
11. **If `main` moved on,** rebase and push safely:

    ```bash
    git fetch origin
    git rebase origin/main
    git push --force-with-lease
    ```

## 4. Working with Claude Code or Codex

AI agents read `AGENTS.md` automatically (Claude Code through `.claude/CLAUDE.md`). Good prompts name the issue, the rules, and the limits. Ask the agent to plan first and explain what it did.

**Example 1: a feature**

```
Work on issue #42 (join form). Read AGENTS.md, foundation/03-safety-privacy.md
(SAFE-002) and the Join screen in foundation/06-api-and-screens.md first.
Show me a short plan with rule IDs before editing. Only touch files under
app/routes/player/ and app/templates/player/. Explain each command you run.
```

**Example 2: a bug**

```
Issue #57: a player's PIN locks after 4 wrong tries instead of 5. Find the
cause, then write a failing test named after SAFE-022 before fixing it.
Read the limit from game-config.yaml, don't hardcode it. Stop and ask
before changing anything in app/auth/ beyond the fix.
```

**Example 3: learning**

```
Explain how the points service should check pause state (ARCH-040,
GAME-102) as if I'm new to FastAPI. Don't change any files. Then suggest
3 test cases with names that include the rule IDs.
```

If the agent says a file is protected, that's expected. It can still change it in a PR if you ask, but Jonathan has to approve that PR.

## 5. How to ask for help

- **Stuck on code:** comment on your issue or PR with what you tried and the exact error. Tag a teammate or @jonathango98.
- **The rules are unclear or OPEN:** add the `needs-decision` label to the issue and say what is unclear. Don't guess.
- **You think a rule should change:** open a PR with the change and say why. Jonathan reviews it.
- **Something might be a security or safety problem:** don't post it publicly. See [SECURITY.md](SECURITY.md).
- **Not sure what to work on:** type `/pick-task` in Claude Code. It shows 3 free tasks that fit you and calls dibs on the one you pick.

There are no silly questions. Asking early saves everyone time.

## 6. This repo is public

Anyone on the internet can read everything here: files, issues, PRs, comments, and the full history. In plain words:

- **Never commit secrets.** No passwords, keys, or `.env` files. Secrets live only on the server.
- **Never commit real people's data.** No names, churches, ages, PINs, answers, or takeaways from real attendees. No playtest data.
- **Never commit database files** (`.db`, `.sqlite`, files ending in `-wal` or `-shm`), backups, exports, or logs.
- **Never post where hidden items are**, or the item list.
- **Use fake data everywhere:** "Test Player 1", "Example Church A". Same for screenshots.
- **If you commit something by mistake,** stop and tell Jonathan right away. Don't try to fix the history yourself. A secret has to be changed (rotated), because deleting a commit does not un-publish it.
