# ADR-001: Run context manifest as the system contract

## Status
Accepted

## Context
The test harness and the results verification service are two decoupled processes. They need a way to communicate what was run and what the expected outcomes are, without being directly coupled to each other.

## Decision
The run context manifest — a JSON file written by the test harness at run start — is the sole interface between the two halves of the system. The verification service reads only the manifest and the database event that triggered it. It has no direct knowledge of the test harness internals.

## Reasoning
- Decouples the two halves completely — either can be updated independently as long as the manifest schema is respected
- The manifest is human-readable and auditable
- All rules and pointers live in one place, making the system's behaviour transparent
- Enables a future manifest generator UI without changing the verification service

## Consequences
- The manifest schema must be carefully maintained — it is a public contract
- Any new verification capability requires a schema addition
- The manifest must be written before the run completes so the verification service can find it via run_id

## Alternatives considered
- Direct API call from harness to verification service — rejected because it creates tight coupling and requires the service to be reachable at run time
- Shared database table as the interface — rejected because it mixes concerns between the pipeline DB and the verification system
