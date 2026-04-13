# ADR 0001: Monorepo and Docs-First Scaffold

## Status

Accepted

## Context

The repository currently contains two source documents that define a full product vision, technical architecture, workflow rules, and production expectations. There is no implementation yet.

## Decision

Create a documentation-first repository scaffold with:

- root `README.md`
- root `CODEX.md`
- structured `docs/` hierarchy
- engineering workflow documentation
- production documentation
- GitHub PR and issue templates
- placeholder directories for future apps and packages

## Alternatives Considered

- Jump directly into code without documentation
- Keep the source documents only
- Split into multiple repos immediately

## Consequences

- The repo becomes usable immediately as a planning and implementation base.
- Future implementation work has an agreed layout and workflow.
- The next coding step can proceed without re-litigating the core product intent.

