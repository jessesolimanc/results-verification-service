# ADR-002: One experiment per feature set

## Status
Accepted

## Context
Some pipeline features share underlying image data. A question arose about whether multiple features could share a single experiment to reduce duplication.

## Decision
Each feature set maps to exactly one experiment with its own workbook and gold standard. Features never share experiments, even if they share underlying image data.

## Reasoning
- Shared experiments produce ambiguous failures — if an experiment fails, it is unclear which feature broke
- Each feature may have different tolerances and success criteria that would conflict in a shared experiment
- Longitudinal queries per feature become clean and unambiguous
- Change management is simpler — updating one feature's gold standard cannot affect another

## Consequences
- Some workbooks may be subsets of the same underlying images — this is acceptable overhead
- The parent/child experiment relationship (available in the schema) handles shared image data without duplicating gold standard files
- Slightly more experiments to manage, but each has a single clear owner and purpose

## Alternatives considered
- Shared experiments per image set — rejected due to ambiguous failures and conflicting tolerances
