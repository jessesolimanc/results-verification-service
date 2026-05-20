# Project vision

## Current scope (Q2 OKR)

The results verification service automatically verifies that pipeline
outputs remain within expected ranges across builds. It listens for
completed runs, compares results against registered gold standards, and
generates structured reports with a build verdict.

This is the foundation. It answers one question:

> "Are the pipeline outputs within expected ranges?"

---

## Near-term evolution (Phase 3-4)

As the comparison registry grows, the service naturally expands to verify
not just output accuracy but pipeline workflow integrity:

- Did all expected output files appear?
- Did each pipeline stage complete?
- Is the folder structure correct?
- Did archiving complete successfully?

These are health checks, not just accuracy checks. The registry pattern
absorbs this expansion without structural changes.

---

## Long-term vision: pipeline health monitoring platform

The results verification service is the seed of something larger — an
automated pipeline health monitoring platform that runs continuously
across all lab machines and answers a broader question:

> "Is the pipeline functioning correctly, end to end, on every run?"

### What this could look like

**Automated health reports** — every run produces a structured health
report covering output accuracy, file system integrity, workflow
completion, and performance metrics. Pass/fail verdicts per dimension.

**Cross-machine monitoring** — the service runs on all lab machines,
not just the regression machine. Every production run gets verified,
not just test runs.

**Longitudinal trend analysis** — the database tracks health metrics
over time. Gradual degradation is detected before it becomes a failure.
"Counts have been drifting downward for 3 builds" is caught automatically.

**LLM-powered diagnostics** — the LLM narrative module evolves from
summarising pass/fail results to actively diagnosing anomalies. "Sample
2DU008 has shown increasing deviation over the last 5 builds — this
correlates with a reagent lot change on 2026-04-15. Recommend investigating
lot QC records."

**Log analysis** — pipeline logs are ingested alongside results. The
system surfaces potential bugs automatically: "Stage 3 processing time
has increased 40% since build IAP-v2.4.1 — the change log shows a
new convolution kernel was introduced in that build."

**Alerting** — health degradation triggers notifications to the team
before a run fails completely.

### Why the current architecture supports this

The foundation decisions made in Q2 were deliberately future-oriented:

- **Manifest as contract** (ADR-001) — the manifest can declare any
  kind of health check, not just count tolerances
- **Comparison registry** (ADR-016) — new check types are additive,
  no core code changes needed
- **Decoupled verification service** (ADR-015) — the service is
  independent of the pipeline and can be expanded without touching it
- **Longitudinal database design** — every result is timestamped and
  versioned, ready for trend analysis from day one
- **Event-driven architecture** (ADR-012) — reacts to pipeline events
  naturally, scales to monitoring all machines

None of these decisions need to be revisited to support the vision.
The vision is already implicit in the architecture.

---

## Naming

The service is currently named "results verification service." This name
will become a misnomer as the scope expands. A future rename to something
like "pipeline health service" or "pipeline monitor" is anticipated when
the functionality meaningfully exceeds output verification. For now the
name stays — rename when it no longer fits.

---

## Scope discipline

The vision is captured here to prevent it from being lost, not to expand
the current scope. Q2 OKR focus is output accuracy verification. Future
phases will be prioritised against OKRs in subsequent quarters.

The rabbit hole is documented. The lid is on.
