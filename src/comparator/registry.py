"""
registry.py — comparison strategy registry.

Maps comparison type strings (as declared in the context manifest)
to handler functions. To add a new comparison type, add one entry
here and implement the corresponding strategy in strategies/.

See ADR-016 for the reasoning behind this pattern.
"""

from src.comparator.strategies.count_tolerance import run_count_tolerance

COMPARISON_REGISTRY = {
    "count_tolerance": run_count_tolerance,
    # future entries:
    # "file_exists":       run_file_exists,
    # "correlation":       run_correlation,
    # "curve_fit":         run_curve_fit,
    # "per_channel_count": run_per_channel_count,
    # "flag_detection":    run_flag_detection,
}
