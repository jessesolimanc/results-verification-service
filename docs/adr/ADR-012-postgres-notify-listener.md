# ADR-012: PostgreSQL NOTIFY/LISTEN for event-driven listener

## Status
Accepted

## Context
The verification service needs to detect when experiments complete in the
pipeline database. Two approaches were previously considered: polling on a
fixed interval (ADR-004, accepted for simplicity) and event subscription.

During implementation it was discovered that the pipeline database is
PostgreSQL and already has triggers on the `Reports` and `Workbooks` tables
that fire `pg_notify()` on named channels when rows are inserted, updated,
or deleted. This makes a native event-driven listener available at no
additional infrastructure cost.

## Decision
Replace the polling-based listener with a PostgreSQL NOTIFY/LISTEN
implementation using `asyncpg`. The listener subscribes to the
`reports_table_changes` channel. When a notification arrives, it parses
the payload and passes the event to the orchestrator.

ADR-004 is superseded by this decision.

## Reasoning
- A native DB event is available — no reason to poll when push exists
- Lower latency than polling — verification starts immediately when a
  report lands rather than waiting for the next poll interval
- No unnecessary DB reads — the listener only wakes up when something
  actually happens
- The pipeline already has the trigger infrastructure in place — no
  pipeline changes required
- `asyncpg` is a well-maintained async PostgreSQL client for Python

## Payload structure
The `reports_table_changes` notification carries:

```json
{
  "schema": "public",
  "op": "insert",
  "experimentId": "EXP_LT_control_assay_run_20260514_001_20260514_1504",
  "name": "report_name",
  "user": "db_user"
}
```

The `experimentId` field encodes the full experiment folder name in the
format `{exp_id}_{run_id}_{timestamp}`. The listener parses this to extract
`exp_id` and `run_id` for grouping and folder lookup.

## Consequences
- The listener module uses `async/await` — `main.py` must use
  `asyncio.run()` to start the event loop
- `asyncpg` must be added to `requirements.txt`
- Testing on a machine without PostgreSQL access requires a mock listener
  (see ADR-013)
- The listener must handle connection drops and retry gracefully — the
  outer retry loop from the pipeline codebase is adopted as the pattern
- One notification fires per experiment completion — the listener must
  group by `run_id` and wait for all expected experiments before handing
  off to the orchestrator

## Alternatives considered
- Polling (ADR-004) — superseded. Polling was chosen originally for
  simplicity before the pipeline's trigger infrastructure was known.
  Now that a native event exists, polling adds unnecessary latency and
  DB load with no benefit.
