# Event Ontology

## Event Categories

- military strike
- drone attack
- missile launch
- infrastructure damage
- maritime disruption
- shipping reroute
- sanctions action
- diplomatic meeting
- official threat
- official de-escalation signal
- militia activity
- border incursion
- mobilization
- force deployment
- market shock
- refinery outage
- LNG disruption
- peacekeeping casualty

## Common Fields

- `event_id`
- `title`
- `event_type`
- `timestamp_utc`
- `location_name`
- `latitude`
- `longitude`
- `actors_involved`
- `target_type`
- `source_ids`
- `extraction_confidence`
- `severity_score`
- `novelty_score`
- `attribution_status`
- `narrative_tags`
- `linked_scenarios`

## Design Rules

- Every event keeps source provenance.
- Observed facts stay separate from inferred dynamics.
- Analyst review can override weak extraction, but the override is versioned.

