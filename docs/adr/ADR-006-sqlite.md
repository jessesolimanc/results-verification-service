# ADR-006: SQLite for the verification database

## Status
Accepted

## Context
The verification service needs a database to store runs, results, gold standards, and reports. Options considered were SQL Server, PostgreSQL, and SQLite.

## Decision
Use SQLite.

## Reasoning
- The verification service runs on a single dedicated lab machine — no multi-user or network access is required
- Zero infrastructure: no server process to manage, install, or maintain
- Single file: easy to back up, inspect, and move
- Python's standard library includes sqlite3 — no external dependency needed
- Fully adequate for sequential regression test workloads
- The relational model is correct for this data regardless of engine choice

## Consequences
- Not suitable if requirements change to require network-accessible or multi-user database access
- Migration to SQL Server or PostgreSQL is straightforward if needed — the schema is standard SQL
- No built-in replication or high availability — acceptable for a lab regression machine

## Alternatives considered
- SQL Server — rejected as over-engineered for a single-machine local workload; familiar to the team but adds infrastructure overhead
- PostgreSQL — rejected for the same reasons; excellent database but unnecessary here
