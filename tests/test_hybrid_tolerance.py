"""
Tests for src/comparator/strategies/hybrid_tolerance.py
"""

import pytest

from src.comparator.strategies.hybrid_tolerance import (
    compare_sample_hybrid,
    run_hybrid_tolerance,
)

TOLERANCE_PERCENT = 10.0
ABSOLUTE_TOLERANCE = 2
COUNT_THRESHOLD = 100


def _compare(expected, actual):
    return compare_sample_hybrid(
        "S1", "hybrid_tolerance", "metric",
        float(actual), float(expected),
        TOLERANCE_PERCENT, ABSOLUTE_TOLERANCE, COUNT_THRESHOLD,
    )


def test_below_threshold_within_absolute_tolerance_passes():
    result = _compare(expected=50, actual=51)
    assert result["verdict"] == "pass"
    assert result["deviation_percent"] is None


def test_below_threshold_outside_absolute_tolerance_fails():
    result = _compare(expected=50, actual=53)
    assert result["verdict"] == "fail"
    assert result["deviation_percent"] is None


def test_at_threshold_uses_percent_tolerance():
    # expected_value == count_threshold is NOT "below" -> percent mode
    result = _compare(expected=100, actual=108)  # 8% deviation, within 10%
    assert result["verdict"] == "pass"
    assert result["deviation_percent"] == 8.0


def test_at_threshold_fails_percent_tolerance():
    result = _compare(expected=100, actual=115)  # 15% deviation, outside 10%
    assert result["verdict"] == "fail"
    assert result["deviation_percent"] == 15.0


def test_zero_expected_zero_actual_passes_via_absolute_mode():
    # Falls into the absolute branch naturally (0 < count_threshold) —
    # no special-casing needed, unlike count_tolerance's zero/zero guard.
    result = _compare(expected=0, actual=0)
    assert result["verdict"] == "pass"
    assert result["deviation_percent"] is None


def test_zero_expected_nonzero_actual_within_absolute_tolerance_passes():
    result = _compare(expected=0, actual=1)
    assert result["verdict"] == "pass"


def test_zero_expected_nonzero_actual_outside_absolute_tolerance_fails():
    result = _compare(expected=0, actual=5)
    assert result["verdict"] == "fail"


def test_run_hybrid_tolerance_one_result_per_sample_per_column():
    gs_samples = [
        {"sample_id": "S1", "full_metrics": '{"UM-01_UM-02": 50, "UM-01_UM-03": 150}'},
        {"sample_id": "S2", "full_metrics": '{"UM-01_UM-02": 40, "UM-01_UM-03": 140}'},
    ]
    actual_samples = [
        {"SampleID": "S1", "UM-01_UM-02": "51", "UM-01_UM-03": "160"},
        {"SampleID": "S2", "UM-01_UM-02": "43", "UM-01_UM-03": "141"},
    ]
    params = {
        "type": "hybrid_tolerance",
        "tolerance_percent": TOLERANCE_PERCENT,
        "absolute_tolerance": ABSOLUTE_TOLERANCE,
        "count_threshold": COUNT_THRESHOLD,
        "columns": ["UM-01_UM-02", "UM-01_UM-03"],
    }

    results = run_hybrid_tolerance(actual_samples, gs_samples, params)

    assert len(results) == 4  # 2 samples x 2 columns
    by_key = {(r["sample_id"], r["metric"]): r for r in results}
    assert by_key[("S1", "UM-01_UM-02")]["verdict"] == "pass"   # abs diff 1 <= 2 (absolute mode)
    assert by_key[("S2", "UM-01_UM-02")]["verdict"] == "fail"   # abs diff 3 > 2 (absolute mode)
    assert by_key[("S1", "UM-01_UM-03")]["verdict"] == "pass"   # 6.67% <= 10% (percent mode)
    assert by_key[("S2", "UM-01_UM-03")]["verdict"] == "pass"   # 0.71% <= 10% (percent mode)


def test_run_hybrid_tolerance_missing_sample_fails_with_note():
    gs_samples = [{"sample_id": "S1", "full_metrics": '{"UM-01_UM-02": 50}'}]
    actual_samples = []  # S1 missing entirely
    params = {
        "type": "hybrid_tolerance",
        "tolerance_percent": TOLERANCE_PERCENT,
        "absolute_tolerance": ABSOLUTE_TOLERANCE,
        "count_threshold": COUNT_THRESHOLD,
        "columns": ["UM-01_UM-02"],
    }

    results = run_hybrid_tolerance(actual_samples, gs_samples, params)

    assert len(results) == 1
    assert results[0]["verdict"] == "fail"
    assert results[0]["note"] == "sample not found in results"
