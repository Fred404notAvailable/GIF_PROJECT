---
name: jira
description: Jira issue lifecycle for the build agent. Load this skill when the issue tracker provider is "jira" in agent-config.json. Covers session start, progress tracking, status transitions, and PR linking.
license: MIT
compatibility: opencode
---

## When to use this skill

Load this skill at the start of any session when `agent-config.json` has `issue_tracker.provider = "jira"`. It covers the full issue lifecycle from picking up a ticket to linking the final PR.

Do not load this skill alongside `gitea-issues` or `github-issues` — use one based on the configured provider.

## Configuration check

Before using any Jira tool, verify configuration is present. Call `jira-get-issue` with any known issue key. If it returns an error message referencing `JIRA_SETUP.md`, stop and show the user that message — do not proceed until Jira is configured.

The most common errors are missing `JIRA_EMAIL` or `JIRA_API_TOKEN` environment variables. Direct the user to `JIRA_SETUP.md` — setup takes under a minute.

## Session start

When the user provides a ticket key or asks to claim a Jira issue:

1. **Load this skill** (already done if you're reading this)
2. **Read the ticket** with `jira-get-issue`. Use the issue description as the authoritative spec. If the user's verbal summary conflicts with the ticket body, surface the discrepancy and ask for clarification before proceeding.
3. **Read comments** — they are returned by `jira-get-issue` in the `## Comments` section. If comments contradict the description, comments take precedence (they are more recent). Pay attention to any blocking conditions or dependency notes.
4. **Transition to "In Progress"** — call `jira-transition-issue` with `transition_name` omitted first to see available transitions, then apply the appropriate one (typically "In Progress" or "Start Progress"). If no suitable transition exists, skip and note it.
5. **Post an opening comment** with `jira-add-comment`:

```
🤖 Starting work on this ticket.

Spec understood: {one-sentence summary of what will be done}

Branch: feature/{slug}
Worktree: ~/worktrees/{project}/{slug}
```

## Issue key format

Jira issue keys are in the format `PROJ-123` (project key + number). Always use the full key (not just the number) when calling Jira tools.

For session naming (via `rename-session`), use: `PROJ-123 - {slug}` — e.g. `PROJ-42 - add-user-auth`.

## Reading comments

`jira-get-issue` returns all comments in the `## Comments` section of its output. Each comment shows:

```
@Display Name (YYYY-MM-DD): comment text
```

Comments are shown oldest-first. If there are many, focus on the most recent ones — they reflect the current state. Look for:

- Blocking conditions (don't start work if a blocker is mentioned)
- Clarifications that override the description
- Prior attempts at the same work (avoid duplicate effort)

## Progress updates

Post progress comments at key milestones using `jira-add-comment`:

- When a significant sub-task is complete
- When a blocker is encountered: describe what is blocked and why
- When unblocked: note what resolved it

Keep comments brief. The PR body is the detailed log; Jira comments are status signals.

## Transitions reference

Transition names vary by project workflow. Always call `jira-transition-issue` without `transition_name` first if you're unsure what's available. Common transitions:

| Workflow state | Typical transition name |
|---|---|
| Start work | "In Progress" or "Start Progress" |
| Ready for review | "In Review" or "Ready for Review" |
| Mark complete | "Done" or "Close Issue" |

Do not close or mark tickets done automatically — the user manages final state.

## Dependencies

Jira issue links serve as dependencies. Before starting work:

1. Use `jira-search-issues` with JQL like `issue in linkedIssues("PROJ-123", "is blocked by")` to check for blockers
2. If a blocker exists and is not resolved, report it to the user and ask whether to proceed
3. Use `jira-link-pr` with `link_issue_key` and `link_type` to create issue-to-issue links when relevant (e.g. "relates to", "blocks")

## Assigning issues

Jira Cloud uses opaque `accountId` strings, not usernames. To assign:

1. Call `jira-search-users` with the person's name or email to get their `accountId`
2. Call `jira-assign-issue` with that `accountId`

Never guess or fabricate an `accountId`.

## Linking a PR

When the PR is opened (from the worktrees skill completion sequence), call `jira-link-pr`:

- `issue_key`: the Jira ticket key
- `pr_url`: the PR URL returned by `gitea-create-pr` or `github-create-pr`
- `pr_title`: the PR title

This posts `🔀 PR opened: [title](url)` as a comment on the ticket.

## Screenshots

Screenshots are committed to the feature branch in the `agent-logs/YYYY-MM-DD-{slug}/` folder (managed by the `worktrees` skill). The PR body embeds them using relative paths:

```markdown
![description](agent-logs/YYYY-MM-DD-slug/filename.png)
```

Both Gitea and GitHub render these inline in the PR. `jira-upload-attachment` is still available if you want to attach a screenshot to the Jira ticket itself for visibility in the issue tracker, but it is not required for the PR.

## On completion

When the PR is opened, call `jira-link-pr` to link the PR on the ticket, then post a comment:

```
✅ Complete. All quality gates passed.

PR: {pr_url}
Task log: agent-logs/YYYY-MM-DD-{slug}/log.md
```

**Do not close or mark the ticket Done.** The user manages final ticket state.

## Tool reference

| Tool | Purpose |
|---|---|
| `jira-get-issue` | Read issue details + comments |
| `jira-search-issues` | JQL search |
| `jira-create-issue` | Create a new issue |
| `jira-update-issue` | Update issue fields |
| `jira-add-comment` | Post a comment |
| `jira-transition-issue` | Change status |
| `jira-assign-issue` | Assign to a user |
| `jira-link-pr` | Link PR URL + create issue links |
| `jira-upload-attachment` | Upload screenshots/files |
| `jira-search-users` | Resolve name → accountId |
