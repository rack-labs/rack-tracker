# Agent Entry Point

## Recent Active Context

- Last active work: `26-chore-clean-up-repository-before-mvp-v2`
- Tracking doc: `docs/mvp-v2/issues/sub-issues/26-chore-clean-up-repository-before-mvp-v2.md`
- Summary: repository cleanup triage was in progress; keep, remove, move, and archive decisions were being aligned with mvp-v2 management docs and workflow rules.
- Use rule: treat this section as a resume hint only when the user's new work clearly matches the same issue or sub-issue. For simple questions, respond directly without switching work context.

## Document Relations

- This is the agent entry point for this repository.
- Read this file first, then open only the linked detail documents needed for the current task.

## Start Here

- Treat repository documents as source of truth for workflow and tracking rules.
- Treat `docs/mvp-v1/` and `docs/mvp-v2/` as repository-local document index groups for this project.
- Do not generalize `mvp-v1` or `mvp-v2` as global workflow concepts or product-version semantics unless a document explicitly says so.
- For agent workflow overview, read `docs/agent-workflow/README.md`.
- For git, branch, commit, push, and PR rules, read `docs/agent-workflow/git-rules.md`, then open the linked detailed git document only when needed.
- For management-document updates and cleanup logging rules, read `docs/agent-workflow/documentation-rules.md`.
- For issue, branch, commit, PR, and management-document templates, read `docs/agent-workflow/templates.md`.

## Pre-Execution Gate

- Before any file edit, file creation, file move, or file deletion, re-check whether the task belongs to a tracked issue or sub-issue.
- If the task belongs to tracked work, open the matching management document under `docs/mvp-v2/issues/` or `docs/mvp-v2/issues/sub-issues/` before editing files.
- Treat this gate as separate from the session-start read order. Reading `AGENTS.md` once at startup does not satisfy the pre-execution check.
- "Small task", "simple fix", "one-line change", and "quick cleanup" are not exceptions to this gate.
- Only pure question-answer turns with no file changes are exempt.
- If the match or logging duty is unclear, read `docs/agent-workflow/documentation-rules.md` again before making changes.

## Pre-Commit Review Gate

- After completing a work unit, show the user a summary of changed files and request explicit approval before writing the management-document log or committing.
- Write the log and commit only after the user approves.
- Do not log or commit without explicit approval.
- Commit immediately after each approved work unit. Do not accumulate changes across multiple work units and commit later.

## Core Rules

- Read `## Recent Active Context` as a lightweight hint, not as a substitute for issue or management-document discovery.
- When a user requests work, first check whether a reusable open GitHub issue already matches the task.
- After the GitHub issue check, search the repository management documents for the matching work item before choosing where to log progress.
- When the user asks to continue, resume, or update existing work, first search under `docs/mvp-v2/issues/` and `docs/mvp-v2/issues/sub-issues/` for a clearly matching management document.
- If a matching management document exists, use it as the primary local tracking context and keep the GitHub issue, branch, commit, and PR context aligned with it.
- Reuse an existing issue only when it is clearly the same work item. If separate tracking would be cleaner, create a new issue.
- If a matching live issue exists, use that real issue number for the branch name, management document, and commit or PR drafts.
- If no suitable issue exists, try creating one with `gh issue create`.
- If issue creation is unavailable, say so and prepare an issue title and body draft that can be posted immediately.
- Do not guess GitHub issue numbers before an existing issue is confirmed or a new issue is created.
- Use repository-relative paths in workflow rules and management documents. Do not depend on absolute paths that may change with the local workspace.
- Do not revert user changes unless explicitly asked.
- Do not make destructive history edits unless explicitly asked.
