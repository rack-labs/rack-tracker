# Agent Workflow Templates

## Document Relations

- Parent index: `docs/agent-workflow/README.md`
- Related rule summaries:
  - `docs/agent-workflow/git-rules.md`
  - `docs/agent-workflow/documentation-rules.md`
- Related detailed git references:
  - `docs/agent-workflow/git-collaboration-convention.md`
  - `docs/agent-workflow/agent-commit-and-push-workflow.md`
- Related legacy mirrors:
  - `docs/mvp-v1/process/git-collaboration-convention.md`
  - `docs/mvp-v1/process/agent-commit-and-push-workflow.md`
- If a format or placeholder changes here, update the matching rule summaries, detailed git references, and legacy mirrors together.

## Issue Placeholder

- Use `#<issue-number>` until GitHub assigns the real number.

## Branch Placeholder

- Use `<issue-number>-type-short-description` until GitHub assigns the real issue number.

## Branch Example

- `26-chore-clean-up-repository-before-mvp-v2`

## Commit Message Template

```text
type: short summary (#<issue-number>)

- change item 1
- change item 2
- change item 3
```

## Issue Template

```text
[TYPE] Short work summary

## Goal
Explain why this work is needed.

## Scope
- Item to implement or fix
- Main behavior or code changes

## Done Criteria
- Conditions that mark the work complete

## References
Related links or documents
```

## PR Title Template

```text
[TYPE] Short work summary (#<issue-number>)
```

## PR Description Template

```text
## Related Issue
Closes #<issue-number>

## Work Summary
- Main implementation or fixes
- Important changes

## Change Details
- Structure or module changes
- API or behavior changes

## Test Method
1. How to run
2. What scenario was checked

## Screenshots / Results
```

## Issue Management Document Path Examples

- `docs/mvp-v2/issues/feature/41-feature-video-upload-api.md`
- `docs/mvp-v2/issues/fix/52-fix-webcam-crash.md`
- `docs/mvp-v2/issues/refactor/33-refactor-mediapipe-module.md`
- `docs/mvp-v2/issues/docs/17-docs-readme-update.md`
- `docs/mvp-v2/issues/chore/26-chore-clean-up-repository-before-mvp-v2.md`
- `docs/mvp-v2/issues/sub-issues/26-chore-clean-up-repository-before-mvp-v2.md`

## Path Rule

- Use repository-relative paths in workflow docs, templates, and management documents.
- Do not write absolute local filesystem paths such as `C:/...` into reusable workflow rules.

## Pre-Execution Gate Template

```text
Before any file edit, creation, move, or deletion, re-check whether the task belongs to tracked issue work.
If it does, open the matching management document first.
"Small task", "simple fix", "one-line change", and "quick cleanup" are not exceptions.
Only pure question-answer turns with no file changes are exempt.
If unsure, read `docs/agent-workflow/documentation-rules.md` again before changing files.
```

## Recent Active Context Template

```text
## Recent Active Context

- Last active work: `26-chore-clean-up-repository-before-mvp-v2`
- Tracking doc: `docs/mvp-v2/issues/sub-issues/26-chore-clean-up-repository-before-mvp-v2.md`
- Summary: repository cleanup triage was in progress; keep, remove, move, and archive decisions were being aligned with mvp-v2 management docs and workflow rules.
- Use rule: treat this section as a resume hint only when the user's new work clearly matches the same issue or sub-issue. For simple questions, respond directly without switching work context.
```

## Issue Management Document Template

```text
# [TYPE] Short work summary
Parent: #<parent-issue-number-or-placeholder>

## Document Relations
- This document tracks one issue-sized work item.
- Keep this file name aligned with the issue branch name.
- Place this file under the matching issue-type directory.
- Update this document before each related commit.

## Summary
Short context for the issue-sized work item.

## Goal
- What this issue needs to achieve

## Scope
- Planned implementation or cleanup scope

## Out Of Scope
- Explicit non-goals

## Done Criteria
- Conditions that mark the issue complete

---

## Work Log

### type: short summary (#<issue-number>)

> One-line description of what changed and why

#### Scope
#### Changes
#### Verification
#### Notes

---

## Management Notes

### Follow-up Candidates
- Items deferred for later issues

### Notes
- Decisions, constraints, or risks worth preserving

### References
- Related issues, docs, or links
```
