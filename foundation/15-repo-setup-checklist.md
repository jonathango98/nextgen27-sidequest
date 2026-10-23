# 15 Repo Setup Checklist

- Status: Active (manual steps for Jonathan; not yet applied)
- Owner: Jonathan (@jonathango98)
- Version: 1.1.0
- Last updated: 2026-10-23

> Protected file. AI agents: read only. To propose a change, open a Foundation Change Request issue.

This file is for Jonathan, the repo owner. It lists the GitHub settings to apply by hand, the `gh` commands to apply them, and the honest limits of each protection layer. Only Jonathan can apply these. Collaborators cannot change repo settings.

Repo: `jonathango98/nextgen27-sidequest`. Public, on a personal account, GitHub Free plan.

Commands marked "verify" use API details that were not confirmed in the docs during setup. Run them, then read the setting back to check.

## 1. Protection layers and their status

The guardrails stay light on purpose (DEC-024). Volunteers should feel free to try things with AI on their own branch. Nothing on a branch can hurt `main`, because `main` only changes through a reviewed PR. There are no local blocks on anyone's laptop.

| Layer | What it does | Status | Limits |
|---|---|---|---|
| 1. Instructions | `AGENTS.md`, `CLAUDE.md`, and `10-ai-agent-rules.md` tell agents that protected paths are read only | Written | Agents can ignore instructions. Humans can ignore them too |
| 2. CODEOWNERS | Code owner review on protected paths | Planned (guardrails phase) | Only works with the ruleset in layer 3 |
| 3. Repo settings | Ruleset on `main`, Actions settings, security features | Not applied (this file) | The settings depend on GitHub features working as documented. Test them (section 4) |

- **ENG-090** [REMOVED] Was: how Jonathan edits protected files past the Claude Code deny rules. The deny rules were dropped (DEC-024), so nothing blocks him.

## 2. Owner bypass

- **ENG-091** [REMOVED] Was: an env var that let Jonathan pass the Claude Code hook. The hook was dropped (DEC-024).

## 3. Steps

### Step 1. Push the first commit

The foundation is the first commit on `main`, with no PR (DEC-005). Push it before turning on the ruleset.

```bash
git push -u origin main
```

### Step 2. Merge settings

Squash merge only, delete branches after merge, wiki off.

```bash
gh repo edit jonathango98/nextgen27-sidequest \
  --enable-squash-merge \
  --enable-merge-commit=false \
  --enable-rebase-merge=false \
  --delete-branch-on-merge \
  --enable-wiki=false
```

### Step 3. Actions settings

Default `GITHUB_TOKEN` permission read-only, and Actions cannot approve PRs:

```bash
gh api -X PUT repos/jonathango98/nextgen27-sidequest/actions/permissions/workflow \
  -f default_workflow_permissions=read \
  -F can_approve_pull_request_reviews=false
```

Require approval before workflows run on PRs from all outside contributors' forks:

```bash
gh api -X PUT repos/jonathango98/nextgen27-sidequest/actions/permissions/fork-pr-contributor-approval \
  -f approval_policy=all_external_contributors
```

In the UI: Settings, Actions, General, "Approval for running fork pull request workflows from contributors", "Require approval for all external contributors".

### Step 4. Security features

Secret scanning and push protection (public repos get these free). Verify in Settings, Advanced Security afterwards:

```bash
gh api -X PATCH repos/jonathango98/nextgen27-sidequest --input - <<'EOF'
{"security_and_analysis": {
  "secret_scanning": {"status": "enabled"},
  "secret_scanning_push_protection": {"status": "enabled"}
}}
EOF
```

Dependabot alerts, Dependabot security updates, and private vulnerability reporting:

```bash
gh api -X PUT repos/jonathango98/nextgen27-sidequest/vulnerability-alerts
gh api -X PUT repos/jonathango98/nextgen27-sidequest/automated-security-fixes
gh api -X PUT repos/jonathango98/nextgen27-sidequest/private-vulnerability-reporting
```

### Step 5. Labels (ENG-040)

```bash
R=jonathango98/nextgen27-sidequest
gh label create safety-review --repo $R --color B42318 --description "Needs second-person safety review (SAFE-016)"
gh label create foundation-change-request --repo $R --color 5319E7 --description "Proposed change to a protected file"
gh label create needs-decision --repo $R --color FBCA04 --description "Blocked on an OPEN decision"
gh label create blocked --repo $R --color 000000 --description "Cannot move, see comment"
gh label create good-first-issue --repo $R --color 7057FF --description "Small and clear, good for a new contributor"
gh label create area:backend --repo $R --color 1F4FD1 --description "Server, services, auth, data"
gh label create area:player-app --repo $R --color 0E8A16 --description "Player pages and scanner"
gh label create area:admin-screens --repo $R --color D93F0B --description "Usher, admin, main screen"
gh label create area:design --repo $R --color F2C14E --description "Look, tokens, icons, copy"
```

### Step 6. Ruleset on `main`

Create it in the UI first, because the ID for the "Repository admin" role is not confirmed in the docs: Settings, Rules, Rulesets, New branch ruleset.

| Setting | Value |
|---|---|
| Name | `main-protection` |
| Enforcement | Active |
| Target | Default branch |
| Bypass list | Repository admin, mode "For pull requests only" |
| Restrict deletions | On |
| Block force pushes | On |
| Require linear history | On |
| Require a pull request before merging | On, 1 approval, dismiss stale approvals, require review from Code Owners, require conversation resolution, allowed merge method: squash |
| Require status checks to pass | Add `ci` after that workflow exists and has run once |

Then read it back to see the IDs GitHub used:

```bash
gh api repos/jonathango98/nextgen27-sidequest/rulesets
gh api repos/jonathango98/nextgen27-sidequest/rulesets/<id>
```

The same ruleset as an API call (verify `actor_id` against the read-back first):

```bash
gh api -X POST repos/jonathango98/nextgen27-sidequest/rulesets --input - <<'EOF'
{
  "name": "main-protection",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  "bypass_actors": [
    {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}
  ],
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "required_linear_history"},
    {"type": "pull_request", "parameters": {
      "required_approving_review_count": 1,
      "dismiss_stale_reviews_on_push": true,
      "require_code_owner_review": true,
      "require_last_push_approval": false,
      "required_review_thread_resolution": true,
      "allowed_merge_methods": ["squash"]
    }}
  ]
}
EOF
```

Why the bypass: nobody can approve their own PR, and Jonathan is the only code owner for protected paths. Without a bypass, Jonathan's own foundation PRs could never merge. "For pull requests only" means Jonathan still has to open a PR (no direct pushes) but can merge it without a second approval.

### Step 7. Collaborators

Invite each developer in Settings, Collaborators. On a personal-account repo, every collaborator gets the same access: they can push branches, open and merge PRs, and manage issues and labels, but cannot change settings or rulesets. The ruleset (step 6) is what stops them from changing `main` without review.

If the repo later moves to an organization, give developers the Write role. Never Admin or Maintain.

### Step 8. Optional: interaction limits

If strangers spam issues or PRs, limit interactions to collaborators for up to 6 months:

```bash
gh api -X PUT repos/jonathango98/nextgen27-sidequest/interaction-limits \
  -f limit=collaborators_only -f expiry=six_months
```

### Step 9. Safety reviewer

When a safety reviewer is named, invite them as a collaborator, then replace the commented `SAFETY_REVIEWER` placeholder in CODEOWNERS (guardrails phase) with their GitHub handle.

## 4. Test the protections

Do these after steps 1 to 6.

- [ ] From a collaborator's account, try `git push origin main`. It must be refused.
- [ ] From a collaborator's account, open a PR that edits `foundation/README.md`. It must require Jonathan's review.
- [ ] Open your own small PR to a protected path. Check that you can merge it without a second approval, and that a direct push to `main` is still refused.
- [ ] Settings, Advanced Security shows secret scanning and push protection as on.
- [ ] A test PR from a fork waits for your approval before its workflows run (once workflows exist).

## 5. Docs used during setup (2026-10-19)

| Topic | URL |
|---|---|
| Claude Code permissions | https://code.claude.com/docs/en/permissions |
| Claude Code hooks | https://code.claude.com/docs/en/hooks |
| Claude Code memory and imports | https://code.claude.com/docs/en/memory |
| Claude Code CLI flags | https://code.claude.com/docs/en/cli-reference |
| Codex AGENTS.md | https://developers.openai.com/codex/guides/agents-md (now redirects to learn.chatgpt.com) |
| Codex config and rules | https://learn.chatgpt.com/docs/config-file/config-reference, https://learn.chatgpt.com/docs/agent-configuration/rules |
| CODEOWNERS | https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners |
| Rulesets | https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets |
| Rulesets REST API | https://docs.github.com/en/rest/repos/rules |
| Actions permissions REST API | https://docs.github.com/en/rest/actions/permissions |
| Workflow events and forks | https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows |
| Personal repo permission levels | https://docs.github.com/en/account-and-profile/reference/permission-levels-for-a-personal-account-repository |
| Interaction limits REST API | https://docs.github.com/en/rest/interactions/repos |
