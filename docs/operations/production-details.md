# Production Details

## Deployment Model

Start with Docker-based deployment. Move to Kubernetes only when scale or operational complexity justifies it.

## Production Components

- web frontend
- API service
- worker service
- scheduler
- Postgres
- TimescaleDB extension
- graph database
- Redis
- object storage for raw documents

## Required Environment Variables

- `DATABASE_URL`
- `REDIS_URL`
- `OBJECT_STORAGE_URL`
- `OBJECT_STORAGE_ACCESS_KEY`
- `OBJECT_STORAGE_SECRET_KEY`
- `GRAPH_DB_URL`
- `GRAPH_DB_USER`
- `GRAPH_DB_PASSWORD`
- `NEXT_PUBLIC_API_BASE_URL`

## Operational Requirements

- raw payload retention
- provenance retention
- versioned analyst overrides
- observable ingestion latency
- observable extraction success rate
- reproducible scenario updates

## Monitoring

- ingestion freshness latency
- extraction pipeline success rate
- source coverage
- scenario update latency
- alert delivery success
- API error rate

## Backup and Recovery

- Back up relational data regularly.
- Preserve raw documents separately from derived tables.
- Test restore procedures before production cutover.

## Release Discipline

- No silent schema changes.
- Ship migrations with rollback notes.
- Document production impact before deploy.

