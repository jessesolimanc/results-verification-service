# ADR-009: Gold standard release as optional convenience snapshot

## Status
Accepted

## Context
A question arose about how to represent a "version" of the full gold standard suite — a way to say "as of this date, these were the active standards across all experiments."

## Decision
A `gold_standard_release` is an optional, non-load-bearing convenience snapshot. It records which experiment versions were active at a point in time via a join table (`release_entries`). Nothing in the verification logic depends on releases — they exist purely for human reference.

## Reasoning
- The experiments and their expected values are the real source of truth — not any grouping of them
- A release is just a label on a moment in time: "as of release 3, these were the active versions"
- Forcing all experiments to be re-registered under a new release on every update would be burdensome and error-prone
- Decoupling releases from the FK structure means individual experiment versioning is fully independent

## Consequences
- Releases are optional — the system works correctly whether or not releases are ever created
- To determine what was current on a given date without a release, query `superseded_at` ranges on `gold_standard_exp_versions`
- The `release_entries` join table can be populated by a simple script that snapshots all currently active versions

## Alternatives considered
- Release as a required FK anchor for all experiment versions — rejected because it forces coordinated re-registration of all experiments on every update
- No release concept at all — acceptable for the MVP but useful enough to include as an optional convenience
