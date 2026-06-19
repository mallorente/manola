# Domain Docs

Manola is a single-context repo. Engineering skills should use the root project docs as the domain source.

## Before exploring, read these

- `AGENTS.md` for repo workflow, constraints, and current implementation notes.
- `docs/PRD.md` for product requirements.
- `docs/STATUS.md` for current implementation state and known gaps.
- `docs/UI_PLAN.md` for local web UI scope and backend gaps.
- `docs/ADR-*.md` for durable technical decisions.

If a `CONTEXT.md`, `CONTEXT-MAP.md`, or `docs/adr/` directory is added later, read it as additional domain context. Do not require those files to exist before proceeding.

## Vocabulary

Use Manola's existing product language in issues and implementation plans:

- local meeting archive
- shared export
- share policy
- meeting folder
- metadata suggestions
- live transcript
- canonical transcript
- report
- recording job
- backend gap

Avoid inventing a second source of truth for meetings. The local archive and existing CLI/backend services remain authoritative.

## ADR Conflicts

If proposed work contradicts an existing ADR, surface the conflict explicitly before changing the architecture.
