"""
orchestrator.py — coordinates the full verification flow for a run.

For each run detected by the listener:
  1. Load the run context manifest
  2. For each experiment in the manifest:
     a. Run the pre-verification gate
     b. Run per-sample comparison (if gate passes)
     c. Hand results to the LLM module
     d. Write report
  3. Record overall build verdict

Entry point: verify_run()
"""

import json
from pathlib import Path


def load_manifest(run_id: str, config: dict) -> dict:
    """Load and return the context manifest for a run."""
    path = Path(config["paths"]["manifests_dir"]) / f"context_manifest_{run_id}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Manifest not found for run '{run_id}': expected at {path}"
        )
    with open(path) as f:
        return json.load(f)


def find_result_folder(run_id: str, exp_id: str, config: dict) -> Path:
    """Locate the result folder for an experiment within a run."""
    # TODO: implement — glob for {exp_id}_{run_id}_* under workbooks_dir
    pass


def verify_run(config: dict, conn, run: dict) -> None:
    """
    Full verification flow for a single run.
    
    Coordinates gate, comparator, llm, and reporter modules.
    All results are written to the verification database.
    """
    # TODO: implement
    pass
