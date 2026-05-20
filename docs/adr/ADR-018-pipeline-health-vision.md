# ADR-018: Evolution toward pipeline health monitoring

## Status
Accepted — future direction captured, out of current OKR scope

## Context
During development of the results verification service, it became clear
that the architecture naturally supports a broader scope than output
accuracy verification. The comparison registry, event-driven listener,
longitudinal database, and manifest-as-contract design all point toward
a general pipeline health monitoring capability.

A decision was needed about whether to pursue this expanded scope now
or capture it for future work.

## Decision
The expanded vision is captured as a formal architectural direction but
explicitly deferred beyond the current OKR scope. The Q2 focus remains
output accuracy verification. Future phases will be prioritised against
OKRs in subsequent quarters.

The architecture is confirmed as intentionally future-oriented — no
decisions need to be revisited to support the vision. The foundation
is already in place.

## The Expanded Vision

The results verification service is the seed of a pipeline health
monitoring platform. The evolution is natural and additive:

**Phase 2 (current OKR):** Output accuracy
- Count tolerance checks on CountableDataSummary.csv
- Build verdict based on stability experiment results

**Phase 3:** File system integrity
- `file_exists` comparison type — did expected files appear?
- `folder_structure` comparison type — is output structure correct?
- E: drive deletion watch as pipeline completion signal

**Phase 4:** Workflow completion
- `stage_completion` checks
- `processing_time` checks
- Metadata unzip and RnDdata comparison types

**Phase 5:** Full pipeline health platform
- Cross-machine monitoring (all lab machines, not just regression)
- LLM-powered diagnostics — anomaly detection, log analysis
- Automated alerting on health degradation
- Correlation of results with reagent lots, build changes, etc.

## Why the Current Architecture Supports This

Every foundational decision was made with this evolution in mind:

- **Manifest as contract (ADR-001)** — can declare any health check type
- **Comparison registry (ADR-016)** — new types are purely additive
- **Decoupled entry point (ADR-015)** — service is independent of pipeline
- **Longitudinal database** — trend analysis ready from day one
- **Event-driven listener (ADR-012)** — scales to monitoring all machines

## Naming

Service remains "results verification service" until the functionality
meaningfully exceeds output verification. Rename anticipated when scope
expands to full pipeline health monitoring.

## Consequences
- Future phases are documented in `docs/vision.md`
- New comparison types continue to be added to the registry as the
  natural extension point
- Database schema is already designed to support longitudinal health
  trend analysis
- No current code needs to change to support future phases

## What This Is Not
This ADR does not expand the current OKR scope. It is a record of
architectural intent and future direction, not a commitment to deliver
beyond the current quarter.
