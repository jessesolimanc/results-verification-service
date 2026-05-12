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
├── src/
│   ├── main.py         Entry point
│   ├── registration/   Gold standard registration tool
│   ├── listener/       Polls pipeline DB for completed runs
│   ├── gate/           Pre-verification integrity checks
│   ├── orchestrator/   Coordinates the verification flow
│   ├── comparator/     Per-sample comparison logic
│   ├── llm/            LLM API calls and prompt management
│   ├── reporter/       Assembles and writes reports
│   └── database/       All database interaction
└── tests/              Unit tests
```

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
