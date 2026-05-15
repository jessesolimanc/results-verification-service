# ADR-005: Pre-verification gate with abort-on-failure

## Status
Accepted — checksum check clarified (see amendment below)

## Context
Before comparing results against a gold standard, the system must confirm that the gold standard itself can be trusted. Two integrity risks were identified: (1) the gold standard file being modified since registration, and (2) a child experiment's workbook containing sample IDs not present in the parent gold standard.

## Decision
A mandatory pre-verification gate runs before any results comparison. It performs two sequential checks:
1. Checksum integrity — recompute SHA-256 of the gold standard CSV and compare against the registered hash
2. Subset validity (child experiments only) — confirm every sample in the workbook exists in the parent gold standard

If either check fails, the run aborts immediately and no comparison is performed.

## Reasoning
- A modified gold standard invalidates any comparison result — proceeding would silently pollute the longitudinal record
- Abort produces a clearly differentiated failure signal ("data integrity issue") vs a normal test failure ("results out of tolerance")
- Sequential ordering matters: subset validity is only meaningful if the file has already passed the checksum check
- Defensive programming: even trusted teams make mistakes, and silent data corruption is the most damaging kind

## Consequences
- Aborted runs must be clearly communicated and are distinguishable from failed runs in the database (`pre_verify_status` field)
- Gold standard files must be treated as immutable after registration — any intentional update requires re-registration
- The gate adds a small amount of processing overhead at the start of each run

## Alternatives considered
- Warn and continue on checksum failure — rejected because comparison results against an untrusted baseline are meaningless
- No integrity check — rejected as it allows silent data corruption to propagate undetected

---

## Amendment — checksum check removed from verification gate

**Date:** 2026-05-14

**Context:** The original design assumed the gate would recompute the SHA-256
hash of the gold standard CSV and compare it against the registered hash to
detect file tampering. This made sense when the comparator was expected to
read expected values directly from the CSV file.

**What changed:** The decision to read gold standard expected values from the
database (ADR-011) rather than the CSV file makes the CSV checksum check
redundant in the verification context. The comparator never touches the CSV
during a run — it reads entirely from `gold_standard_samples` in the
verification database. Whether the CSV has changed is therefore irrelevant
to verification correctness.

**Revised gate behaviour:** The gate now performs one check only:

> Does an active registered gold standard exist in the database for this
> experiment? If yes — trust the database and proceed. If no — abort.

```python
def run_gate(conn, experiment):
    active = get_active_gs_version(conn, experiment["experiment_id"])
    if active is None:
        return (False, "no_gold_standard")
    return (True, "pass")
```

The database's `superseded_at` pattern guarantees the active version is
always the most recently registered one. This is a stronger integrity
guarantee than a file checksum because the database record is written
programmatically and is not subject to accidental modification.

**Checksum at registration time:** The SHA-256 hash is still computed and
stored at registration time. Its purpose is now narrowly scoped to:
- Providing an audit trail of what file was registered
- Supporting a future re-registration workflow that could warn if the CSV
  has changed since last registration

**Subset validity check:** Unchanged — still planned for Phase 3.

**Impact on `checksum_check()` function:** The function remains in
`gate.py` as it may be useful for the re-registration workflow. It is
simply not called during the verification gate flow.
