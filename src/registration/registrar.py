"""
registrar.py — gold standard registration tool.

Reads a gold standard CSV, computes its SHA-256 checksum,
inserts a new version into gold_standard_exp_versions, and
inserts one row per sample into gold_standard_samples.

Entry point: register_gold_standard()
"""

import hashlib
import csv
from pathlib import Path


def compute_checksum(file_path: str) -> str:
    """Compute and return the SHA-256 hash of a file."""
    # TODO: implement
    pass


def read_gold_standard_csv(file_path: str) -> list[dict]:
    """Read a gold standard CSV and return a list of sample dicts."""
    # TODO: implement
    pass


def register_gold_standard(conn, experiment_id: str, file_path: str,
                            registered_by: str, reason: str) -> str:
    """
    Full registration flow for a gold standard experiment version.
    
    1. Compute checksum
    2. Read samples from CSV
    3. Retire current active version if one exists
    4. Insert new gs_exp_version record
    5. Insert gs_sample records
    
    Returns the new gs_exp_version_id.
    """
    # TODO: implement
    pass
