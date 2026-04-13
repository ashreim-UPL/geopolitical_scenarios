# Command Reference

This repo includes runnable web and API starter apps.

## Repo Inspection

- `Get-ChildItem -Force`
- `Get-ChildItem -Force -Recurse`
- `git status --short`
- `git branch --show-current`

## Web Commands

- `cd apps/web`
- `npm install`
- `npm run dev`
- `npm run lint`
- `npm run build`

## API Commands

- `cd apps/api`
- `pip install -e .[dev]`
- `uvicorn geostate_api.main:app --reload --host 0.0.0.0 --port 8000`
- `pytest -q`

## Command Discipline

- Prefer small, explicit commands.
- Document any new command in this file.
- If a command affects production, add it to the runbook.
