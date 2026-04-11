# Agent Workflow Docs

## Document Relations

- Parent entry point: `AGENTS.md`
- This document is the workflow index for agents and points to the smallest next document to read.
- Child documents:
  - `docs/agent-workflow/git-rules.md`
  - `docs/agent-workflow/git-collaboration-convention.md`
  - `docs/agent-workflow/agent-commit-and-push-workflow.md`
  - `docs/agent-workflow/documentation-rules.md`
  - `docs/agent-workflow/templates.md`
- Related legacy process mirrors:
  - `docs/mvp-v1/process/git-collaboration-convention.md`
  - `docs/mvp-v1/process/agent-commit-and-push-workflow.md`
- If you change scope, ownership, or cross-document rules here, update the child docs and linked legacy mirrors together.

## Purpose

- Keep `AGENTS.md` short.
- Allow `AGENTS.md` to carry a minimal recent-work resume hint without replacing the normal issue and management-document lookup flow.
- Let agents open only the detailed document needed for the current task.
- Separate durable workflow rules from issue-specific management documents.

## Read Order

- At session startup: `AGENTS.md`
- At session startup: `docs/agent-workflow/documentation-rules.md`
- At session startup when git work is expected: `docs/agent-workflow/git-rules.md`
- Before any file edit, creation, move, or deletion: `AGENTS.md` `## Pre-Execution Gate`
- Before any file edit, creation, move, or deletion: `docs/agent-workflow/documentation-rules.md`
- Before commit, push, or PR work: `docs/agent-workflow/git-collaboration-convention.md`
- Before commit, push, or PR work: `docs/agent-workflow/agent-commit-and-push-workflow.md`
- For placeholders, naming formats, and reusable examples: `docs/agent-workflow/templates.md`

## Scope

- These docs are the primary agent-oriented workflow references.
- Treat `docs/mvp-v1/` and `docs/mvp-v2/` as repository-local document index namespaces for this repository only.
- Do not infer product-version meaning or reuse these names outside this repository unless a document explicitly defines that meaning.
- The `docs/mvp-v1/process/` docs remain legacy mirrors and should stay aligned with these primary docs.
