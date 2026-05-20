# ADR-020: Metafolder timing and RnDdata access — deferred

## Status
Accepted — deferred beyond current OKR scope

## Context
The pipeline stores a second category of output in a metadata folder:

```
E:\CountableLabs\Data\metafolder\{exp_id}_{run_id}_{timestamp}\
  exp_metadata.zip
    └── exp_metadata_inner.zip   ← password protected
          └── exp_RnDdata.csv    ← contains per-channel columns
```

This data is needed for future comparison types (linkage, dynamic range,
10-channel handling) that go beyond simple count tolerance checks on
CountableDataSummary.csv.

The metafolder presents a more complex timing and access problem than
the data folder:

1. **Slow copy** — metadata is larger and takes longer to copy E: → F:
2. **Double-zipped** — outer zip + password-protected inner zip
3. **Password handling** — secure password storage and retrieval needed
4. **Long/melted CSV format** — RnDdata.csv requires pivot preprocessing
   before comparison (see ADR-011 amendment)

## Decision
Metafolder access and RnDdata comparison types are explicitly deferred
beyond the current OKR scope. The E: deletion watch (ADR-019) covers
only E:\CountableLabs\ReportData — the metafolder is not watched at
this stage.

## What Will Be Needed When This Is Implemented

**Completion signal:**
The same deletion-watch pattern from ADR-019 applies — watch
E:\CountableLabs\Data\metafolder\{exp_id}_{run_id}_* for deletion
as the signal that F: copy is complete.

**Unzip sequence:**
```
Watch E: metafolder for deletion
        ↓
Locate F:\CountableLabs\metadata\{exp_id}_{run_id}_*\exp_metadata.zip
        ↓
Unzip outer archive
        ↓
Unzip inner password-protected archive
        ↓
Read and pivot RnDdata.csv (long → wide format)
        ↓
Proceed with comparison
```

**Password handling:**
Password for the inner archive must be stored securely — not in
config.yaml or any committed file. Options to evaluate at implementation
time: environment variable, Windows Credential Manager, secrets manager.

**CSV preprocessing:**
RnDdata.csv is in long/melted format (N rows per sample where N = number
of dyes). Must be pivoted to wide format before comparison. A
`preprocess_long_format()` function is already planned in
`read_gold_standard_csv()` — see STATUS.md open design questions.

## Consequences
- No code changes in current scope
- `e_drive_metafolder` and `metadata_dir` paths are added to config
  as placeholders for future use
- The open design question for RnDdata preprocessing remains in STATUS.md
- Password handling strategy to be decided at implementation time

## Related
- ADR-011 (JSON blob metrics) — amendment covers RnDdata long format
- ADR-019 (E: deletion watch) — same pattern applies to metafolder
- ADR-016 (comparison registry) — new comparison types will be added
  when RnDdata comparisons are implemented
