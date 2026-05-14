# ADR index

Architecture Decision Records for the results verification service.

| ADR | Title | Status |
|---|---|---|
| [ADR-001](ADR-001-manifest-as-contract.md) | Run context manifest as the system contract | Accepted |
| [ADR-002](ADR-002-experiment-per-feature.md) | One experiment per feature set | Accepted |
| [ADR-003](ADR-003-test-classification.md) | Stability vs exploratory experiment classification | Accepted |
| [ADR-004](ADR-004-polling-listener.md) | Polling over event subscription for the listener | ~~Superseded by ADR-012~~ |
| [ADR-005](ADR-005-pre-verification-gate.md) | Pre-verification gate with abort-on-failure | Accepted |
| [ADR-006](ADR-006-sqlite.md) | SQLite for the verification database | Accepted |
| [ADR-007](ADR-007-immutable-snapshots.md) | Immutable result snapshots — no backpropagation | Accepted |
| [ADR-008](ADR-008-gold-standard-versioning.md) | Experiment-level gold standard versioning | Accepted |
| [ADR-009](ADR-009-release-as-snapshot.md) | Gold standard release as optional convenience snapshot | Accepted |
| [ADR-010](ADR-010-hybrid-workflow.md) | Hybrid planning and implementation workflow | Accepted |
| [ADR-011](ADR-011-json-blob-metrics.md) | JSON blob storage for sample metrics | Accepted |
| [ADR-012](ADR-012-postgres-notify-listener.md) | PostgreSQL NOTIFY/LISTEN for event-driven listener | Accepted |
| [ADR-013](ADR-013-mock-listener.md) | Mock listener for development and testing | Accepted |
| [ADR-014](ADR-014-experiment-naming-convention.md) | Experiment folder naming convention and run_id stamping | Accepted |
| [ADR-015](ADR-015-decoupled-entry-point.md) | Decoupled entry point to support future test generator | Accepted |
