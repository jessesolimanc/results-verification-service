# ADR-015: Decoupled entry point to support future test generator

## Status
Accepted

## Context
The current entry point into the regression testing system is manual:
a developer creates the context manifest and workbooks by hand, then
runs the test harness. This is acceptable for the MVP but is not
scalable.

A future "test generator" application is envisioned that would:
1. Provide a UI for configuring a test run
2. Generate the context manifest automatically
3. Generate stamped workbooks automatically
4. Explicitly kick off the test harness
5. Potentially monitor test progress

A question arose about whether this future component could be added
without rebuilding large portions of the verification service.

## Decision
The verification service entry point is intentionally kept decoupled
from whatever initiates a test run. The service is always-on and
passively listening — it does not care how a run was initiated or who
wrote the manifest.

This is a deliberate architectural decision, not an accidental property
of the current implementation.

## Reasoning
The verification service is already fully event-driven and
manifest-driven (ADR-001). It responds to pipeline DB notifications
and reads whatever manifest it finds at the deterministic path
`context_manifest_{run_id}.json`. It has no knowledge of:

- Who initiated the run
- Whether a UI or a manual process created the manifest
- Whether the test harness was started automatically or manually

This means the test generator is purely **additive** — it produces
inputs (manifest, workbooks) and triggers (test harness start) that
the existing system already knows how to consume. No verification
service code changes are required.

## What changes when the test generator is built
- New application: test generator UI
  - Generates context manifest → writes to manifests_dir
  - Generates stamped workbooks → writes to workbooks_dir
  - Signals test harness to start
- Verification service: no changes

## What stays the same
Everything from the pipeline DB notification onwards is identical
regardless of how the run was initiated:

```
DB notification arrives
    ↓
Listener parses experimentId
    ↓
Orchestrator loads context_manifest_{run_id}.json
    ↓
Gate, comparator, reporter run as normal
```

## Consequences
- The verification service must be running before a test run starts —
  an always-on Windows Service (Phase 4) is the correct deployment
  model to guarantee this
- The test generator does not need to start or manage the verification
  service — it can assume it is already listening
- The manifest schema (ADR-001) is the interface between the test
  generator and the verification service — keeping it stable is
  important as both components evolve

## Relationship to other ADRs
- Extends ADR-001 (manifest as contract) — the manifest remains the
  sole interface regardless of what produces it
- Consistent with ADR-014 (experiment naming convention) — the test
  generator would be responsible for stamping run_id into workbooks
  and folder names at run time, replacing the current manual step

## Alternatives considered
- On-demand startup — test generator starts the verification service
  as part of each run. Rejected because it couples two independent
  components and adds complexity for no benefit given the always-on
  Windows Service model.
