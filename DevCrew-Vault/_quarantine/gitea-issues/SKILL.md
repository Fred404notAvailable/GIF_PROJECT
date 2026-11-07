---
name: gitea-issues
description: Working with Gitea issues — reading tickets, posting progress updates, and managing dependencies. Load this skill at the start of any session where a Gitea issue number is provided.
license: MIT
compatibility: opencode
---

## Prerequisites

This skill requires:

- **`agent-config.json` at the project root** — contains `{ "issue_tracker": { "provider": "gitea", "gitea": { "repo_url": "https://gitea.example.com/owner/repo" } } }`. This file lives in the application repo being worked on, not in the OpenCode config repo. A `GITEA_REPO_URL` environment variable overrides the config value if set.
- **`GITEA_ACCESS_TOKEN`** — environment variable containing a Gitea personal access token with `issue` read/write scope. This is never stored in files.

See `GITEA_SETUP.md` for step-by-step setup instructions.

All Gitea tools gracefully return a configuration error message if the token or URL is missing — no crash, no silent failure.

## Session start

When the user provides a ticket number at the start of a session:

1. Call `gitea-get-issue` with that number immediately.
2. Read the full issue: title, description, labels, state, assignees, and all comments. Comments are returned as part of `gitea-get-issue` output — no separate call is needed.
3. Check whether the issue has dependencies by calling `gitea-manage-dependencies` with `action: "list"`. If blocking issues are open, surface them to the user before proceeding.
4. Treat the issue description as the source of truth for what needs to be done. If it conflicts with the user's verbal summary, surface the discrepancy and confirm before proceeding.
5. Post an opening comment using `gitea-add-comment` to signal that work has begun:

```
🚧 Picking up this ticket. Starting investigation.
```

Do not post the opening comment if the issue is already closed.

## Reading comments

Comments are fetched automatically by `gitea-get-issue` and included in its output. Each comment shows the author, date, and body. Read them carefully — they often contain clarifications, prior investigation notes, review feedback, or scope changes that supersede the original description.

If a comment contradicts the issue body, the comment is more recent and should take precedence unless the user says otherwise.

## During the work

**Post progress comments** at meaningful checkpoints — not after every file edit, but when a significant phase completes:

- After the implementation plan is confirmed
- After the first passing test (if TDD is in play)
- When blocked (with a description of the blocker)
- When handing off between agents (e.g. "backend complete, starting frontend")

Keep comments factual and brief. Examples:

```
✅ Implementation complete. Running reviewers now.
```

```
🔍 @code-reviewer passed. @security-reviewer passed. @observability-reviewer passed. Moving to QA.
```

```
🚫 Blocked: discovered that the `users` table is missing the `email_verified` column. Needs schema migration before this can proceed.
```

## On completion

When all quality gates pass and the PR is opened, post a final comment:

```
✅ Complete. All quality gates passed.

PR: {pr_url}
Task log: agent-logs/YYYY-MM-DD-{slug}/log.md
```

**Do not close the ticket.** The user or the team manages ticket state — closing is not the agent's responsibility.

## Updating issue body

Do not rewrite the issue body unless the user explicitly asks you to. The original description is the spec — preserve it.

If clarifications or scope changes emerge during the work, add them as comments rather than editing the body.

## Dependencies

Gitea supports blocking dependencies between issues. Issue A *depends on* Issue B means B must be resolved before A can proceed.

**Checking dependencies at session start** — always list dependencies when picking up a ticket (see Session start above). If any blocking issue is still open, tell the user and ask whether to proceed anyway or pause.

**Setting a dependency** — if the user says this ticket is blocked by another, or if you discover during planning that a prerequisite ticket needs to exist first:

```
gitea-manage-dependencies
  action: "add"
  issue_number: <this ticket>
  dependency_issue_number: <the blocking ticket>
```

**Removing a dependency** — once a blocking issue is resolved:

```
gitea-manage-dependencies
  action: "remove"
  issue_number: <this ticket>
  dependency_issue_number: <the resolved ticket>
```

**Important — internal IDs vs. display numbers:** Gitea's dependency API requires the internal database `id` of an issue, not its display `number`. The `gitea-manage-dependencies` tool handles this automatically by resolving the display number to an internal ID before calling the API. Always pass display numbers (the `#N` you see in the UI) — never pass raw internal IDs.

## Creating follow-up issues

If the work reveals a bug, tech debt, or deferred item that should be tracked, call `gitea-create-issue` to open a new ticket. Use the current issue number in the body for traceability:

```
Discovered during work on #N. [Description of the follow-up.]
```

If the new issue is a prerequisite for the current one, add a dependency immediately after creating it.

## Label conventions

When creating issues, use labels that already exist in the repository. Do not invent new labels. Common conventions (confirm with the repo's label list before applying):

- `bug` — something is broken
- `enhancement` — new feature or improvement
- `tech-debt` — refactoring or cleanup
- `blocked` — cannot proceed without external action

## Tool reference

| Tool | When to use |
|------|-------------|
| `gitea-get-issue` | Session start; any time you need to re-read the ticket (includes comments) |
| `gitea-list-issues` | When the user asks to see open tickets or pick the next task |
| `gitea-create-issue` | Creating follow-up or child tickets |
| `gitea-update-issue` | Updating issue fields if the user explicitly requests it |
| `gitea-manage-dependencies` | Listing, adding, or removing blocking dependencies |
| `gitea-create-pr` | Opening a PR on completion — coordinated by the `worktrees` skill |
| `gitea-add-comment` | Progress updates, blockers, completion notes |

## Error handling

If any Gitea tool returns an error (network failure, bad token, missing repo):

1. Report the error to the user immediately — do not silently skip.
2. Do not retry automatically more than once.
3. Continue the engineering work regardless — ticket tracking must never block the actual task.
