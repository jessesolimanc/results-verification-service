# ADR-007: Immutable result snapshots — no backpropagation

## Status
Accepted

## Context
When a gold standard is updated, historical result records contain `expected_value` fields that were compared against an older baseline. A question arose about whether to update these historical expected values to reflect the new gold standard.

## Decision
Historical records are never modified. `expected_value` in `sample_results` is a snapshot of what was expected at the time of the run. It is never backfilled or updated when a gold standard changes.

## Reasoning
- Historical records are a factual account of what happened — retroactive modification destroys that
- A longitudinal trend is only meaningful when all data points in the trend were measured against the same baseline
- Gold standard version tracking (ADR-008) provides the correct mechanism for handling baseline changes
- Silent backpropagation would make it impossible to detect when a gold standard update caused a result shift

## Consequences
- Longitudinal queries must filter by gold standard version to be meaningful across a version boundary
- The discontinuity introduced by a gold standard update is visible in the data — this is a feature, not a bug
- Developers must be aware that `expected_value` in historical records reflects the standard at time of run

## Alternatives considered
- Backpropagate expected values on gold standard update — rejected because it destroys historical accuracy and makes version boundaries invisible
