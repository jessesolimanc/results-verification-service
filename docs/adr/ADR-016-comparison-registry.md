# ADR-016: Strategy pattern for extensible comparison registry

## Status
Accepted

## Context
The comparator was initially designed to perform a single type of comparison:
count tolerance (is the actual count within X% of the expected count?).
However different experiment types require fundamentally different comparison
logic:

- Baseline algo performance → count tolerance per sample
- Linkage → file existence checks, colocalization metrics
- Dynamic range → curve shape / linearity (R²)
- 10-channel → per-channel count breakdown
- Reference sample → low count accuracy, flag detection

Hardcoding comparison logic in the comparator would make adding new
experiment types require modifying core comparator code — a violation of
the open/closed principle and a maintenance burden as the suite grows.

## Decision
Implement the comparator using the **strategy pattern** with a
**comparison registry**:

1. The context manifest declares which comparison types to run for each
   experiment via a `comparisons` list
2. A registry (`src/comparator/registry.py`) maps comparison type strings
   to handler functions
3. The comparator loops through the manifest's comparison list, looks up
   each handler in the registry, and executes it
4. Adding a new comparison type requires only adding one entry to the
   registry — no changes to the comparator's core logic

## Manifest schema change

The `sample_tolerances` field is replaced by a `comparisons` list:

```json
{
  "experiment_id": "EXP_LT_control_assay",
  "comparisons": [
    {
      "type": "count_tolerance",
      "tolerance_percent": 10.0
    }
  ]
}
```

This is a small, additive change. The `comparisons` list can contain
multiple entries for experiments that require multiple comparison types.

## Registry structure

```python
# src/comparator/registry.py

from src.comparator.strategies.count_tolerance import run_count_tolerance

COMPARISON_REGISTRY = {
    "count_tolerance": run_count_tolerance,
    # future entries added here:
    # "file_exists":   run_file_exists,
    # "correlation":   run_correlation,
    # "curve_fit":     run_curve_fit,
}
```

Each strategy function has a consistent signature:

```python
def run_count_tolerance(
    actual_samples: list[dict],
    gs_samples: list[dict],
    params: dict           # the comparison entry from the manifest
) -> list[dict]:           # list of per-sample result dicts
    ...
```

## MVP scope
Only `count_tolerance` is implemented in the MVP. The registry pattern
is in place from the start so future strategies are purely additive.

## Consequences
- The manifest schema changes from `sample_tolerances` to `comparisons`
  — all existing MVP manifests must be updated
- The comparator is slightly more complex than a direct implementation
  but the pattern is familiar and well-documented
- Each strategy is independently testable in isolation
- New comparison types can be added without touching existing code
- The registry is the single place to look when asking "what comparison
  types does this system support?"

## Future comparison types (anticipated)
| Type | Used by | Description |
|---|---|---|
| `count_tolerance` | All MVP experiments | Per-sample count within X% |
| `file_exists` | Linkage | Required output file present |
| `correlation` | Linkage | Colocalization / alignment metric |
| `curve_fit` | Dynamic range | R² of linearity fit |
| `per_channel_count` | 10-channel | Count tolerance per dye channel |
| `flag_detection` | Reference sample | Correct issue flags raised |

## Alternatives considered
- Hardcoded comparison logic per experiment type — rejected because it
  requires modifying core comparator code to add new experiment types
- Subclassing per experiment type — rejected as over-engineered for the
  current scale; the registry is simpler and equally extensible
- Comparison type defined in a YAML config file rather than code —
  rejected because strategies require executable code, not just
  configuration; a code registry is more explicit and type-safe
