# Contributing

## Scope

This project is contract-first and evidence-traceable. Changes must preserve domain purity and explainability.

## Workflow

1. Create a short-lived branch from `main`.
2. Update contracts before implementation when behavior changes.
3. Add tests with each behavioral change.
4. Update relevant docs in `docs/`.
5. Open a PR with risk and rollback notes.

## PR Checklist

- Purpose and scope are clear.
- Contracts updated when needed.
- Tests added or updated.
- Docs updated.
- Rollback path documented for risky changes.

## Commit Style

Use conventional commits:

- `feat: ...`
- `fix: ...`
- `docs: ...`
- `refactor: ...`
- `chore: ...`

