# ADR-013: Mock listener for development and testing

## Status
Accepted

## Context
The verification service listener depends on a live PostgreSQL connection
to receive NOTIFY events from the pipeline database. Development is being
done on a personal machine without access to the pipeline database, making
it impossible to test the listener — and by extension the orchestrator,
gate, comparator, and reporter — against real events.

## Decision
Implement a mock listener (`listen_async_mock()`) alongside the real
listener (`listen_async()`) in `listener.py`. A config flag
(`listener.use_mock`) controls which is used at startup.

```yaml
# config.yaml
listener:
  use_mock: true    # set to false on the regression machine
```

The mock listener reads a hardcoded or file-based payload and passes it
through the same `on_notification` callback as the real listener, allowing
the full verification pipeline to be exercised without a DB connection.

## Reasoning
- Unblocks development of orchestrator, gate, comparator, and reporter
  on a machine without pipeline DB access
- The mock and real listeners share the same callback interface — swapping
  them requires only a config change, no code changes
- Isolates the asyncpg dependency behind the real listener — the rest of
  the codebase doesn't need to know which listener is active
- Mock payloads can be crafted to test specific scenarios (missing
  experiments, malformed payloads, partial runs)

## Consequences
- The mock listener must never be used on the production regression machine
  — the config flag must be set to false before deployment
- End-to-end testing against the real pipeline DB is deferred until the
  regression machine is available
- The mock payload format must match the real trigger payload exactly to
  avoid false confidence during development

## Mock payload format
```json
{
  "schema": "public",
  "op": "insert",
  "experimentId": "EXP_LT_control_assay_run_20260514_001_20260514_1504",
  "name": "mock_report",
  "user": "mock_user"
}
```

## Alternatives considered
- Integration test against a local PostgreSQL instance — rejected as
  over-engineered for the current stage; adds infrastructure complexity
  with no benefit over a well-crafted mock
- Skip listener testing entirely and test only on the regression machine —
  rejected because it would make the orchestrator, gate, comparator, and
  reporter untestable during development
