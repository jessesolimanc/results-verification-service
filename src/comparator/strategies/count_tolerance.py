"""
count_tolerance.py — count tolerance comparison strategy.

Compares actual pipeline count values against gold standard expected
values within a percentage tolerance defined in the manifest.

Strategy signature: run_count_tolerance(actual_samples, gs_samples, params)
"""

from src.registration.registrar import PRIMARY_METRIC, SAMPLE_ID_COLUMN


def compare_sample(sample_id: str, actual_value: float,
                   expected_value: float, tolerance_percent: float) -> dict:
    """
    Compare one sample's actual count against its expected value.

    Returns a result dict with sample_id, actual_value, expected_value,
    deviation_percent, and verdict ('pass' | 'fail').

    If expected_value is zero, returns 'fail' with deviation_percent of
    None and a 'note' field — division by zero avoided.
    """
    if expected_value == 0:
        return {
            "sample_id":         sample_id,
            "actual_value":      actual_value,
            "expected_value":    expected_value,
            "deviation_percent": None,
            "verdict":           "fail",
            "note":              "expected_value is zero — division avoided",
        }

    deviation = round(abs(actual_value - expected_value) / expected_value * 100, 4)
    return {
        "sample_id":         sample_id,
        "actual_value":      actual_value,
        "expected_value":    expected_value,
        "deviation_percent": deviation,
        "verdict":           "pass" if deviation <= tolerance_percent else "fail",
    }


def run_count_tolerance(actual_samples: list[dict],
                        gs_samples: list[dict],
                        params: dict) -> list[dict]:
    """
    Run count tolerance comparison for all samples in an experiment.

    actual_samples — raw CSV rows from read_gold_standard_csv() (actual results)
    gs_samples     — sample dicts from get_gs_samples() (gold standard from DB)
    params         — comparison entry from manifest e.g.
                     {"type": "count_tolerance", "tolerance_percent": 10.0}

    Returns a list of per-sample result dicts.
    """
    actual_by_id = {row[SAMPLE_ID_COLUMN]: row for row in actual_samples}
    tolerance = params["tolerance_percent"]

    results = []
    for gs_sample in gs_samples:
        sid = gs_sample["sample_id"]
        actual_row = actual_by_id.get(sid)

        if actual_row is None:
            results.append({
                "sample_id":         sid,
                "actual_value":      None,
                "expected_value":    gs_sample["primary_metric_value"],
                "deviation_percent": None,
                "verdict":           "fail",
                "note":              "sample not found in results",
            })
        else:
            results.append(compare_sample(
                sid,
                float(actual_row[PRIMARY_METRIC]),
                gs_sample["primary_metric_value"],
                tolerance,
            ))

    return results
