"""
comparator.py — per-sample comparison orchestration.

Fetches gold standard data, reads actual results, and dispatches
to the appropriate comparison strategy for each entry in the
manifest's comparisons list.

Entry point: compare_experiment()
"""

from src.comparator.registry import COMPARISON_REGISTRY
from src.database.models import get_active_gs_version, get_gs_samples
from src.registration.registrar import read_gold_standard_csv


def compare_experiment(conn, experiment: dict, result_csv_path: str) -> dict:
    """
    Orchestrate comparison for one experiment against the active gold standard.

    Dispatches to each handler declared in experiment["comparisons"] via
    the COMPARISON_REGISTRY. Raises ValueError for unrecognised types.

    Returns a dict with:
      gs_exp_version_id  — FK needed by the reporter
      gs_samples         — {sample_id: gs_sample_dict} for gs_sample_id lookup
      comparison_results — list of per-sample result dicts across all comparison types
    """
    active = get_active_gs_version(conn, experiment["experiment_id"])
    gs_exp_version_id = active["gs_exp_version_id"]

    gs_samples = get_gs_samples(conn, gs_exp_version_id)
    gs_samples_by_id = {s["sample_id"]: s for s in gs_samples}

    actual_samples = read_gold_standard_csv(result_csv_path)

    comparison_results = []
    for comparison in experiment["comparisons"]:
        handler = COMPARISON_REGISTRY.get(comparison["type"])
        if handler is None:
            raise ValueError(f"Unknown comparison type: '{comparison['type']}'")
        results = handler(actual_samples, gs_samples, comparison)
        comparison_results.extend(results)

    return {
        "gs_exp_version_id": gs_exp_version_id,
        "gs_samples":        gs_samples_by_id,
        "comparison_results": comparison_results,
    }
