# ADR-014: Experiment folder naming convention and run_id stamping

## Status
Accepted

## Context
The pipeline generates metadata folders for each experiment using the
`ExperimentId` field from the workbook. Multiple runs of the same
experiment type produce multiple folders with the same base name, making
it impossible to distinguish which folder belongs to which test run without
additional information.

Two problems needed solving:
1. Grouping experiments that belong to the same run
2. Locating the correct result folder when multiple runs of the same
   experiment exist on disk

## Decision
The test harness stamps the `run_id` into the experiment folder name at
runtime by renaming/creating the raw image folder to follow the convention:

```
{exp_id}_{run_id}_{timestamp}
```

For example:
```
EXP_LT_control_assay_run_20260514_001_20260514_1504/
```

This naming is propagated through the pipeline — the IAP reads the folder
name as the `ExperimentId` and uses it for all downstream metadata folders
and database records. The `ExperimentId` field in the Reports table trigger
payload therefore carries the full `{exp_id}_{run_id}_{timestamp}` string.

## Parsing

The `run_id` is extracted from the full experiment folder name by splitting
on `_run_`:

```python
def parse_experiment_notification(experiment_id_field: str) -> tuple[str, str]:
    parts = experiment_id_field.split('_run_')
    exp_id = parts[0]
    remainder = 'run_' + parts[1]
    run_id = '_'.join(remainder.split('_')[:3])
    return exp_id, run_id
```

## Grouping

The listener maintains a run group — a dict keyed by `run_id` tracking
which experiments have completed. When all experiments listed in the
manifest for a given `run_id` are present, the orchestrator is triggered.

## Folder lookup

The orchestrator locates result files by globbing for:
```python
results_dir.glob(f"{exp_id}_{run_id}_*")
```
This always returns exactly one folder since `run_id` is unique per run.

## MVP manual steps
For the MVP, the following are done manually before each run:
- Workbooks are updated to reflect the stamped experiment name
- The context manifest is updated with the correct workbook names

A workbook generator and manifest generator are planned as future
components to automate these steps.

## Consequences
- The test harness must perform the folder rename/create as the first
  step of simulating image acquisition
- The base `exp_id` (e.g. `EXP_LT_control_assay`) remains the stable
  longitudinal key in the verification database — the full stamped name
  is a coordination mechanism only
- Workbooks and manifests require manual updates for the MVP — this is
  a known limitation with a clear automation path

## Alternatives considered
- Appending run_id to experiment_id as a permanent identifier — rejected
  because it breaks longitudinal tracking (see ADR-002)
- Timestamp proximity matching to find result folders — rejected as
  fragile; two runs starting close together could produce ambiguous matches
- Storing folder path explicitly in the pipeline DB — unnecessary given
  the deterministic naming convention
