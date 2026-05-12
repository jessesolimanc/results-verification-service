"""
reporter.py — assembles and writes verification reports.

Takes structured results from the comparator and narrative text
from the LLM module and writes the final report to the
verification database.

Entry point: write_report()
"""


def determine_experiment_verdict(sample_results: list[dict]) -> str:
    """
    Roll up per-sample verdicts into an experiment-level verdict.
    Returns 'pass' if all samples pass, 'fail' otherwise.
    """
    # TODO: implement
    pass


def determine_run_verdict(experiment_results: list[dict],
                          policy: dict) -> str:
    """
    Roll up experiment-level verdicts into a run-level build verdict
    according to the build_verdict_policy in the manifest.
    
    Returns 'pass' | 'fail' | 'warn'
    """
    # TODO: implement
    pass


def write_report(conn, run_id: str, result_id: str,
                 narrative: str, verdict: str) -> None:
    """Write a report record to the verification database."""
    # TODO: implement
    pass
