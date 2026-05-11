# ADR-005: Pre-verification gate with abort-on-failure

## Status
Accepted

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
