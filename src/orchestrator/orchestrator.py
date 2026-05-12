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


def load_manifest(manifest_path: str) -> dict:
    """Load and return a run context manifest from disk."""
    with open(manifest_path) as f:
        return json.load(f)


def verify_run(config: dict, conn, run: dict) -> None:
    """
    Full verification flow for a single run.
    
    Coordinates gate, comparator, llm, and reporter modules.
    All results are written to the verification database.
    """
    # TODO: implement
    pass
