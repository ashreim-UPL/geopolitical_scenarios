# Git Management

## Branching Model

Use trunk-based development with short-lived branches.

## Branch Naming

- `feat/<short-name>`
- `fix/<short-name>`
- `refactor/<short-name>`
- `docs/<short-name>`
- `chore/<short-name>`

## Commit Rules

Use conventional commits:

- `feat: add state taxonomy contracts`
- `fix: normalize scenario weights`
- `docs: add event ontology v1`
- `refactor: separate impact engine from scenario engine`

## Pull Request Rules

Every PR should include:

- purpose
- scope
- screenshots if UI changes
- test summary
- migration note if schema changes
- rollback note if risky
- related issue or ADR reference

## Safety Rules

- Keep PRs small when practical.
- Keep changes reversible.
- Do not silently rewrite source-of-truth data.

