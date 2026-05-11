# Results verification service — architecture overview

## Purpose

The results verification service is a regression testing system built on top of the existing Countable PCR production pipeline. It runs on a dedicated lab machine in an isolated environment and automatically verifies that pipeline outputs remain within expected ranges across builds.

The system has two decoupled pieces:

1. **Test harness** — drives the main app through real workflows using known gold standard inputs
2. **Results verification service** — listens for completed runs and independently judges whether outputs match expectations

These two pieces communicate through a single shared artifact: the **run context manifest**.

---

## Guiding principles

- **The manifest is the contract.** Everything the verification service needs is either contained in or referenced by the manifest. The test harness writes it; the verification service reads it. Neither piece needs to know about the other's internals.
- **Loud failures over silent ones.** The system should never produce a result that cannot be trusted. Pre-verification gates abort early with a clear reason rather than producing a potentially meaningless comparison.
- **Single source of truth.** Gold standards live in one place. The database records what was expected at the time of each run as an immutable snapshot.
- **Separation of concerns.** The science team owns gold standards and tolerances. The engineering team owns verification logic. The manifest is the interface between them.
- **Designed to evolve.** The MVP uses a static manifest and simple tolerances. The schema and architecture are designed so that customisation, a manifest generator, and richer success criteria can be added without structural changes.

---

## Component overview

```
Dedicated regression machine
│
├── Test harness (scenario driver)
│     Reads the manifest, drives the main app workflows,
│     feeds gold standard images through the pipeline
│
├── Run context manifest (JSON file)
│     Written by the test harness at run start.
│     The contract between the two halves of the system.
│
└── Results verification service (Windows Service)
      │
      ├── Listener
      │     Polls the pipeline database for completed runs
      │
      ├── Pre-verification gate
      │     Checksum integrity check
      │     Subset validity check (child experiments)
      │
      ├── Orchestrator
      │     Loads manifest, coordinates per-sample comparison
      │
      ├── LLM analysis module
      │     Sends structured results to Claude API for narrative
      │
      ├── Report writer
      │     Assembles and stores the final report
      │
      └── Verification database (SQLite)
            Stores runs, experiment results, sample results,
            gold standards, and reports
```

---

## Data flow

```
1. Test harness writes manifest → watched folder
2. Test harness drives main app → pipeline runs
3. Pipeline results land in pipeline database
4. Listener detects completed run (polling)
5. Orchestrator loads manifest via run_id
6. Pre-verification gate runs:
     a. Checksum check — gold standard file unmodified?
     b. Subset check — all samples present in parent? (if child experiment)
7. Per-sample comparison against gold standard
8. LLM module generates narrative from structured results
9. Report writer stores report in verification database
10. Build verdict recorded: pass / fail / warn / aborted
```

---

## Environment

- **Machine:** dedicated lab machine, isolated environment
- **No production runs** touch this machine — every run is a regression test run
- **Pipeline database:** central database on a separate machine, read-only from the verification service's perspective
- **Verification database:** local SQLite file on the regression machine
- **Service model:** Windows Service, starts on boot, runs continuously

---

## Key interfaces

| Interface | Direction | Description |
|---|---|---|
| Run context manifest | Harness → service | JSON file, keyed by run_id |
| Pipeline database | Pipeline → service | Read-only, polled for completed runs |
| Gold standard CSV | Disk → service | Read at registration time only |
| Anthropic API | Service → LLM | Structured results in, narrative out |
| Verification database | Service → SQLite | All verification outputs stored here |

---

## Related documents

- [Manifest schema](manifest-schema.md)
- [Database schema](database-schema.md)
- [Glossary](glossary.md)
- [ADR index](adr/index.md)
