# Results Verification Service

Automated regression testing system for the Countable PCR image analysis pipeline.

## Overview

The verification service runs on a dedicated lab machine. It polls the pipeline database for completed test runs, verifies results against registered gold standards, and generates reports.

See `docs/architecture.md` for the full system design.

## Project structure

```
results-verification-service/
├── docs/               Architecture, schema reference, ADRs, glossary
├── schema/             SQLite DDL
├── config/             Configuration (paths, polling interval, tolerances)
├── entry_point/        Manifest template + stamping script for the
│                       GitHub Actions trigger (ADR-023) — see below
├── .github/workflows/  trigger_regression_run.yml — manual workflow_dispatch
│                       entry point, runs on the regression machine itself
├── src/
│   ├── main.py         Service entry point (the always-on listener/orchestrator)
│   ├── registration/   Gold standard registration tool
│   ├── listener/       Listens for pipeline DB NOTIFY events
│   ├── gate/           Pre-verification integrity checks
│   ├── orchestrator/   Coordinates the verification flow
│   ├── comparator/     Per-sample comparison logic
│   ├── llm/            LLM API calls and prompt management
│   ├── reporter/       Assembles and writes reports
│   └── database/       All database interaction
└── tests/              Unit tests
```

## Triggering a regression run

Runs are started manually with the "Trigger Regression Run" GitHub Actions
workflow (`workflow_dispatch`), after a build has been produced and
installed on the regression machine by hand — this workflow does not
build or install anything itself. Dispatching it stamps a new manifest
from `entry_point/manifest_template.json` and starts the test harness;
it does not wait for verification to complete. See ADR-023 for the full
design and its `entry_point/stamp_manifest_for_run.py` --help for the
same script run locally/manually.

Requires a self-hosted GitHub Actions runner registered on the regression
machine (labels `self-hosted, pcr-regression`) and two repository
variables set (Settings → Secrets and variables → Actions → Variables):
`PCR_MANIFESTS_DIR` (matching `config.paths.manifests_dir` on that
machine) and `PCR_TEST_HARNESS_EXE_PATH` (where the built test harness
executable lives there).

## Data directory

Runtime data lives outside the project on the regression machine:

```
C:/RegressionTesting/
├── manifests/          Run context manifests (written by test harness)
├── gold_standards/     Gold standard CSVs
├── workbooks/          Experiment workbooks
└── verification.db     SQLite database
```

Paths are configured in `config/config.yaml`.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create the data directory and initialise the database:
   ```
   python src/main.py --init
   ```

3. Register gold standards:
   ```
   python src/main.py --register
   ```

4. Start the service:
   ```
   python src/main.py --run
   ```

## Dependencies

See `requirements.txt`.
