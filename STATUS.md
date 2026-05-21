# Project status

Quick reference for current implementation state. Update this file at the end of every development session.

Last updated: 2026-05-21 (session 11)
Current phase: MVP feature complete — PR review hardening

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
| `models.py` | `get_gs_samples()` | ✅ Done | Returns list of sample dicts for a gs_exp_version_id |
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
| `listener.py` | `parse_experiment_notification()` | ✅ Done | Regex-validated: requires 8-digit date + 3-digit seq after _run_; returns None on any malformed input |
| `listener.py` | `listen_async()` | ✅ Done | asyncpg NOTIFY/LISTEN with retry loop; waits on shutdown token OR connection termination — dropped connections now trigger reconnect |
| `listener.py` | `listen_async_mock()` | ✅ Done | Fires hardcoded payload, sleeps indefinitely |

### `src/gate/`
| File | Function | Status | Notes |
|---|---|---|---|
| `gate.py` | `checksum_check()` | ✅ Done | Delegates to compute_checksum from registrar |
| `gate.py` | `subset_check()` | 🔲 Stub | Phase 3 |
| `gate.py` | `run_gate()` | ✅ Done | Returns (bool, status); no_gold_standard / pass. DB is source of truth — checksum_check not called here |

### `src/orchestrator/`
| File | Function | Status | Notes |
|---|---|---|---|
| `orchestrator.py` | `load_manifest()` | ✅ Done | Constructs path from run_id + config; raises FileNotFoundError if missing |
| `orchestrator.py` | `find_result_folder()` | ✅ Done | Globs for {exp_id}_{run_id}_* under results_dir; raises on 0 or >1 matches |
| `orchestrator.py` | `verify_run()` | ✅ Done | Full flow: gate → compare → persist → report |
| `watcher.py` | `ReportDataDeletionHandler` | ✅ Done | watchdog event handler; bridges OS thread to asyncio via run_coroutine_threadsafe; fired guard prevents double-trigger |
| `watcher.py` | `wait_for_e_drive_deletion()` | ✅ Done | Starts observer first, then pre-checks — closes race window; timeout from config; uses get_running_loop(); observer.join() via asyncio.to_thread |
| `watcher.py` | `watch_and_confirm()` | ✅ Done | Dispatches to on_confirmed / on_timeout callbacks |

### `src/comparator/`
| File | Function | Status | Notes |
|---|---|---|---|
| `comparator.py` | `compare_experiment()` | ✅ Done | Dispatches to registry; raises ValueError on unknown type |
| `registry.py` | `COMPARISON_REGISTRY` | ✅ Done | Maps type strings to strategy handlers; count_tolerance wired |
| `strategies/__init__.py` | — | ✅ Done | Package marker |
| `strategies/count_tolerance.py` | `compare_sample()` | ✅ Done | Zero/zero → pass (deviation 0.0); zero expected, non-zero actual → fail; result includes comparison_type and metric fields |
| `strategies/count_tolerance.py` | `run_count_tolerance()` | ✅ Done | Iterates params["columns"]; one result per (sample, column) |

### `src/llm/`
| File | Function | Status | Notes |
|---|---|---|---|
| `analyst.py` | `build_prompt()` | ⬜ Not started | |
| `analyst.py` | `generate_narrative()` | ⬜ Not started | |

### `src/reporter/`
| File | Function | Status | Notes |
|---|---|---|---|
| `reporter.py` | `determine_experiment_verdict()` | ✅ Done | Any sample fail → experiment fail |
| `reporter.py` | `determine_run_verdict()` | ✅ Done | Now reads and validates build_verdict_policy fields; raises ValueError on unsupported rule or on_exploratory_failure values |
| `reporter.py` | `write_report()` | ✅ Done | Writes detail_report.csv + summary_report.csv; stores JSON blob in reports table |

### `src/main.py`
| Function | Status | Notes |
|---|---|---|
| `load_config()` | ✅ Done | |
| `init()` | ✅ Done | |
| `register()` | ✅ Done | |
| `run()` | ✅ Done | |
| `run_service()` | ✅ Done | Async loop — spawns watch_and_confirm task per experiment; verify_run fires via asyncio.to_thread when confirmed_ready ⊇ expected; on_timeout() cleans up run state |

---

## Schema status

| Change | Status | Notes |
|---|---|---|
| Initial schema from DDL | ✅ Applied | |
| Added `primary_metric`, `primary_metric_value` to `gold_standard_samples` | ✅ Applied | MVP scaffolding — to be dropped once full JSON comparison implemented |
| Added `full_metrics` JSON column to `gold_standard_samples` | ✅ Applied | |
| Added `primary_metric`, `actual_value`, `expected_value`, `deviation_percent` to `sample_results` | 🔁 Superseded | Replaced by normalised schema below |
| Added `full_actual_metrics`, `full_expected_metrics` JSON columns to `sample_results` | 🔁 Superseded | Replaced by normalised schema below |
| Normalised `sample_results` — one row per (sample, metric); added `metric`, `comparison_type`, `notes`; `deviation_percent` now nullable | ✅ Applied (DDL) | Requires DB re-init and re-registration — see session 7 notes |
| Added `report_json TEXT NOT NULL DEFAULT ''` to `reports` | ✅ Applied (DDL) | Stores structured JSON for future HTML rendering (ADR-017) |
| Drop `primary_metric`, `primary_metric_value` scaffold columns from `gold_standard_samples` | ✅ Applied (DDL) | registrar.py updated — PRIMARY_METRIC constant removed, sample records now store full_metrics JSON only |
| `sample_results.actual_value` made nullable | ✅ Applied (DDL) | Missing-sample rows now stored as auditable fail records; orchestrator no longer skips them |
| `experiment_results.gs_exp_version_id` made nullable | ✅ Applied (DDL) | Gate failures (no_gold_standard) now get a DB record with NULL FK |
| `experiment_results.pre_verify_status` CHECK expanded | ✅ Applied (DDL) | Added `no_gold_standard` and `result_not_found` as valid statuses |

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
| manifest gold_standard_checksum field is redundant — gate reads checksum from DB. Field can be removed from manifest schema in a future cleanup. | 🔲 Future |
| PRIMARY_METRIC constant in registrar.py — removed (session 7) | ✅ Resolved |
| Results folder — currently manually maintained with CSVs dropped in directly. Future implementation requires password-protected unzip step before CSVs are accessible. | 🔲 Future |

---

## Key architectural decisions (recent)

- **Listener changed from polling to PostgreSQL NOTIFY/LISTEN** (ADR-012 supersedes ADR-004)
- **Mock listener added for dev** — controlled by `listener.use_mock` config flag (ADR-013)
- **Experiment folder naming** — `{exp_id}_{run_id}_{timestamp}`, test harness does rename at runtime (ADR-014)
- **run_id is a coordination mechanism only** — base `exp_id` remains the stable longitudinal key in verification DB
- **E: drive deletion watch as pipeline completion signal** — NOTIFY fires before F: copy is complete; watching E: for folder deletion is the safe trigger (ADR-019)

---

## Build phases

### Phase 1 — Foundation
- [x] Project structure and skeleton
- [x] Virtual environment and dependencies
- [x] Database initialisation
- [x] database-schema.md updated to match current DDL
- [x] Gold standard registration tool
- [x] models.py gold standard insert functions

### Phase 2 — Happy path end to end ✅ COMPLETE
- [x] models.py remaining insert functions
- [x] Listener — mock + real (asyncpg)
- [x] Orchestrator (manifest loading, folder lookup, flow coordination)
- [x] Pre-verification gate (checksum check)
- [x] Comparator (per-sample comparison)
- [x] Reporter (detail + summary CSV, JSON blob in DB)
- [x] main.py run() wired to asyncio event loop
- [x] E: drive deletion watcher (ADR-019) — race condition safe, per-experiment concurrent tasks

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

PR review hardening — async correctness + docs (session 11):
- verify_run now owns its DB connection (created inside asyncio.to_thread worker) — fixes SQLite check_same_thread error
- conn removed from _watch_experiment signature and asyncio.create_task call — verify_run no longer needs it passed in
- run_service startup connection scoped tightly: open, query get_all_processed_run_ids, close immediately
- smoke_test.py: conn closed before verify_run call (cleanup and verification now use separate connections)
- on_timeout() now cleans up in_progress/confirmed_ready/manifests; guarded so only first timeout per run triggers cleanup
- get_event_loop() → get_running_loop() in watcher.py — explicit and deprecation-safe
- observer.join() moved to asyncio.to_thread — no longer blocks event loop during observer shutdown
- parse_experiment_notification rewritten with compiled regex (_NOTIFICATION_RE) — validates 8-digit date + 3-digit seq; malformed payloads return None reliably
- asyncio-reference.md updated: verify_run note corrected (sync def, not async def); parse_experiment_notification examples updated with None guard; get_event_loop → get_running_loop throughout; verify_run call pattern updated to asyncio.to_thread in all examples

E: drive watcher + MVP feature complete (session 10):
- watcher.py created: ReportDataDeletionHandler, wait_for_e_drive_deletion, watch_and_confirm
- Race condition handled: observer starts before pre-check — no window where a deletion can be missed
- run_service() redesigned: confirmed_ready dict tracks F: copy status per experiment; verify_run fires only when all experiments confirmed; asyncio.to_thread keeps event loop unblocked during sync verification
- parse_experiment_notification() now returns None on malformed input — handle_notification guards against it
- watchdog==6.0.0 added to requirements.txt
- config.yaml and local_config.yaml: duplicate results_dir keys removed; e_drive_deletion_timeout_seconds: 600 added to verification block
- local_config.yaml to be retired when dev machine is set up as production replica (no more mock listener needed)
- MVP is feature complete — dev machine setup with pipeline DB is the next prerequisite before end-to-end live testing

PR hardening — correctness and robustness fixes (session 9):
- actual_value made nullable in sample_results — missing-sample rows now persisted as auditable fail records (removed orchestrator skip guard)
- gs_exp_version_id made nullable in experiment_results — gate failures now get a DB record (verdict: aborted) instead of being silently dropped
- pre_verify_status CHECK expanded: no_gold_standard and result_not_found added
- Experiments with comparison=None now always get an experiment_results row; sample inserts remain guarded
- listen_async() reconnect fixed: asyncio.wait on shutdown token AND conn_terminated event — dropped connections now trigger retry loop instead of leaving service idle
- generated_at in reporter changed from datetime.utcnow() to datetime.now(timezone.utc) — consistent with rest of codebase
- determine_run_verdict() now reads and validates build_verdict_policy fields; raises ValueError on unsupported values
- count_tolerance zero/zero case fixed: both expected and actual zero → pass with deviation_percent=0.0 (was incorrectly failing)
- Orchestrator try/except split: find_result_folder guarded separately from compare_experiment — comparator ValueErrors now propagate as real failures instead of being swallowed as result_not_found
- DB re-init required to pick up sample_results and experiment_results schema changes

Smoke test end-to-end confirmed (session 8):
- Phase 2 happy path smoke test passing end-to-end — reports written, DB populated correctly
- run_gate() signature corrected: now accepts experiment_id: str directly (was experiment: dict)
- Root cause of blank reports: experiment_id typo in manifest (T087 vs T078) — manifests must match registered experiment_ids exactly
- All diagnostic prints removed

Reporter + orchestrator + schema redesign (session 7):
- Reporter implemented: detail_report.csv (one row per sample/metric/experiment), summary_report.csv (one row per feature_set/comparison_type/metric), JSON blob stored in reports table
- Orchestrator fully implemented: find_result_folder globs for {exp_id}_{run_id}_* under results_dir; verify_run orchestrates gate → compare → DB inserts → write_report
- verify_run wired into main.py run_service — Phase 2 happy path is now end-to-end
- sample_results schema redesigned: normalised to one row per (sample, metric); added metric, comparison_type, notes columns; removed flat-value scaffolding and JSON blob columns (ADR-017)
- report_json added to reports table (ADR-017)
- DB must be re-initialised and gold standard re-registered before smoke testing (schema changed)
- gold_standard_samples scaffold columns (primary_metric, primary_metric_value) still present — cleanup tracked in schema status table above

Import audit (session 6):
- All internal imports across `src/` now use the full `src.` prefix (required for smoke_test.py to resolve modules from project root)
- Files updated: gate.py, comparator.py, registry.py, count_tolerance.py, registrar.py, main.py
- Smoke test confirmed working end-to-end

Listener redesign (session 4):
- Pipeline DB is PostgreSQL with existing NOTIFY triggers on Reports and Workbooks tables
- reports_table_changes channel fires on INSERT/UPDATE/DELETE with ExperimentId in payload
- asyncpg added to requirements.txt
- Full async architecture required — main.py run() uses asyncio.run()
- Mock listener unblocks development on personal machine without pipeline DB access
