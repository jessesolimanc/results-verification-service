# ADR-004: Polling over event subscription for the listener

## Status
Accepted

## Context
The verification service needs to detect when new runs complete in the pipeline database. Two approaches were considered: polling the database at a fixed interval, or subscribing to database push notifications.

## Decision
Use a polling-based listener with a fixed interval.

## Reasoning
- Simpler to implement and debug
- Latency is not a concern — regression testing can tolerate a delay of seconds to minutes
- Avoids dependency on database-specific push infrastructure (e.g. SQL Server Service Broker)
- The regression machine is isolated — all runs are test runs, so no filtering logic is needed
- Polling overhead is negligible at low frequency on a lightly loaded system

## Consequences
- Slight delay between run completion and verification start
- Continuous low-level database reads — acceptable at low polling frequency
- Easy to replace with event subscription later if requirements change

## Alternatives considered
- SQL Server Service Broker / Query Notifications — rejected due to infrastructure complexity for no meaningful benefit at this scale
- Direct trigger from test harness to service — rejected because it couples the two halves of the system
