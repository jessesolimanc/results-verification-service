# ADR-011: JSON blob storage for sample metrics

## Status
Accepted

## Context
Gold standard CSVs and pipeline result files have a variable number of metric
columns depending on the experiment type. The number of dyes used (e.g. UM-01,
FAM, HEX) and the metrics captured per dye (e.g. CountsPer50ul, IDscore,
Signal, Background) vary across experiments. This variability needed to be
handled in how expected and actual metric values are stored in the database.

Two options were considered:

**Option A — Normalised rows (one row per metric per sample)**
Store each metric as its own database row with columns
`sample_id`, `metric_name`, `metric_value`. A sample with 5 metrics produces
5 rows.

**Option B — JSON blob (one row per sample, all metrics serialised)**
Store all metrics for a sample as a JSON object in a single `full_metrics`
TEXT column. A sample with 5 metrics still produces 1 row.

## Decision
Use JSON blob storage (Option B) with MVP scaffolding columns for the
primary metric.

Specifically:
- `gold_standard_samples` stores all metrics in a `full_metrics` JSON column,
  plus `primary_metric` (column name) and `primary_metric_value` (float) as
  explicit scaffolding columns for the MVP comparator
- `sample_results` stores `full_actual_metrics` and `full_expected_metrics`
  as JSON snapshots, plus explicit `actual_value`, `expected_value`, and
  `deviation_percent` columns as MVP scaffolding

The scaffolding columns will be dropped once full JSON-based comparison is
implemented (see Consequences).

## Reasoning
- The registrar does not need to understand the semantic meaning of columns —
  it reads whatever is in the CSV and stores it faithfully as a dict
- Comparison is naturally metric-name-keyed: deserialise both gold standard
  and actual result into dicts, then iterate over matching keys. Variable
  column names and counts are handled without any schema changes
- Adding a new experiment type with new dye combinations requires no database
  schema changes — the JSON absorbs the variability
- Option A would require the registrar to know which columns are metrics and
  which are metadata on a per-experiment basis, creating coupling that grows
  as experiment types are added
- At the scale of this system (single lab machine, sequential runs) there is
  no performance argument for normalisation

## Consequences
- **Longitudinal queries** on individual metrics require JSON deserialisation
  and cannot use simple SQL column comparisons. This is mitigated by defining
  stock SQL views for the most common longitudinal queries (e.g. counts trend
  per sample per experiment) — query complexity is paid once at view
  definition time
- **MVP scaffolding columns** (`primary_metric`, `primary_metric_value`,
  `actual_value`, `expected_value`, `deviation_percent`) exist temporarily to
  keep the initial comparator simple. These are explicitly marked as
  scaffolding in the schema and STATUS.md, and should be removed in a future
  migration once full JSON comparison is implemented
- **Inspecting raw data** in the database requires JSON parsing — a tool like
  DB Browser for SQLite with JSON functions, or a small reporting script, is
  needed for ad-hoc inspection
- **The comparator** must deserialise `full_metrics` JSON before comparison.
  The comparison logic itself becomes experiment-agnostic: same key →
  compare values → apply tolerance

## Stock views to define (future task)
The following longitudinal queries should be implemented as SQL views to
offset the JSON querying cost:

- Counts trend per sample per experiment across builds
- Pass rate per experiment across builds
- Deviation trend per metric per experiment across builds

## Alternatives considered
- **Normalised rows (Option A)** — rejected because it requires the registrar
  to understand per-experiment column semantics, creating coupling that scales
  poorly as experiment types grow. Also produces an order of magnitude more
  rows per sample with no benefit at this scale.
- **Hybrid without scaffolding** — rejected for the MVP because it would
  require JSON deserialisation in the comparator from day one, adding
  complexity before the basic plumbing is proven
