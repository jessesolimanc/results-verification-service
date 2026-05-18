"""
orchestrator.py — coordinates the full verification flow for a run.

For each run detected by the listener:
  1. Load the run context manifest
  2. For each experiment in the manifest:
     a. Run the pre-verification gate
     b. Locate the result folder and CSV
     c. Run per-sample comparison (if gate passes)
  3. Determine experiment and run verdicts
  4. Persist results to the database
  5. Write CSV reports and store JSON blob

Entry points: load_manifest(), verify_run()
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.comparator.comparator import compare_experiment
from src.database.models import insert_experiment_result, insert_run, insert_sample_result
from src.gate.gate import run_gate
from src.reporter.reporter import (
    determine_experiment_verdict,
    determine_run_verdict,
    write_report,
)


def load_manifest(run_id: str, config: dict) -> dict:
    """Load and return the context manifest for a run."""
    path = Path(config["paths"]["manifests_dir"]) / f"context_manifest_{run_id}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Manifest not found for run '{run_id}': expected at {path}"
        )
    with open(path) as f:
        return json.load(f)


def find_result_folder(exp_id: str, run_id: str, config: dict) -> Path:
    """
    Locate the pipeline result folder for a given experiment and run.

    Globs for {exp_id}_{run_id}_* under results_dir.
    Always returns exactly one match — run_id uniqueness guarantees this.

    NOTE: Currently assumes CSVs are manually placed in the results folder.
    Future implementation will include a password-protected unzip step
    before this lookup — see STATUS.md open design questions.
    """
    results_dir = Path(config["paths"]["results_dir"])
    matches = list(results_dir.glob(f"{exp_id}_{run_id}_*"))

    if len(matches) == 0:
        raise FileNotFoundError(
            f"No result folder found for experiment '{exp_id}' / run '{run_id}' "
            f"under {results_dir}. "
            f"Expected a folder matching '{exp_id}_{run_id}_*'."
        )
    if len(matches) > 1:
        raise ValueError(
            f"Multiple result folders found for '{exp_id}' / '{run_id}' — "
            f"expected exactly one: {[str(m) for m in matches]}"
        )
    return matches[0]


def verify_run(conn, config: dict, run_id: str, manifest: dict) -> None:
    """
    Full verification flow for a single run.

    Coordinates gate, comparator, and reporter modules. All results are
    written to the verification database and CSV reports are written to
    {reports_dir}/{run_id}/.
    """
    policy = manifest["build_verdict_policy"]
    now = datetime.now(timezone.utc).isoformat()
    manifest_path = str(
        Path(config["paths"]["manifests_dir"]) / f"context_manifest_{run_id}.json"
    )

    experiment_results = []

    for experiment in manifest["experiments"]:
        gate_passed, gate_status = run_gate(conn, experiment["experiment_id"])
        sample_results = []
        comparison = None

        if gate_passed:
            try:
                result_folder = find_result_folder(
                    experiment["experiment_id"], run_id, config
                )
                result_csvs = list(result_folder.glob("*CountableDataSummary.csv"))
                if not result_csvs:
                    raise FileNotFoundError(
                        f"No CountableDataSummary.csv found in {result_folder}"
                    )
                comparison = compare_experiment(
                    conn, experiment, str(result_csvs[0])
                )
                sample_results = comparison["comparison_results"]
            except (FileNotFoundError, ValueError) as e:
                print(f"Warning: {e}")
                gate_passed = False

        experiment_results.append({
            "experiment_id":  experiment["experiment_id"],
            "feature_set":    experiment["feature_set"],
            "classification": experiment["classification"],
            "comparisons":    experiment.get("comparisons", []),
            "gate_status":    gate_status,
            "comparison":     comparison,
            "sample_results": sample_results,
            "verdict":        determine_experiment_verdict(sample_results),
        })

    run_verdict = determine_run_verdict(experiment_results, policy)

    with conn:
        insert_run(conn, {
            "run_id":         run_id,
            "triggered_at":   manifest["run"]["triggered_at"],
            "pipeline_build": manifest["run"]["pipeline_build"],
            "scenario":       manifest["run"]["scenario"],
            "manifest_path":  manifest_path,
            "verdict":        run_verdict,
        })

        for exp_result in experiment_results:
            if exp_result["comparison"] is None:
                continue  # gate or result lookup failed — no DB record for this experiment

            result_id = str(uuid.uuid4())
            exp_result["result_id"] = result_id
            comparison = exp_result["comparison"]

            insert_experiment_result(conn, {
                "result_id":         result_id,
                "run_id":            run_id,
                "gs_exp_version_id": comparison["gs_exp_version_id"],
                "experiment_id":     exp_result["experiment_id"],
                "feature_set":       exp_result["feature_set"],
                "classification":    exp_result["classification"],
                "pre_verify_status": exp_result["gate_status"],
                "verdict":           exp_result["verdict"],
                "verified_at":       now,
            })

            gs_samples_by_id = comparison["gs_samples"]
            for sr in exp_result["sample_results"]:
                if sr.get("actual_value") is None:
                    continue  # sample not found in results — captured in verdict, skip DB row
                gs_sample = gs_samples_by_id.get(sr["sample_id"])
                insert_sample_result(conn, {
                    "sample_result_id": str(uuid.uuid4()),
                    "result_id":        result_id,
                    "gs_sample_id":     gs_sample["gs_sample_id"] if gs_sample else "",
                    "sample_id":        sr["sample_id"],
                    "metric":           sr["metric"],
                    "comparison_type":  sr["comparison_type"],
                    "actual_value":     sr["actual_value"],
                    "expected_value":   sr["expected_value"],
                    "deviation_percent": sr.get("deviation_percent"),
                    "verdict":          sr["verdict"],
                    "notes":            sr.get("note"),
                })

    write_report(conn, config, run_id, experiment_results, run_verdict)
    print(f"Run {run_id} complete — verdict: {run_verdict}")
