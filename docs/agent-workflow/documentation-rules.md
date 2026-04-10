# Agent Documentation Rules

## Document Relations

- Parent index: `docs/agent-workflow/README.md`
- Related git convention: `docs/agent-workflow/git-collaboration-convention.md`
- Related git execution guide: `docs/agent-workflow/agent-commit-and-push-workflow.md`
- Related templates: `docs/agent-workflow/templates.md`
- Related cleanup tracker: `docs/mvp-v2/issues/sub-issues/26-chore-clean-up-repository-before-mvp-v2.md`
- If documentation workflow rules change here, update `AGENTS.md`, the git workflow docs, the template reference, and any active management document that encodes the old rule.

## Management Document Rule

- Apply the pre-execution check immediately before any file edit, file creation, file move, or file deletion.
- Treat that pre-execution check as separate from session-start rule reading.
- Use behavior, not perceived task size, to decide whether the check applies.
- "Small task", "simple fix", "one-line change", "quick cleanup", and similar labels are not exceptions.
- Only pure question-answer turns with no file changes are exempt.
- If the match or logging duty is unclear, re-read this file before changing files.
- `AGENTS.md` may include a short `## Recent Active Context` block near the top.
- Keep that block lightweight: prefer a last active work name, a repository-relative tracking-document path, and a one-line summary.
- Treat that block as a resume hint only. It does not replace GitHub issue lookup or management-document discovery.
- Use the recent active context only when the user's new request clearly belongs to the same issue or sub-issue.
- For simple questions or unrelated requests, answer directly or follow the normal issue and management-document lookup flow without forcing reuse of the recent active context.
- After checking for a matching GitHub issue, search the repository for the management document that matches the work before creating a new one.
- When the task is to continue, resume, or update ongoing work, search `docs/mvp-v2/issues/` and `docs/mvp-v2/issues/sub-issues/` first.
- Reuse an existing management document only when the issue, summary, scope, and current requested work clearly match.
- If no suitable management document exists after that search, create one under the matching issue-type directory before committing.
- Before any commit, update the management document that matches the work.
- Do not log every task in one fixed document.
- For issue-tracked work, create or update an issue-specific management document named after the issue branch.
- Place the management document under the matching issue-type directory, such as `docs/mvp-v2/issues/feature/`, `fix/`, `refactor/`, `docs/`, or `chore/`. Use `docs/mvp-v2/issues/sub-issues/` when the work is tracked as a scoped child task under a broader issue.
- Use the issue branch name as the management document file name.
- Keep the issue title, issue number, branch name, directory type, and management document file name aligned.
- Use repository-relative paths in management documents so the rules remain stable if the local workspace root changes.

## Work Log Rule

- Record implementation progress in the issue management document at commit-sized granularity.
- Use one `##` section per commit-sized work unit.
- Use the commit title as that section heading.
- Lower headings and sub-structure inside a log section are optional. Use them only when they improve readability.
- After completing a work unit, show the user a summary of changed files and request explicit approval before writing the log or committing.
- Write the log and commit only after the user approves. Do not log or commit without approval.
- Commit immediately after each approved work unit. Do not accumulate changes across multiple work units and commit later.
- If files changed without a matching management-document update, treat that as a workflow miss and correct it in the same work session.

## Fast Correction Loop

- Prefer a repository-local check that reports file changes without a matching management-document update before commit.
- Use `scripts/check-management-doc-update.ps1 -Staged` for a pre-commit style check.
- The script expects the changed management document to match the current branch name.
- If Git hooks are enabled with `git config core.hooksPath .githooks`, the repository hook should run that script automatically before commit.
- Use the script as a correction tool, not as permission to skip the pre-execution gate.

## Cleanup Rule

- For repository cleanup work, record keep, remove, move, or archive decisions in the relevant management document.
- Prefer `archive/` over immediate deletion when a path may still be useful for reference.
- Keep active implementation paths separate from legacy, sample, experimental, or output assets.

## Sync Rule

- When a workflow change affects multiple docs, update the related docs in the same change.
- Do not let top-level guidance and detailed templates diverge.
