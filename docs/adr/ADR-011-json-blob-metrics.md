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

## Amendment — sample_results normalised to per-metric rows

**Date:** 2026-05-18

**Context:** The original design stored per-sample actual and expected values
as JSON blobs (`full_actual_metrics`, `full_expected_metrics`) in
`sample_results`, with scalar scaffolding columns (`actual_value`,
`expected_value`, `deviation_percent`) for simple single-metric queries.

**Problem identified:** A single set of scalar columns implicitly assumes
one metric per sample. With multiple dye channels (4-10 per experiment),
a sample has multiple actual and expected values — one per column. The
scalar columns can only hold one value, making the rest inaccessible
without deserialising JSON. This is the same problem the JSON blob design
solved for `gold_standard_samples`, but applied incorrectly to results.

**Resolution:** `sample_results` is normalised to one row per
`(sample_id, metric)` combination — the same melt pattern used in the
detail report. The JSON blob columns are removed entirely from
`sample_results`. Scalar columns are retained but now correctly represent
a single metric per row.

**Updated `sample_results` schema:**

```sql
CREATE TABLE IF NOT EXISTS sample_results (
    sample_result_id    TEXT    PRIMARY KEY,
    result_id           TEXT    NOT NULL
        REFERENCES experiment_results (result_id),
    gs_sample_id        TEXT    NOT NULL
        REFERENCES gold_standard_samples (gs_sample_id),
    sample_id           TEXT    NOT NULL,
    metric              TEXT    NOT NULL,       -- e.g. UM-01_CountsPer50ul
    comparison_type     TEXT    NOT NULL,       -- e.g. count_tolerance
    actual_value        REAL    NOT NULL,
    expected_value      REAL    NOT NULL,
    deviation_percent   REAL,
    verdict             TEXT    NOT NULL
        CHECK (verdict IN ('pass', 'fail')),
    notes               TEXT    DEFAULT NULL
);
```

**Removed from `sample_results`:**
- `primary_metric` — replaced by `metric`
- `primary_metric_value` — replaced by `actual_value` / `expected_value`
- `full_actual_metrics` — no longer needed; data is in normalised rows
- `full_expected_metrics` — no longer needed; data is in normalised rows

**`gold_standard_samples` unchanged:** The `full_metrics` JSON blob is
retained in `gold_standard_samples` as a complete archival record of what
was registered. The JSON approach remains correct there since registration
captures the full CSV row and column variability is a registration concern.

**Longitudinal queries now work cleanly:**

```sql
SELECT r.pipeline_build, sr.actual_value, sr.deviation_percent
FROM sample_results sr
JOIN experiment_results er ON sr.result_id = er.result_id
JOIN runs r ON er.run_id = r.run_id
WHERE sr.sample_id = '2DU008_01'
  AND sr.metric = 'UM-01_CountsPer50ul'
ORDER BY r.triggered_at ASC;
```

If the pipeline output CSV schema changes (column names renamed, columns
added or removed), the correct response is:

1. Re-register the gold standard with the new CSV format
2. The new `full_metrics` blob captures whatever columns exist in the new format
3. The comparator deserialises both blobs and compares matching keys — no
   code changes required

This means the verification service is effectively immune to pipeline output
schema changes as long as the gold standard is kept current. The only
exception is the MVP scaffolding (`PRIMARY_METRIC` constant hardcoded as
`"UM-01_CountsPer50ul"`) which would need updating if that column is renamed.
This is another argument for removing the scaffolding once full JSON
comparison is implemented.

## Alternatives considered
- **Normalised rows (Option A)** — rejected because it requires the registrar
  to understand per-experiment column semantics, creating coupling that scales
  poorly as experiment types grow. Also produces an order of magnitude more
  rows per sample with no benefit at this scale.
- **Hybrid without scaffolding** — rejected for the MVP because it would
  require JSON deserialisation in the comparator from day one, adding
  complexity before the basic plumbing is proven
