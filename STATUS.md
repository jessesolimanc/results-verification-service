# Project status

Quick reference for current implementation state. Update this file at the end of every development session.

Last updated: 2026-05-12 (session 2)
Current phase: Phase 1 — Foundation

---

## Implementation status

### `src/database/`
| File | Function | Status | Notes |
|---|---|---|---|
| `db.py` | `get_connection()` | ✅ Done | |
| `db.py` | `initialise_database()` | ✅ Done | Wired to `--init` in main.py |
| `models.py` | `insert_gs_exp_version()` | ⬜ Not started | |
| `models.py` | `insert_gs_sample()` | ⬜ Not started | |
| `models.py` | `get_active_gs_version()` | ⬜ Not started | |
| `models.py` | `retire_gs_version()` | ⬜ Not started | |
| `models.py` | `insert_run()` | ⬜ Not started | |
| `models.py` | `get_unprocessed_runs()` | ⬜ Not started | |
| `models.py` | `insert_experiment_result()` | ⬜ Not started | |
| `models.py` | `insert_sample_result()` | ⬜ Not started | |
| `models.py` | `insert_report()` | ⬜ Not started | |

### `src/registration/`
| File | Function | Status | Notes |
|---|---|---|---|
| `registrar.py` | `compute_checksum()` | ⬜ Not started | |
| `registrar.py` | `read_gold_standard_csv()` | ⬜ Not started | |
| `registrar.py` | `register_gold_standard()` | ⬜ Not started | |

### `src/listener/`
| File | Function | Status | Notes |
|---|---|---|---|
| `listener.py` | `get_completed_runs()` | ⬜ Not started | |
| `listener.py` | `start_listener()` | ⬜ Not started | |

### `src/gate/`
| File | Function | Status | Notes |
|---|---|---|---|
| `gate.py` | `checksum_check()` | ⬜ Not started | |
| `gate.py` | `subset_check()` | ⬜ Not started | |
| `gate.py` | `run_gate()` | ⬜ Not started | |

### `src/orchestrator/`
| File | Function | Status | Notes |
|---|---|---|---|
| `orchestrator.py` | `load_manifest()` | ⬜ Not started | |
| `orchestrator.py` | `verify_run()` | ⬜ Not started | |

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
| `register()` | ⬜ Not started | |
| `run()` | ⬜ Not started | |

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
| Primary metric column name per experiment type — how does registrar know which column to use? | 🔲 Unresolved |

---

## Build phases

### Phase 1 — Foundation
- [x] Project structure and skeleton
- [x] Virtual environment and dependencies
- [x] Database initialisation
- [x] database-schema.md updated to match current DDL
- [ ] Gold standard registration tool
- [ ] models.py insert functions

### Phase 2 — Happy path end to end
- [ ] Listener (polling loop)
- [ ] Orchestrator (manifest loading + flow coordination)
- [ ] Pre-verification gate (checksum check)
- [ ] Comparator (per-sample comparison)
- [ ] Reporter (basic structured report, no LLM)

### Phase 3 — Harden and complete
- [ ] Subset validity check in gate
- [ ] All 5 experiments wired up
- [ ] LLM narrative module
- [ ] Edge case handling (aborted runs, missing manifests)

### Phase 4 — Observability
- [ ] Longitudinal queries and trend detection
- [ ] Run-level summary reports
- [ ] Windows Service wrapper

---

## Notes

_Use this section for anything that doesn't fit above — unexpected decisions made during implementation, things to discuss next session, gotchas discovered, etc._
