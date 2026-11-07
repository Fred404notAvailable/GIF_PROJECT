---
name: worktrees
description: Git worktree lifecycle for isolated per-ticket workstreams. Load this skill whenever the user describes a problem to solve or asks to claim a ticket, before any implementation work begins.
license: MIT
compatibility: opencode
---

## When to use this skill

Load this skill whenever:

- The user describes a problem or feature to implement
- The user asks to pick up or claim a ticket
- The user brings review feedback for an existing PR

Do not use this skill if the user explicitly asks to work in the current directory.

## Step 0 — Ensure a git repository exists

Before doing anything else, check whether the project is a git repository:

```bash
git -C . rev-parse --is-inside-work-tree
```

If this command fails or returns false, initialise one:

```bash
git init
```

All subsequent steps depend on git being present.

## Step 1 — Derive the worktree path

**Project name**: the last path component of the current working directory.

> cwd `/home/user/dev/myapp` → project = `myapp`

**Slug**:

- With a ticket number: `{number}-{slugified-title}` — e.g. `42-add-user-auth`
- Without a ticket: slugify the problem description into a short kebab-case phrase — e.g. `fix-login-redirect`

Slugification: lowercase, spaces and special characters become hyphens, max ~40 characters, trim trailing hyphens.

**Worktree path**: `~/worktrees/{project}/{slug}`

**Branch name**: `feature/{slug}`

## Step 1b — Rename the session

Once the slug is known (and the ticket number, if applicable), call `rename-session` with the appropriate title:

- With a Gitea or GitHub ticket: `Issue #N - {slug}` — e.g. `Issue #42 - add-user-auth`
- With a Jira ticket: `PROJ-N - {slug}` — e.g. `PROJ-42 - add-user-auth`
- Without a ticket: `{slug}` — e.g. `fix-login-redirect`

Call this once and do not repeat it. If `rename-session` returns an error, log it and continue — session naming is not a blocker.

## Step 1c — Derive the agent-logs path

Compute the agent-logs folder for this session:

```
agent-logs/YYYY-MM-DD-{slug}/
```

Use today's date in `YYYY-MM-DD` format. For example: `agent-logs/2026-03-05-42-add-user-auth/`.

This path is **relative to the worktree root**. Full absolute path: `~/worktrees/{project}/{slug}/agent-logs/YYYY-MM-DD-{slug}/`.

Hold this path — you will pass it to `@frontend-engineer` and use it when writing the task log.

## Step 2 — Create or re-enter the worktree

First, check whether a worktree for this branch already exists:

```bash
git worktree list
```

**If the worktree already exists** at `~/worktrees/{project}/{slug}` (e.g. returning for review feedback):

- Skip to [Passing the path to subagents](#passing-the-path-to-subagents) — the worktree and branch are ready to use as-is
- Do not re-copy `.env` or re-install dependencies unless the user indicates time has passed and they may be stale

**If the worktree does not exist but the branch does** (worktree was manually removed):

```bash
mkdir -p ~/worktrees/{project}
git worktree add ~/worktrees/{project}/{slug} feature/{slug}
```

Then copy `.env` and install dependencies (steps 3–4).

**If neither the worktree nor the branch exists** (fresh start):

```bash
mkdir -p ~/worktrees/{project}
git worktree add ~/worktrees/{project}/{slug} -b feature/{slug}
```

Then copy `.env` and install dependencies (steps 3–4).

If `git worktree add` fails for any other reason, report to the user and stop.

## Step 3 — Copy environment files

```bash
cp .env ~/worktrees/{project}/{slug}/.env
```

Skip silently if `.env` does not exist. Copy any additional non-tracked env files (`.env.local`, `.env.test`) if present.

`agent-config.json` does not need to be copied — it is a tracked file present in the worktree automatically.

## Step 4 — Install dependencies

Delegate to `@backend-engineer` before any implementation begins:

> "Before starting work, run the project's dependency install command (e.g. `pnpm install`, `npm install`, `bun install`) from `{worktree_path}`. Confirm once done."

## Passing the path to subagents

Every Task invocation for the duration of this session **must** include the worktree path:

> "Your working directory for this task is `{worktree_path}`. All file reads, writes, edits, and bash commands must operate relative to this path. Do not operate on files outside this directory."

This applies without exception to: `@backend-engineer`, `@frontend-engineer`, `@devops-engineer`, `@qa`, `@developer-advocate`, `@code-reviewer`, `@security-reviewer`, `@observability-reviewer`, `@logger`.

When invoking `@frontend-engineer`, also include the agent-logs path:

> "Save all screenshots to `{agent_logs_path}` (create the folder if it does not exist). Report back the filenames of any screenshots you save."

## Handling review feedback

When the user brings back review feedback from a PR:

1. Re-enter the existing worktree (Step 2 — "already exists" path). Do not create a new one.
2. Pass the worktree path to the relevant engineer(s) along with the review comments.
3. After changes are made and quality gates pass, push again:
   ```bash
   git push origin feature/{slug}
   ```
   This updates the existing PR automatically — no new PR is needed.
4. Post a comment on the issue noting the updated push (if a ticket is open).
5. Leave the worktree in place for any further rounds of feedback.

## On completion: write the log, push, and open PR

After all quality gates pass — reviewers, QA, devops-engineer (if applicable), and developer-advocate — follow these steps **in order** before invoking `@logger`.

### 1. Collect the task context

Gather from all agent reports:

- Task name and ticket number/key (if any)
- What was done (prose summary, 2–4 sentences)
- Architect's recommendation (if architect was invoked) and what was kept, modified, or rejected
- Files changed (path + one-line description each)
- Tests added
- Reviewer verdicts (code-reviewer, security-reviewer, observability-reviewer — full JSON)
- QA verdict (if applicable)
- Devops-engineer report (if applicable)
- Developer-advocate update list
- Screenshot filenames as reported by `@frontend-engineer` (relative to the agent-logs folder)
- Any follow-up items with reasoning
- Any tradeoffs made during implementation (what was chosen and why)
- Any errors or complications encountered and how they were resolved
- Any engineer notes on uncertainty or tech debt

### 2. Determine the base branch

```bash
git symbolic-ref refs/remotes/origin/HEAD
```

Strip `refs/remotes/origin/` to get the branch name (usually `main` or `develop`). Default to `main` if this fails.

### 3. Write the task log

Create `{agent_logs_path}/log.md` in the worktree. This is the detailed record for agents, reviewers, and future analysis — not the PR itself. Include everything:

```markdown
# Task log: {task title}

**Date:** YYYY-MM-DD
**Ticket:** {ticket reference, or "None"}
**Branch:** feature/{slug}
**PR:** {pr_url — fill in after PR is opened; leave blank until then}

## Implementation plan

{If architect was invoked: what was recommended. What was accepted as-is, what was
modified, what was rejected, and why. If no architect: note that the task was
implemented directly.}

## Tradeoffs and decisions

{Each significant choice made during implementation. Format: what was chosen, what
alternatives were considered, why this approach was taken. If no notable tradeoffs,
write "No significant tradeoffs — implementation followed the plan directly."}

## Changes

| File | Description |
|------|-------------|
| `path/to/file.ts` | What changed |

## Tests added

- `path/to/test.ts` — what it covers

## Quality gate verdicts

### code-reviewer

{full JSON verdict}

### security-reviewer

{full JSON verdict}

### observability-reviewer

{full JSON verdict}

### QA

{full JSON verdict, or "Not applicable — no endpoint or UI changes"}

### devops-engineer

{summary, or "Not applicable — no new services or infrastructure changes"}

## Errors and complications

{Any unexpected errors, surprising behaviour, or complications during implementation.
For each: what happened, what was tried, how it was resolved. If none: "None."}

## Screenshots

{If screenshots exist, embed each one:}
![description](log-folder-name/screenshot-filename.png)

{Where log-folder-name is the last path component of agent_logs_path, e.g.
2026-03-05-42-add-user-auth. Use relative paths from the worktree root.}

## Documentation updates

{List of files updated by developer-advocate, or "None"}

## Follow-up items

{Each deferred item: what it is, why it was deferred, recommended approach. Or "None."}

## Agent notes

{Anything flagged by the engineer as uncertain, potentially brittle, or worth
revisiting. Confidence levels on non-obvious decisions. Or "None."}
```

### 4. Commit and push the feature branch

Stage and commit all changes in the worktree, including the agent-logs folder:

```bash
git -C ~/worktrees/{project}/{slug} add -A
git -C ~/worktrees/{project}/{slug} commit -m "{concise imperative summary of the work done}"
```

If there is nothing to commit (working tree clean), skip the commit and proceed to push. Then push:

```bash
git push origin feature/{slug}
```

Do not open the PR until the push succeeds.

### 5. Compose the PR body

The PR body is a clean, human-readable summary. Reviewers and team members read the PR — keep it clear and concise. Full detail lives in `log.md`.

Use this template:

```markdown
## Summary

{2–4 sentence prose description of what was done and why. No jargon.}

## Changes

| File | Description |
|------|-------------|
| `path/to/file.ts` | What changed |

## Tests added

- `path/to/test.ts` — what it covers

## Quality gates

| Gate | Result |
|------|--------|
| code-reviewer | ✅ pass |
| security-reviewer | ✅ pass |
| observability-reviewer | ✅ pass |
| QA | ✅ pass |
| devops-engineer | ✅ pass |

_Omit rows that were not applicable to this task._

## Screenshots

{If screenshots exist, embed each one using a relative path from the repo root:}
![description](agent-logs/YYYY-MM-DD-{slug}/screenshot-filename.png)

{"None" if no UI changes}

## Follow-up items

{Brief bulleted list, or "None"}

---

Full task log: [agent-logs/YYYY-MM-DD-{slug}/log.md](agent-logs/YYYY-MM-DD-{slug}/log.md)

{If a ticket exists: "Refs #N" (Gitea/GitHub) or "Refs PROJ-N" (Jira)}
```

### 6. Open the PR

Call the PR tool appropriate for the active git host provider (from `agent-config.json → git_host.provider`):

- **Gitea**: `gitea-create-pr`
- **GitHub**: `github-create-pr`

Parameters:

- `head`: `feature/{slug}`
- `base`: base branch from step 2
- `title`: ticket title, or a concise imperative summary (e.g. "Fix completed_at column default")
- `body`: the composed PR body from step 5

Once the PR URL is returned, go back and fill it into the `**PR:**` field in `log.md`, then commit the update:

```bash
git -C ~/worktrees/{project}/{slug} add agent-logs/
git -C ~/worktrees/{project}/{slug} commit -m "Add PR URL to task log"
git push origin feature/{slug}
```

### 7. Post the PR URL on the ticket

Post a comment on the issue using the active issue tracker provider:

- **Gitea**: `gitea-add-comment`
- **GitHub**: `github-add-comment`
- **Jira**: `jira-link-pr` (posts the PR as a linked item on the ticket)

Comment text for Gitea/GitHub:

```
🔀 PR opened: {pr_url}
```

### 8. Invoke logger

Pass to `@logger`:
- The PR URL
- A one-sentence summary of what was done

### 9. Leave the worktree in place

Report the PR URL to the user. The worktree stays available for review feedback rounds.

## Explicit cleanup

Only remove the worktree when the user confirms the work is done (PR merged, abandoned, or explicitly dismissed):

```bash
git worktree remove ~/worktrees/{project}/{slug}
```

If removal fails due to untracked or modified files, report this rather than force-removing. Leave cleanup to the user.

## Error handling

- Worktree creation failure → report and stop; do not proceed without an isolated workspace
- `.env` copy failure → report and continue; not a blocker
- Dependency install failure → report and ask whether to continue or abort
- `git commit` failure → report; do not push or open PR until resolved
- `git push` failure → report; do not open PR until push succeeds
- PR creation failure → report the error with the branch name so the user can open it manually
- Worktree removal failure → report and leave it; never force-remove
- `agent-logs` folder creation failure → report and continue; log writing is important but not a blocker on the PR
