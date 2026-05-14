# Project status

Quick reference for current implementation state. Update this file at the end of every development session.

Last updated: 2026-05-14 (session 5)
Current phase: Phase 2 — Happy path end to end

---

## Implementation status

### `src/database/`
| File | Function | Status | Notes |
|---|---|---|---|
| `db.py` | `get_connection()` | ✅ Done | |
| `db.py` | `initialise_database()` | ✅ Done | Wired to `--init` in main.py |
| `models.py` | `insert_gs_exp_version()` | ✅ Done | |
| `models.py` | `insert_gs_sample()` | ✅ Done | |
| `models.py` | `get_active_gs_version()` | ✅ Done | |
| `models.py` | `retire_gs_version()` | ✅ Done | |
| `models.py` | `insert_run()` | ✅ Done | |
| `models.py` | `get_all_processed_run_ids()` | ✅ Done | Replaces get_unprocessed_runs() — NOTIFY/LISTEN push model needs deduplication check, not a poll query |
| `models.py` | `insert_experiment_result()` | ✅ Done | |
| `models.py` | `insert_sample_result()` | ✅ Done | |
| `models.py` | `insert_report()` | ✅ Done | |

### `src/registration/`
| File | Function | Status | Notes |
|---|---|---|---|
| `registrar.py` | `compute_checksum()` | ✅ Done | Reused by gate module |
| `registrar.py` | `read_gold_standard_csv()` | ✅ Done | Skips 4 metadata rows; wide-format only |
| `registrar.py` | `register_gold_standard()` | ✅ Done | Atomic transaction; retires previous version if exists |

### `src/listener/`
| File | Function | Status | Notes |
|---|---|---|---|
| `listener.py` | `parse_experiment_notification()` | ✅ Done | Splits on _run_, reconstructs run_id as run_YYYYMMDD_NNN |
| `listener.py` | `listen_async()` | ✅ Done | asyncpg NOTIFY/LISTEN with retry loop; filters INSERT only |
| `listener.py` | `listen_async_mock()` | ✅ Done | Fires hardcoded payload, sleeps indefinitely |

### `src/gate/`
| File | Function | Status | Notes |
|---|---|---|---|
| `gate.py` | `checksum_check()` | ⬜ Not started | Imports compute_checksum from registrar |
| `gate.py` | `subset_check()` | ⬜ Not started | |
| `gate.py` | `run_gate()` | ⬜ Not started | |

### `src/orchestrator/`
| File | Function | Status | Notes |
|---|---|---|---|
| `orchestrator.py` | `load_manifest()` | ✅ Done | Constructs path from run_id + config; raises FileNotFoundError if missing |
| `orchestrator.py` | `find_result_folder()` | 🔲 Stub | Globs for {exp_id}_{run_id}_* under workbooks_dir |
| `orchestrator.py` | `verify_run()` | 🔲 Stub | |

### `src/comparator/`
| File | Function | Status | Notes |
|---|---|---|---|
| `comparator.py` | `compare_sample()` | ⬜ Not started | |
| `comparator.py` | `compare_experiment()` | ⬜ Not started | |

### `src/llm/`
| File | Function | Status | Notes |
|---|---|---|---|
| `analyst.py` | `build_prompt()` | ⬜ Not started | |
| `analyst.py` | `generate_narrative()` | ⬜ Not started | |

### `src/reporter/`
| File | Function | Status | Notes |
|---|---|---|---|
| `reporter.py` | `determine_experiment_verdict()` | ⬜ Not started | |
| `reporter.py` | `determine_run_verdict()` | ⬜ Not started | |
| `reporter.py` | `write_report()` | ⬜ Not started | |

### `src/main.py`
| Function | Status | Notes |
|---|---|---|
| `load_config()` | ✅ Done | |
| `init()` | ✅ Done | |
| `register()` | ✅ Done | |
| `run()` | ✅ Done | |
| `run_service()` | ✅ Done | Async loop — accumulates experiments per run_id, triggers verify_run when set is complete |

---

## Schema status

| Change | Status | Notes |
|---|---|---|
| Initial schema from DDL | ✅ Applied | |
| Added `primary_metric`, `primary_metric_value` to `gold_standard_samples` | ✅ Applied | MVP scaffolding — to be dropped once full JSON comparison implemented |
| Added `full_metrics` JSON column to `gold_standard_samples` | ✅ Applied | |
| Added `primary_metric`, `actual_value`, `expected_value`, `deviation_percent` to `sample_results` | ✅ Applied | MVP scaffolding |
| Added `full_actual_metrics`, `full_expected_metrics` JSON columns to `sample_results` | ✅ Applied | |

---

## Open design questions

| Question | Status |
|---|---|
| Linkage experiment success criteria — not count-based, TBD | 🔲 Unresolved |
| Dynamic range experiment — may need curve metric not per-sample tolerance | 🔲 Unresolved |
| 10-channel experiment — per-channel criteria TBD | 🔲 Unresolved |
| Image paths for all 5 experiments — pending image transfer to regression machine | 🔲 Unresolved |
| Primary metric column name per experiment type — hardcoded as UM-01_CountsPer50ul for MVP | ✅ Resolved |
| RnDdata CSV uses long/melted format — needs pivot preprocessing. Not needed for MVP. | 🔲 Future |
| Pipeline DB schema — reports_table_changes NOTIFY channel confirmed. ExperimentId carries full {exp_id}_{run_id}_{timestamp} string | ✅ Resolved |
| Workbook generator — automates workbook stamping with run_id. Out of scope for MVP, done manually. | 🔲 Future |

---

## Key architectural decisions (recent)

- **Listener changed from polling to PostgreSQL NOTIFY/LISTEN** (ADR-012 supersedes ADR-004)
- **Mock listener added for dev** — controlled by `listener.use_mock` config flag (ADR-013)
- **Experiment folder naming** — `{exp_id}_{run_id}_{timestamp}`, test harness does rename at runtime (ADR-014)
- **run_id is a coordination mechanism only** — base `exp_id` remains the stable longitudinal key in verification DB

---

## Build phases

### Phase 1 — Foundation
- [x] Project structure and skeleton
- [x] Virtual environment and dependencies
- [x] Database initialisation
- [x] database-schema.md updated to match current DDL
- [x] Gold standard registration tool
- [x] models.py gold standard insert functions

### Phase 2 — Happy path end to end
- [ ] models.py remaining insert functions
- [ ] Listener — mock + real (asyncpg)
- [ ] Orchestrator (manifest loading, folder lookup, flow coordination)
- [ ] Pre-verification gate (checksum check)
- [ ] Comparator (per-sample comparison)
- [ ] Reporter (basic structured report, no LLM)
- [ ] main.py run() wired to asyncio event loop

### Phase 3 — Harden and complete
- [ ] Subset validity check in gate
- [ ] All 5 experiments wired up
- [ ] LLM narrative module
- [ ] Edge case handling (aborted runs, missing manifests, malformed payloads)

### Phase 4 — Observability
- [ ] Longitudinal queries and trend detection
- [ ] Run-level summary reports
- [ ] Windows Service wrapper

---

## Notes

Listener redesign (session 4):
- Pipeline DB is PostgreSQL with existing NOTIFY triggers on Reports and Workbooks tables
- reports_table_changes channel fires on INSERT/UPDATE/DELETE with ExperimentId in payload
- asyncpg added to requirements.txt
- Full async architecture required — main.py run() uses asyncio.run()
- Mock listener unblocks development on personal machine without pipeline DB access
