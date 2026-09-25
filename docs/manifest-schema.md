# Run context manifest — schema reference

## Purpose

The run context manifest is a JSON file that is the contract between the test harness and the results verification service. Everything the verification service needs to verify a run is either contained in or referenced by the manifest.

The manifest carries rules and pointers — not raw expected values. Gold standard data lives entirely in the verification database, keyed by `experiment_id`. The manifest never points at a gold standard file directly (see the amendment note under "Experiment fields" below).

---

## File location and naming

Manifests are stored in a watched folder, shared between the test harness and the verification service:

```
manifests/
  context_manifest_run_20260924_001.json
  context_manifest_run_20260925_001.json
```

Naming convention: `context_manifest_{run_id}.json`, where `run_id` matches the `run.run_id` field inside the manifest (format `run_YYYYMMDD_NNN`, NNN a zero-padded sequence number). The verification service locates a manifest by constructing this exact path from the `run_id` in the database event — no searching required (see `orchestrator.load_manifest()`).

---

## Top-level structure

```json
{
  "run": { ... },
  "build_verdict_policy": { ... },
  "experiments": [ ... ]
}
```

---

## `run` object

Metadata identifying the run.

| Field | Type | Description |
|---|---|---|
| `run_id` | string | Unique run identifier. Format: `run_YYYYMMDD_NNN`. Determines the manifest's own filename. |
| `triggered_at` | string | ISO-8601 timestamp of run start. |
| `triggered_by` | string | Always `"scenario_driver"` in the MVP. |
| `pipeline_build` | string | Build identifier of the IAP being tested e.g. `"IAP-v2.4.1"`. Currently filled in manually — pulling this from the build process automatically is a future improvement. |
| `scenario` | string | Name of the scenario being run e.g. `"full_regression_suite"`. |
| `run_type` | string | `"Imaging"` or `"Reanalysis"`. Consumed by the C# test harness (`RunInfo.RunType`), not by the verification service itself — but required in practice: the harness's JSON deserializer silently defaults a missing `run_type` to `"Imaging"` rather than erroring, which caused a real run to silently attempt a fresh hardware/simulated acquisition instead of reprocessing existing images (session 13). Always set this explicitly. |

---

## `build_verdict_policy` object

Defines how the verification service rolls up experiment-level results into a run-level verdict.

| Field | Type | Description |
|---|---|---|
| `rule` | string | `"all_stability_experiments_must_pass"` in the MVP. |
| `on_exploratory_failure` | string | `"warn_only"` — exploratory failures never fail the build. |

---

## `experiments` array

Each entry defines one experiment to be run and verified. All current experiments are flat single entries — no parent/child nesting in v1.

### Experiment fields

| Field | Type | Required | Description |
|---|---|---|---|
| `experiment_id` | string | yes | Stable identifier e.g. `"T078_run3"`. Must match registration in the verification database exactly — a mismatch here silently produces blank reports (see STATUS.md session 8). |
| `feature_set` | string | yes | Pipeline feature being exercised e.g. `"baseline_algo_performance"`. |
| `classification` | string | yes | `"stability"` or `"exploratory"` (ADR-003). |
| `counts_for_build_verdict` | boolean | yes | Whether this experiment's result contributes to the build verdict. |
| `image_source` | string | yes | Path to the raw images for this experiment — what the test harness feeds through the pipeline. |
| `sample_workbook` | string | yes | Path to the workbook file. Used for sample metadata only — not currently read by the verification service's code, but part of the documented contract for the harness/future tooling. |
| `comparisons` | array | yes | List of comparison entries to run against this experiment's active registered gold standard. See below. |
| `parent_experiment_id` | string | no | Present only for child experiments. References the experiment whose gold standard should be inherited. |
| `gold_standard_mode` | string | no | `"inherit_from_parent"` for child experiments. |

**Amendment (documented after being caught as a discrepancy, session 12):** earlier versions of this manifest included `gold_standard_ref` (a path to the gold standard CSV) and `gold_standard_checksum` (its SHA-256 hash, computed at registration). These are **no longer part of the manifest.** They were relevant when the gate recompared the CSV's checksum at verification time — see ADR-005's original decision. ADR-005's amendment (2026-05-14) removed that check once the comparator started reading expected values directly from `gold_standard_samples` in the database rather than from the CSV file: `run_gate()` today only checks whether an active registered gold standard *exists* in the database for `experiment_id` (`get_active_gs_version()`), never a file path or hash from the manifest. Comparisons run entirely against the database's active version for that `experiment_id` — the manifest doesn't need to know, or care, what file it came from.

### `comparisons` array entries

Introduced in ADR-016 (comparison registry), superseding the earlier `sample_tolerances` field. Each entry names a `type` that's looked up in `COMPARISON_REGISTRY` (`src/comparator/registry.py`), plus whatever parameters that strategy needs.

**`count_tolerance`** — percent-deviation check, one result per (sample, column).

| Field | Type | Description |
|---|---|---|
| `type` | string | `"count_tolerance"` |
| `tolerance_percent` | number | Maximum allowable percent deviation. |
| `columns` | array of strings | Which CSV columns (metrics) to compare. |

**`hybrid_tolerance`** — same shape as `count_tolerance`, but switches to absolute-difference tolerance below a count floor (percent deviation is noisy/meaningless near zero — see `src/comparator/strategies/hybrid_tolerance.py` and ADR-021).

| Field | Type | Description |
|---|---|---|
| `type` | string | `"hybrid_tolerance"` |
| `tolerance_percent` | number | Percent tolerance used when `expected_value >= count_threshold`. |
| `absolute_tolerance` | number | Absolute tolerance used when `expected_value < count_threshold`. |
| `count_threshold` | number | The cutover point between the two modes. |
| `columns` | array of strings | Which CSV columns (metrics) to compare. |

An experiment's `comparisons` array can contain more than one entry — e.g. a future experiment could run both a `count_tolerance` check on some columns and a different strategy on others.

---

## MVP manifest example

```json
{
  "run": {
    "run_id": "run_20260924_001",
    "triggered_at": "2026-09-24T21:00:00Z",
    "triggered_by": "scenario_driver",
    "pipeline_build": "IAP-v2.4.1",
    "scenario": "new_build_regression_baseline",
    "run_type": "Reanalysis"
  },

  "build_verdict_policy": {
    "rule": "all_stability_experiments_must_pass",
    "on_exploratory_failure": "warn_only"
  },

  "experiments": [
    {
      "experiment_id": "T078_run3",
      "feature_set": "baseline_algo_performance",
      "classification": "stability",
      "counts_for_build_verdict": true,
      "image_source": "E:\\CountableLabs\\Data\\T078_run3",
      "sample_workbook": "E:\\CountableLabs\\Data\\T078_run3\\Workbook_T078_run3.json",
      "comparisons": [
        {
          "type": "count_tolerance",
          "tolerance_percent": 10.0,
          "columns": [
            "UM-01_CountsPer50ul",
            "UM-02_CountsPer50ul",
            "UM-03_CountsPer50ul",
            "UM-04_CountsPer50ul"
          ]
        }
      ]
    },
    {
      "experiment_id": "MP47b_Adverum_02",
      "feature_set": "linkage",
      "classification": "exploratory",
      "counts_for_build_verdict": false,
      "image_source": "E:\\CountableLabs\\Data\\MP47b_Adverum_02",
      "sample_workbook": "E:\\CountableLabs\\Data\\MP47b_Adverum_02\\Workbook_MP47b_Adverum_02.json",
      "comparisons": [
        {
          "type": "hybrid_tolerance",
          "tolerance_percent": 10.0,
          "absolute_tolerance": 2,
          "count_threshold": 100,
          "columns": ["UM-01_only", "UM-01_UM-02", "UM-01_UM-02_UM-03_UM-04"]
        }
      ]
    }
  ]
}
```

---

## Open items

| Experiment | Issue |
|---|---|
| `linkage` (e.g. `MP47b_Adverum_02`) | Success criteria likely not count-based long-term. `hybrid_tolerance` in use as a near-term stand-in. See ADR-021 for the proposed aggregate-scope direction. |
| `dynamic_range` (e.g. `JS221N_serial_titration_PSF`) | Really a whole-experiment trend/curve property (linearity, %CV), not a per-sample check. `hybrid_tolerance` in use as a near-term stand-in. See ADR-021. |
| `10_channel` | Per-channel breakdown criteria still TBD — no registered experiment yet. |
| All experiments | `pipeline_build` is filled in manually for now; pulling it from the build process automatically is a future improvement. |
