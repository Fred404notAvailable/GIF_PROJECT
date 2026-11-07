---
name: github-issues
description: GitHub issue lifecycle for the build agent. Load this skill when the issue tracker provider is "github" in agent-config.json. Covers session start, progress tracking, and PR linking.
license: MIT
compatibility: opencode
---

## When to use this skill

Load this skill at the start of any session when `agent-config.json` has `issue_tracker.provider = "github"`. It covers the full issue lifecycle from picking up a ticket to linking the final PR.

Do not load this skill alongside `gitea-issues` or `jira` — use one based on the configured provider.

## Configuration check

Before using any GitHub tool, verify configuration is present. Call `github-get-issue` with any known issue number. If it returns an error message referencing `agent-config.json`, stop and show the user that message — do not proceed until GitHub is configured.

## Session start

When the user provides an issue number or asks to claim a GitHub issue:

1. **Load this skill** (already done if you're reading this)
2. **Read the issue** with `github-get-issue`. Use the issue body as the authoritative spec. If the user's verbal summary conflicts with the issue body, surface the discrepancy and ask for clarification before proceeding.
3. **Read comments** — they are returned by `github-get-issue` in the `## Comments` section. Comments take precedence over the body when they conflict (they are more recent). Pay attention to any blocking conditions or clarifications.
4. **Post an opening comment** with `github-add-comment`:

```
🤖 Starting work on this issue.

Spec understood: {one-sentence summary of what will be done}

Branch: feature/{slug}
Worktree: ~/worktrees/{project}/{slug}
```

Note: GitHub has no native "In Progress" status transition — issue state is simply open or closed. Use labels (e.g. "in progress") if the repository uses label-based workflows. Do not change state until the user asks.

## Issue number format

GitHub issues use plain numbers (`#42`). For session naming (via `rename-session`), use: `Issue #N - {slug}` — e.g. `Issue #42 - add-user-auth`.

## Reading comments

`github-get-issue` returns all comments in the `## Comments` section of its output. Each comment shows:

```
@username (YYYY-MM-DD): comment text
```

Comments are shown oldest-first. Focus on the most recent ones — they reflect current intent. Look for:

- Blocking conditions (don't start work if a blocker is noted)
- Clarifications that override the description
- Prior attempts at the same work (avoid duplicate effort)

## Progress updates

Post progress comments at key milestones using `github-add-comment`:

- When a significant sub-task is complete
- When a blocker is encountered: describe what is blocked and why
- When unblocked: note what resolved it

Keep comments brief. The PR body is the detailed log; issue comments are status signals.

## Linking a PR

When the PR is opened, call `github-add-comment`:

```
🔀 PR opened: [{pr_title}]({pr_url})
```

GitHub also automatically cross-references the issue if the PR body contains `Closes #N` or `Refs #N` — the worktrees skill PR template already includes this.

## On completion

When the PR is opened, post a final comment:

```
✅ Complete. All quality gates passed.

PR: {pr_url}
Task log: agent-logs/YYYY-MM-DD-{slug}/log.md
```

**Do not close the issue.** The user or the team manages issue state — closing is not the agent's responsibility.

## Screenshots

Screenshots are committed to the feature branch in the `agent-logs/YYYY-MM-DD-{slug}/` folder (managed by the `worktrees` skill). The PR body embeds them using relative paths:

```markdown
![description](agent-logs/YYYY-MM-DD-slug/filename.png)
```

GitHub renders these inline in the PR. No external upload is needed.

## Tool reference

| Tool | Purpose |
|---|---|
| `github-get-issue` | Read issue details + comments |
| `github-list-issues` | List issues by state |
| `github-create-issue` | Create a new issue |
| `github-update-issue` | Update title, body, state, labels, assignees |
| `github-add-comment` | Post a comment |
| `github-create-pr` | Open a pull request |

Note: there is no `github-manage-dependencies` (GitHub has no dependency API) and no `github-upload-attachment` (not needed — screenshots are committed to `agent-logs/` and embedded via relative path).
