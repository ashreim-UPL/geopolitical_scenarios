# Operations Runbook

## Daily Checks

- Confirm ingestion freshness.
- Confirm extraction success.
- Confirm queue backlog is within expected range.
- Confirm alert delivery is functioning.
- Review error logs for new regressions.

## Incident Triage

1. Identify the failing layer.
2. Verify whether the issue is data, extraction, state, scenario, or UI.
3. Check recent deploys and migrations.
4. Preserve evidence before rollback.
5. Record the incident in a follow-up doc or issue.

## Recovery Principles

- Prefer rollback over partial silent repair when evidence is unclear.
- Keep raw source payloads intact.
- Never overwrite extracted events without versioning.

