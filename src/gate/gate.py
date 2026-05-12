"""
gate.py — pre-verification integrity checks.

Two sequential checks before any results comparison:
  1. Checksum check — gold standard file matches registered hash
  2. Subset check  — all samples in workbook exist in parent
                     gold standard (child experiments only)

If either check fails the run is aborted and no comparison runs.

Entry point: run_gate()
"""

import hashlib
from pathlib import Path


def checksum_check(file_path: str, expected_hash: str) -> bool:
    """Return True if the file's SHA-256 matches expected_hash."""
    # TODO: implement
    pass


def subset_check(workbook_sample_ids: list[str],
                 parent_sample_ids: list[str]) -> list[str]:
    """
    Return a list of sample IDs in the workbook that are NOT
    present in the parent gold standard. Empty list = pass.
    """
    # TODO: implement
    pass


def run_gate(conn, experiment: dict) -> tuple[bool, str]:
    """
    Run the full pre-verification gate for one experiment.
    
    Returns (passed: bool, status: str) where status is one of:
      'pass' | 'checksum_fail' | 'subset_fail'
    """
    # TODO: implement
    pass
