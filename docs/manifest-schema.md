# Run context manifest — schema reference

## Purpose

The run context manifest is a JSON file written by the test harness at the start of every regression run. It is the contract between the test harness and the results verification service. Everything the verification service needs to verify a run is either contained in or referenced by the manifest.

The manifest carries rules and pointers — not raw expected values. Gold standard data lives in registered CSV files and in the verification database.

---

## File location and naming

Manifests are stored in a watched folder on the regression machine:

```
manifests/
  run_20260428_001.json
  run_20260428_002.json
```

Naming convention: `run_YYYYMMDD_NNN.json` where NNN is a zero-padded sequence number. The verification service locates a manifest by constructing the path from the `run_id` in the database event — no searching required.

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

Metadata identifying the run. Fields marked `[runtime]` are populated automatically by the test harness at execution time.

| Field | Type | Description |
|---|---|---|
| `run_id` | string | Unique run identifier. Format: `run_YYYYMMDD_NNN`. `[runtime]` |
| `triggered_at` | string | ISO-8601 timestamp of run start. `[runtime]` |
| `triggered_by` | string | Always `"scenario_driver"` in the MVP. |
| `pipeline_build` | string | Build identifier of the IAP being tested e.g. `"IAP-v2.4.1"`. `[runtime]` |
| `scenario` | string | Name of the scenario being run e.g. `"full_regression_suite"`. |

---

## `build_verdict_policy` object

Defines how the verification service rolls up experiment-level results into a run-level verdict.

| Field | Type | Description |
|---|---|---|
| `rule` | string | `"all_stability_experiments_must_pass"` in the MVP. |
| `on_exploratory_failure` | string | `"warn_only"` — exploratory failures never fail the build. |

---

## `experiments` array

Each entry defines one experiment to be run and verified. All five MVP experiments are flat single entries — no parent/child nesting in v1.

### Experiment fields

| Field | Type | Required | Description |
|---|---|---|---|
| `experiment_id` | string | yes | Stable identifier e.g. `"EXP_LT_control_assay"`. Must match registration in the verification database. |
| `feature_set` | string | yes | Pipeline feature being exercised e.g. `"baseline_algo_performance"`. |
| `classification` | string | yes | `"stability"` or `"exploratory"`. |
| `counts_for_build_verdict` | boolean | yes | Whether this experiment's result contributes to the build verdict. |
| `image_source` | string | yes | Local path to the raw images for this experiment. |
| `sample_workbook` | string | yes | Path to the workbook file. Used for sample metadata only — not for expected values. |
| `gold_standard_ref` | string | yes | Path to the gold standard CSV. Used at registration time. After registration the database is the source of truth. |
| `gold_standard_checksum` | object | yes | See below. |
| `sample_tolerances` | object | yes | See below. |
| `parent_experiment_id` | string | no | Present only for child experiments. References the experiment whose gold standard should be inherited. |
| `gold_standard_mode` | string | no | `"inherit_from_parent"` for child experiments. |

### `gold_standard_checksum` object

| Field | Type | Description |
|---|---|---|
| `algorithm` | string | Always `"sha256"` in the MVP. |
| `hash` | string | SHA-256 hash of the gold standard CSV. Computed and recorded at registration time. |
| `registered_at` | string | ISO-8601 timestamp of registration. |
| `registered_by` | string | Name of person who registered the gold standard. |

### `sample_tolerances` object

| Field | Type | Description |
|---|---|---|
| `counts_tolerance_percent` | number | Maximum allowable deviation from the gold standard expected value, expressed as a percentage. MVP default: `10.0`. |

---

## MVP manifest example

```json
{
  "run": {
    "run_id": "run_20260428_001",
    "triggered_at": "2026-04-28T09:00:00Z",
    "triggered_by": "scenario_driver",
    "pipeline_build": "IAP-v2.4.1",
    "scenario": "full_regression_suite"
  },

  "build_verdict_policy": {
    "rule": "all_stability_experiments_must_pass",
    "on_exploratory_failure": "warn_only"
  },

  "experiments": [
    {
      "experiment_id": "EXP_LT_control_assay",
      "feature_set": "baseline_algo_performance",
      "classification": "stability",
      "counts_for_build_verdict": true,
      "image_source": "<path TBD>",
      "sample_workbook": "workbooks\\EXP_LT_control_assay_workbook.xlsx",
      "gold_standard_ref": "gold_standards\\EXP_LT_control_assay_reference.csv",
      "gold_standard_checksum": {
        "algorithm": "sha256",
        "hash": "<computed at registration>",
        "registered_at": "<ISO-8601>",
        "registered_by": "<name>"
      },
      "sample_tolerances": {
        "counts_tolerance_percent": 10.0
      }
    },
    {
      "experiment_id": "EXP_linkage",
      "feature_set": "linkage",
      "classification": "stability",
      "counts_for_build_verdict": true,
      "image_source": "<path TBD>",
      "sample_workbook": "workbooks\\EXP_linkage_workbook.xlsx",
      "gold_standard_ref": "gold_standards\\EXP_linkage_reference.csv",
      "gold_standard_checksum": {
        "algorithm": "sha256",
        "hash": "<computed at registration>",
        "registered_at": "<ISO-8601>",
        "registered_by": "<name>"
      },
      "sample_tolerances": {
        "counts_tolerance_percent": 10.0
      }
    },
    {
      "experiment_id": "EXP_dynamic_range",
      "feature_set": "dynamic_range",
      "classification": "stability",
      "counts_for_build_verdict": true,
      "image_source": "<path TBD>",
      "sample_workbook": "workbooks\\EXP_dynamic_range_workbook.xlsx",
      "gold_standard_ref": "gold_standards\\EXP_dynamic_range_reference.csv",
      "gold_standard_checksum": {
        "algorithm": "sha256",
        "hash": "<computed at registration>",
        "registered_at": "<ISO-8601>",
        "registered_by": "<name>"
      },
      "sample_tolerances": {
        "counts_tolerance_percent": 10.0
      }
    },
    {
      "experiment_id": "EXP_reference_sample_low_count",
      "feature_set": "reference_sample_module",
      "classification": "stability",
      "counts_for_build_verdict": true,
      "image_source": "<path TBD>",
      "sample_workbook": "workbooks\\EXP_reference_sample_low_count_workbook.xlsx",
      "gold_standard_ref": "gold_standards\\EXP_reference_sample_low_count_reference.csv",
      "gold_standard_checksum": {
        "algorithm": "sha256",
        "hash": "<computed at registration>",
        "registered_at": "<ISO-8601>",
        "registered_by": "<name>"
      },
      "sample_tolerances": {
        "counts_tolerance_percent": 10.0
      }
    },
    {
      "experiment_id": "EXP_10_channel",
      "feature_set": "multi_channel_handling",
      "classification": "stability",
      "counts_for_build_verdict": true,
      "image_source": "<path TBD>",
      "sample_workbook": "workbooks\\EXP_10_channel_workbook.xlsx",
      "gold_standard_ref": "gold_standards\\EXP_10_channel_reference.csv",
      "gold_standard_checksum": {
        "algorithm": "sha256",
        "hash": "<computed at registration>",
        "registered_at": "<ISO-8601>",
        "registered_by": "<name>"
      },
      "sample_tolerances": {
        "counts_tolerance_percent": 10.0
      }
    }
  ]
}
```

---

## Open items

The following tolerances and success criteria are placeholders and need to be revisited before the MVP can be considered complete:

| Experiment | Issue |
|---|---|
| `EXP_linkage` | Success criteria likely not count-based. Needs definition. |
| `EXP_dynamic_range` | May need a curve-shape metric rather than per-sample tolerance. |
| `EXP_10_channel` | Needs per-channel breakdown criteria. |
| All experiments | Image paths marked `<path TBD>` — update when images transferred to regression machine. |
