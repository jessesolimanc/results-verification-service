# Project status

Quick reference for current implementation state. Update this file at the end of every development session.

Last updated: 2026-09-28 (session 14)
Current phase: Phase 3 hardening (complete) moving into entry-point automation — GitHub Actions trigger added (ADR-023)

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
| `listener.py` | `listen_async()` | ✅ Done | asyncpg NOTIFY/LISTEN with retry loop; waits on shutdown token OR connection termination — dropped connections now trigger reconnect. No longer does experiment_id/run_id parsing — see ADR-022 |
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
| `orchestrator.py` | `find_result_folder()` | ✅ Done | Now takes the pipeline's own timestamped `name` (from the NOTIFY payload) rather than reconstructing {exp_id}_{run_id}_*; globs `{name}*` under results_dir. Raises on 0 or >1 matches (session 14, ADR-022) |
| `orchestrator.py` | `verify_run()` | ✅ Done | Full flow: gate → compare → persist → report. Takes `experiment_names: dict` (experiment_id → pipeline name), collected live from notifications, to pass through to find_result_folder. Now also takes an explicit `manifest_record_path` argument (session 14, PR review) — caller passes the manifest's post-archive destination so `runs.manifest_path` never records a path that's about to stop existing |
| `manifest_watcher.py` | `watch_manifests_dir()` | ✅ Done | Watches manifests_dir for new context_manifest_*.json files, observer-first pattern (same as ADR-019's watcher.py); registers each manifest's experiments as "expected" the moment it appears — see ADR-022. Now also handles `on_moved` (atomic rename hand-off), not just `on_created`, and accepts an optional `ready_event` set once the startup catch-up scan finishes (session 14, PR review) |
| `watcher.py` | `ReportDataDeletionHandler` | ✅ Done | watchdog event handler; bridges OS thread to asyncio via run_coroutine_threadsafe; fired guard prevents double-trigger. Now matches on the pipeline's `name` (session 14, PR review) — previously matched `{exp_id}_{run_id}_*`, which was almost always a no-op post-ADR-022 |
| `watcher.py` | `wait_for_e_drive_deletion()` | ✅ Done | Starts observer first, then pre-checks — closes race window; timeout from config; uses get_running_loop(); observer.join() via asyncio.to_thread. Signature now takes `name` (pipeline's timestamped identifier), exp_id/run_id kept only for log labels |
| `watcher.py` | `watch_and_confirm()` | ✅ Done | Dispatches to on_confirmed / on_timeout callbacks; signature updated to take `name` |

### `src/comparator/`
| File | Function | Status | Notes |
|---|---|---|---|
| `comparator.py` | `compare_experiment()` | ✅ Done | Dispatches to registry; raises ValueError on unknown type |
| `registry.py` | `COMPARISON_REGISTRY` | ✅ Done | Maps type strings to strategy handlers; count_tolerance wired |
| `strategies/__init__.py` | — | ✅ Done | Package marker |
| `strategies/count_tolerance.py` | `compare_sample()` | ✅ Done | Zero/zero → pass (deviation 0.0); zero expected, non-zero actual → fail; result includes comparison_type and metric fields |
| `strategies/count_tolerance.py` | `run_count_tolerance()` | ✅ Done | Iterates params["columns"]; one result per (sample, column) |
| `strategies/hybrid_tolerance.py` | `compare_sample_hybrid()` | ✅ Done | expected_value < count_threshold -> absolute tolerance; else percent tolerance |
| `strategies/hybrid_tolerance.py` | `run_hybrid_tolerance()` | ✅ Done | Same shape as run_count_tolerance; registered in COMPARISON_REGISTRY (session 12) |

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
| `run_service()` | ✅ Done | Async loop — runs watch_manifests_dir() concurrently alongside the Postgres listener (ADR-022), now gated on a `manifest_watcher_ready` event so the listener can't start consuming before the initial manifest catch-up scan completes (session 14, PR review). Builds expected_experiment_to_run {experiment_id: run_id} from registered manifests, rejecting (not overwriting) a manifest that collides with an already-pending run; handle_new_manifest() retries its JSON read with backoff to tolerate partial writes. handle_notification() is a plain dict lookup, no parsing. Spawns watch_and_confirm task per experiment; verify_run fires via asyncio.to_thread when confirmed_ready ⊇ expected, now wrapped in try/except — on failure the manifest is archived to a new failed/ subfolder and run state is freed instead of crashing the service. processed_dir/timed_out_dir/failed_dir all created with parents=True |

### `entry_point/` (session 14, PR-reviewed session 15)
| File | Function | Status | Notes |
|---|---|---|---|
| `manifest_template.json` | — | ✅ Done | Committed stable `build_verdict_policy` + `experiments` (all 3 registered experiments) — the parts of a manifest that don't change run to run. Editing this file is how an experiment gets added/changed/removed (ADR-023) |
| `stamp_manifest_for_run.py` | `load_config()` | ✅ Done | Standalone copy of `src.main.load_config()` — deliberately not imported, to avoid pulling in asyncpg/watchdog just to read a path |
| `stamp_manifest_for_run.py` | `next_run_id()` | ✅ Done | Scans manifests_dir + processed/timed_out/failed for today's highest sequence number; tested against collisions and cross-folder scanning |
| `stamp_manifest_for_run.py` | `main()` | ✅ Done | CLI: `--pipeline-build` (required), `--scenario`, `--run-type`. Refuses to stamp while an unarchived manifest exists at manifests_dir's top level — glob fixed session 15 (PR review) to match `manifest_watcher.py`'s `context_manifest_*.json` exactly, not just `*run_*` names, closing a gap where a stale non-run-prefixed file could slip past the check. Writes `GITHUB_OUTPUT` (run_id, manifest_path) when running under Actions |
| `.github/workflows/trigger_regression_run.yml` | — | ✅ Done | `workflow_dispatch` on `[self-hosted, pcr-regression]`. Stamps a manifest, then runs the already-installed test harness exe with a 3hr timeout cap (guards the harness's own `Console.Read()`-on-fatal-exception hang, not fixed here). Fire-and-forget — does not wait for verification. Session 15 (PR review): dispatch inputs now passed through job-level `env:` and read via `$env:...` instead of being interpolated as `${{ inputs.* }}` text directly into PowerShell — the latter was a real command-injection path on the self-hosted runner. Summary step now branches on the stamp/harness steps' actual outcomes instead of always printing success text. **Not yet exercised for real: no self-hosted runner is registered on the regression machine yet, and `PCR_MANIFESTS_DIR`/`PCR_TEST_HARNESS_EXE_PATH` repo variables are not yet set.** |

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
| Pipeline DB schema — reports_table_changes NOTIFY channel confirmed. **Correction (session 14):** ExperimentId is a bare experiment_id, NOT {exp_id}_{run_id}_{timestamp} as originally documented — that assumption was never true in either Imaging or Reanalysis mode and caused a full run to silently fail verification. See ADR-022. | ✅ Resolved (corrected) |
| Workbook generator — automates workbook stamping with run_id. Out of scope for MVP, done manually. | 🔲 Future |
| manifest gold_standard_checksum field is redundant — gate reads checksum from DB. Removed from manifest-schema.md and from the run_20260924_001 manifest (session 12); gold_standard_ref removed alongside it, same reasoning. | ✅ Resolved |
| PRIMARY_METRIC constant in registrar.py — removed (session 7) | ✅ Resolved |
| Results folder — currently manually maintained with CSVs dropped in directly. Future implementation requires password-protected unzip step before CSVs are accessible. | 🔲 Future |
| count_tolerance strategy only supports percent deviation — a standalone absolute-difference mode is needed for near-zero-count comparisons (e.g. linkage combos). Near-term gap, not yet implemented. | 🔲 Unresolved |
| Comparator scope extension (sample vs aggregate strategies, for linkage hybrid tolerance / dynamic range trend / grouped-sample comparisons) — shaped in ADR-021. Deferred until after data team philosophy discussion. | 🔲 Future |
| Graceful crash isolation — an unhandled exception inside a single run's verification flow (or the notification/manifest handlers) currently propagates up and can take down the whole service, not just that run. Needs try/except boundaries around each notification handler and each _watch_experiment task. Observed session 14. **Fixed (session 14, PR review):** `on_confirmed()` now wraps `verify_run()` in try/except, archiving to a new `manifests_dir/failed/` on exception and freeing run state. Notification/manifest handlers themselves still have no equivalent boundary — a malformed payload or manifest could still raise uncaught; narrower in practice since both are guarded by their own try/except-like validation already, but worth a follow-up pass. | ✅ Resolved (partially — see note) |
| Test harness (`Countable.PCR`) never archives a processed manifest — `LoadManifests()` globs and reprocesses every context_manifest_*.json in the folder on every invocation, indefinitely. Separate from the verification-service-side archiving added in ADR-022; needs a harness-side fix (e.g. move to a processed/ subfolder, or accept a single `--manifest` path from the entry point). Found session 14, not yet fixed. | 🔲 Future |
| Entry point / self-hosted GitHub Actions runner design — stamping a manifest with per-run metadata (build id, run id, timestamp) and triggering the harness. Designed and implemented session 14 (ADR-023). Not yet live: needs a self-hosted runner registered on the regression machine (labels `[self-hosted, pcr-regression]`) and the `PCR_MANIFESTS_DIR` / `PCR_TEST_HARNESS_EXE_PATH` repo variables set before first real dispatch. | ✅ Resolved (implemented, not yet deployed) |
| Automating build → install (currently both manual, ahead of the new GitHub Actions trigger) — out of scope for ADR-023; touches code-signing, MSI install, and the pipeline's own service lifecycle. | 🔲 Future |
| `pipeline_build` on the manifest is a free-text label the person dispatching the workflow types in — nothing checks it against what's actually installed on the regression machine. A wrong value silently produces a misleadingly-labeled but otherwise normal run. | 🔲 Unresolved |

---

## Key architectural decisions (recent)

- **Listener changed from polling to PostgreSQL NOTIFY/LISTEN** (ADR-012 supersedes ADR-004)
- **Mock listener added for dev** — controlled by `listener.use_mock` config flag (ADR-013)
- ~~**Experiment folder naming** — `{exp_id}_{run_id}_{timestamp}`, test harness does rename at runtime (ADR-014)~~ — **superseded (ADR-022, session 14):** the harness never actually performs this stamping in either run mode; the naming convention and its parsing are removed
- **Explicit manifest hand-off replaces run_id stamping** — the service watches manifests_dir directly and registers expected experiments the moment a manifest appears, rather than inferring run_id from a pipeline-supplied string (ADR-022)
- **E: drive deletion watch as pipeline completion signal** — NOTIFY fires before F: copy is complete; watching E: for folder deletion is the safe trigger (ADR-019); now matches on the pipeline's `name` field instead of the never-implemented `{exp_id}_{run_id}_*` convention (ADR-022 addendum, session 14)
- **Per-run failures no longer crash the service** — `verify_run()` failures are caught at the `on_confirmed()` boundary and archived to `failed/`, so one bad run doesn't take down in-flight or future runs (ADR-022 addendum, session 14)
- **GitHub Actions `workflow_dispatch` as the manual run trigger** — a self-hosted runner on the regression machine stamps a manifest from a committed template and starts the test harness; fire-and-forget, no build/install automation, no waiting on verification (ADR-023)

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

PR review hardening on the ADR-023 GitHub Actions trigger (session 15):
- 3 Copilot review comments on the trigger_regression_run.yml PR, all confirmed accurate by direct inspection before fixing:
  1. Command injection: dispatch inputs (`pipeline_build`, `scenario`, `run_type`) were interpolated as `${{ inputs.* }}` directly into two PowerShell `run:` blocks (the stamp step and the summary step) — GitHub substitutes `${{ }}` expressions into the script's text before PowerShell parses it, so a crafted input value could break out of its quoted argument and execute arbitrary commands on the self-hosted runner. Fixed with a job-level `env:` block (`PIPELINE_BUILD`/`SCENARIO`/`RUN_TYPE`) and `$env:...` reads instead — a real env var read at runtime, not a script-text splice.
  2. `stamp_manifest_for_run.py`'s collision safety check globbed `context_manifest_run_*.json`, narrower than `manifest_watcher.py`'s actual `context_manifest_*.json` match — a stale file like `context_manifest_old.json` would defeat the safety check while still being exactly what it's meant to catch. Fixed to use the identical glob; re-verified against a scratch manifests_dir with that exact filename.
  3. The job Summary step runs `if: always()` but was unconditionally printing success text ("Regression run triggered", "harness process has exited") even when stamping failed or the harness step failed/timed out — the opposite of useful during the failure modes a job summary exists for. Fixed by giving the harness step an `id` and branching the summary text on `steps.stamp.outcome`/`steps.harness.outcome`.
- Full detail in ADR-023's new Addendum section.

GitHub Actions entry point (ADR-023, session 14 continued):
- Read the two existing Countable.PCR build workflows (Build_Official_Release.yml, Build_Unofficial_Release.yml) and Bump_Build_Number.yml for house conventions before writing the new one — both run on GitHub-hosted `windows-latest`, since building/signing needs no special hardware. The new regression trigger differs: it must run on the regression machine itself (`[self-hosted, pcr-regression]`), since only that machine has the installed pipeline and the E:/F: drives.
- Read `Countable.Pcr.TestHarness/Program.cs` directly to confirm the actual invocation contract rather than guessing: it reads `COUNTABLE_PCR_REGRESSION_TEST_MANIFEST_PATH` (a folder, not a single file — confirms `LoadManifests()`'s whole-folder glob), restarts the `CountableAnalysisService` Windows service itself before running, and on any unhandled exception calls `Console.Read()` — which would block forever on an unattended runner. Not fixed (harness changes are out of scope this pass), but the harness step's `timeout-minutes: 180` exists specifically to bound that failure mode.
- New `entry_point/` directory: `manifest_template.json` (committed stable `build_verdict_policy` + `experiments`, copied from the real, currently-registered 3-experiment manifest) and `stamp_manifest_for_run.py` (stamps the `run` block, computes `run_id` by scanning manifests_dir + processed/timed_out/failed for today's highest sequence number, refuses to run while an unarchived manifest already exists). Tested standalone against a scratch config before wiring into the workflow: verified the collision refusal, the sequence bump across archive folders, and `GITHUB_ACTOR`/`GITHUB_RUN_ID`/`GITHUB_OUTPUT` handling.
- New `.github/workflows/trigger_regression_run.yml`: `workflow_dispatch` with `pipeline_build` (required text), `scenario` and `run_type` (both optional) inputs; checks out with `clean: false` (this workspace persists on the regression machine between dispatches — the default `git clean -ffdx` would delete the gitignored `config/local_config.yaml` and `.venv` every run, which would have been a nasty one to debug later); ensures a venv; runs the stamping script; runs the already-installed harness exe with the manifests folder as an env var; fire-and-forget beyond that — does not wait for or report a verification verdict.
- Found in passing: `pyyaml` was an undeclared dependency — both `main.py` and the new stamping script import it, but it was never in `requirements.txt` (only present incidentally in the existing dev venv). Added.
- Not yet deployed: no self-hosted runner is registered on the regression machine yet, and the workflow's two repo variables (`PCR_MANIFESTS_DIR`, `PCR_TEST_HARNESS_EXE_PATH`) haven't been set. First real dispatch is blocked on both.
- Deliberately not addressed here, tracked as open questions above: automating build→install, and validating `pipeline_build` against what's actually installed.

PR review hardening on the ADR-022 redesign (session 14 continued):
- A GitHub Copilot review of the ADR-022 PR surfaced 8 comments; all 8 were independently verified against the actual code before fixing (two were initially unclear whether they were real issues — both confirmed real: the `watcher.py` E: drive match and the `runs.manifest_path` staleness, below).
- `watcher.py`'s `ReportDataDeletionHandler` / `wait_for_e_drive_deletion` / `watch_and_confirm` changed to match on the pipeline's own timestamped `name` instead of `{exp_id}_{run_id}_*` — the latter almost always matched zero folders post-ADR-022 (the harness never stamps run_id), silently skipping the real wait for the F: copy on nearly every run. This was the more serious of the two comments the fix's author was initially unsure about.
- `on_confirmed()` in `main.py` now wraps `verify_run()` in try/except: on exception, the manifest is archived to a new `manifests_dir/failed/` subfolder and run state is freed via `_archive()`, instead of the exception propagating uncaught and crashing the whole service (this is the exact crash observed earlier in session 14).
- `verify_run()` now takes an explicit `manifest_record_path` argument instead of recomputing the manifest's path from `manifests_dir` + `run_id` — the old computation went stale the moment `_archive()` moved the file into `processed/`, so `runs.manifest_path` pointed at a location that no longer existed. The caller now passes the path the manifest is about to be archived to.
- `watch_manifests_dir()` gained an optional `ready_event`, set once its startup catch-up scan finishes; `run_service()` now awaits it before starting the NOTIFY listener, closing a startup race where a manifest already on disk could be missed if a notification for it arrived first.
- `handle_new_manifest()`'s collision path now skips registering a manifest whose experiments collide with an already-pending run, instead of warning and then overwriting the existing `expected_experiment_to_run` mapping anyway.
- `manifest_watcher.py`'s `ManifestCreatedHandler` now also handles `on_moved` (an atomic rename into the directory fires this, not `on_created`), and `handle_new_manifest()` retries its JSON read with backoff (5 attempts, ~3s total) to tolerate a file being read mid-write.
- `scratch/smoke_test.py` updated to pass `experiment_names` and `manifest_record_path` to `verify_run()`, matching the signature changes above.
- Full detail in ADR-022's new Addendum section. One open item: the `watcher.py` name-based match assumes the E: drive folder is named identically to the F: result folder (both by the pipeline's `name` field) — consistent with how `find_result_folder()` already works on F:, but not yet directly confirmed against a live E: drive folder.
- Not addressed this pass: the notification and manifest handlers themselves still lack their own exception boundaries (only the `verify_run()` call site does) — a malformed payload reaching deep enough to raise would still be uncaught. Narrower risk in practice since both already validate/guard their inputs, but worth a follow-up pass.

Silent listener bug, run-correlation redesign, result file naming (session 14):
- Diagnosed a full weekend Reanalysis-mode run (3 experiments, real pipeline writes and `Reports` trigger all confirmed healthy) that produced zero verification output with no error anywhere. Root cause: `parse_experiment_notification()` (ADR-014) expected `experimentId` to be `{exp_id}_run_{date}_{seq}_...`; the real pipeline sends a bare experiment_id in every case. The regex never matched, returned None, and `handle_notification()` silently returned — no log, no error. Confirmed by manually firing realistic `pg_notify()` payloads against the running service and watching it react to garbage (loud JSON error) vs. a real-shaped payload (total silence).
- Investigated the harness (`Countable.PCR`) directly: neither `AcquisitionWorkflow.ExperimentName` nor `ReanalysisWorkflow.ExperimentName` ever stamps run_id into the name — both derive it unmodified from the workbook's own `RunInfo.ExperimentId`. The run_id-stamping behavior ADR-014 documented was never implemented in either run mode; `Report.cs`'s own doc comment confirms `ExperimentId` is "assigned by IAP," an external system this codebase doesn't control.
- Also found: `TestRunner.LoadManifests()` globs and reprocesses every `context_manifest_*.json` in the folder on every invocation — nothing ever archives one. Not yet fixed on the harness side; tracked as an open design question.
- Redesigned run correlation around an explicit hand-off (ADR-022, supersedes ADR-014): new `src/orchestrator/manifest_watcher.py` watches manifests_dir (same observer-first pattern as ADR-019) and registers every experiment a manifest declares as "expected" the instant the file appears, building `expected_experiment_to_run: {experiment_id: run_id}`. `handle_notification()` is now a plain dict lookup; a miss prints a visible warning instead of returning silently. `parse_experiment_notification()` and its regex are deleted from `listener.py`.
- Manifests are now archived: moved to `manifests_dir/processed/` on successful verification or `manifests_dir/timed_out/` if the E: drive watch times out, via a new `_archive()` helper in `run_service()`.
- Second bug found immediately after, on the same replayed weekend run: `find_result_folder()` reconstructed `{exp_id}_{run_id}_*` to locate the result folder, but the pipeline actually names result folders after its own timestamped `name` (e.g. `JS221N_serial_titration_PSF_260925_1416`), which has no relationship to the verification service's run_id. Fixed by capturing the `name` field from each live notification (`experiment_names: {run_id: {experiment_id: name}}` in `run_service()`) and passing it through `verify_run()` into `find_result_folder(name, config)`.
- Third issue, specific to `MP47b_Adverum_02` (the linkage experiment): its result folder contains a differently-named output CSV (`*CountableLinkageSummary_beta.csv`) than the previously-hardcoded `*CountableDataSummary.csv`. Added an optional `result_file_suffix` field to the manifest schema (documented in manifest-schema.md) — `find_result_folder`'s caller now globs on `experiment.get("result_file_suffix", "CountableDataSummary.csv")`. Set on `MP47b_Adverum_02` in `context_manifest_run_20260924_001.json`.
- An unhandled exception during this session's live debugging crashed the running service outright — graceful per-run error isolation (catching inside each notification/task handler rather than letting it propagate to the event loop) is a known gap, tracked above as an open design question, not fixed this session.
- The stuck weekend manifest (`run_20260924_001`) was recovered in place: restarting the service after these fixes re-registers it via `manifest_watcher.py`'s startup catch-up scan, and replaying the three experiments' real NOTIFY payloads (from their actual `Reports` rows) lets the run complete without re-running the harness.

Hybrid tolerance strategy + ADR-021 (session 12):
- Added src/comparator/strategies/hybrid_tolerance.py: run_hybrid_tolerance()/compare_sample_hybrid() — same sample-scope shape as count_tolerance, but expected_value < count_threshold uses absolute tolerance instead of percent (percent deviation is meaningless near zero, e.g. low-count linkage combos)
- Registered as "hybrid_tolerance" in COMPARISON_REGISTRY — additive, count_tolerance untouched
- Zero-expected-value case now falls out naturally from the absolute branch — no special-casing needed, unlike count_tolerance's explicit zero/zero guard
- deviation_percent is None on absolute-mode rows; the absolute deviation and which mode was used are recorded in the notes field instead — no schema change needed, sample_results used as-is
- tests/test_hybrid_tolerance.py added — 9 cases covering percent mode, absolute mode, the threshold boundary, zero-value edge cases, and missing-sample handling; verified passing (pytest not runnable from this session's shell — verified by executing the test functions directly against a stdlib-only Python)
- ADR-021 drafted (Proposed, rough shaping — not required for current OKR scope): generalizes this pattern as "sample-scope" strategies vs a future "aggregate-scope" family (grouped-sample and whole-experiment trend comparisons, e.g. dynamic range linearity/%CV) for later, once linkage/dynamic-range criteria are defined with the data team
- Two gold standards pending registration for the new build regression baseline: T078_run3 (baseline_algo_performance, re-registration — will retire the existing May 18 v1) and MP47b_Adverum_02 (new registration; likely the linkage-feature experiment based on its accompanying CountableLinkageSummary_beta.csv output) — feature_set/classification for MP47b_Adverum_02 still TBD

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
