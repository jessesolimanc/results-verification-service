# ADR-008: Experiment-level gold standard versioning

## Status
Accepted

## Context
Gold standards will be updated over time as algorithms improve or reference data is corrected. The system needs to track which version of a gold standard governed each run, and allow independent versioning of individual experiments without forcing all experiments to be re-registered simultaneously.

## Decision
Each experiment maintains its own independent version history in `gold_standard_exp_versions`. A version is retired by setting `superseded_at` — it is never deleted. `experiment_results` and `sample_results` link directly to `gs_exp_version_id`, anchoring every result to the exact gold standard version it was verified against.

## Reasoning
- Experiment-level versioning means updating one experiment's gold standard does not require re-registering all others
- The FK to `gs_exp_version_id` makes longitudinal queries explicit — you can query trends within a fixed baseline or across all versions
- Retiring rather than deleting versions preserves full audit history
- The natural identifier (`experiment_id`) repeating across versions is expected and correct — surrogate PKs ensure row uniqueness

## Consequences
- Longitudinal queries must be baseline-aware — comparing results across a version boundary requires intent
- The same `experiment_id` and `sample_id` will appear in multiple rows across versions — this is by design
- Registering a new gold standard version is a deliberate, audited act (see registration workflow in manifest-schema.md)

## Alternatives considered
- Global version number across all experiments — rejected because it forces all experiments to increment together even when only one changes
- No versioning — rejected because it makes longitudinal tracking across gold standard updates impossible
