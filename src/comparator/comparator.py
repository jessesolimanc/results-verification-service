"""
comparator.py — per-sample comparison logic.

Compares actual pipeline output values against gold standard
expected values within the tolerances defined in the manifest.

Entry point: compare_experiment()
"""


def compare_sample(sample_id: str, actual: float,
                   expected: float, tolerance_percent: float) -> dict:
    """
    Compare one sample's actual value against its expected value.
    
    Returns a result dict containing:
      sample_id, actual_value, expected_value,
      deviation_percent, verdict ('pass' | 'fail')
    """
    # TODO: implement
    pass


def compare_experiment(actual_results: list[dict],
                       gold_standard_samples: list[dict],
                       tolerance_percent: float) -> list[dict]:
    """
    Compare all samples in an experiment.
    
    Returns a list of per-sample result dicts.
    """
    # TODO: implement
    pass
