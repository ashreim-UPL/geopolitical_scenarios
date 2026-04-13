# Scenario Engine Spec

## Objective

Maintain and update a probability distribution over geopolitical scenarios using weighted evidence and rule-based constraints.

## Initial Scenario Set

- Managed confrontation
- Hybrid pressure equilibrium
- Maritime or infrastructure shock
- Controlled partial reopening or corridor deal
- Regional war escalation
- Internal fragmentation or political rupture
- Negotiated stabilization

## Inputs

- extracted events
- source reliability
- novelty
- severity
- actor posture
- threshold conditions

## Output Per Scenario

- probability
- delta versus prior window
- top supporting evidence
- top contradicting evidence
- trigger thresholds to the next state

## Engine Principles

- Start with simple weighted Bayesian updates.
- Apply rule-based caps and floors for hard constraints.
- Keep every probability change explainable.
- Preserve contradictory evidence instead of discarding it.

