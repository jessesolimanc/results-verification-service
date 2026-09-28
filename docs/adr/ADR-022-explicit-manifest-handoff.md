# ADR-022: Explicit manifest hand-off replaces run_id stamping for run correlation

## Status
Accepted

## Context
ADR-012 documented the `reports_table_changes` NOTIFY payload as carrying
an `experimentId` field in the format `{exp_id}_{run_id}_{timestamp}`.
ADR-014 documented the mechanism behind that: the test harness would stamp
`run_id` into the experiment folder name at runtime, as the first step of
simulating image acquisition, and this stamped name would propagate through
the pipeline (IAP) into the `Reports` table and its NOTIFY payload.
`parse_experiment_notification()` extracted `run_id` from that string via
regex, and the orchestrator used `{exp_id}_{run_id}_*` to locate result
folders on disk.

In session 14, a full weekend Reanalysis-mode run — three experiments, all
pipeline writes and the `Reports` trigger confirmed healthy — produced zero
verification output, with no error anywhere. Manually replaying a
realistic NOTIFY payload against the running service reproduced this
silently: `parse_experiment_notification()` received a bare `experimentId`
(e.g. `"MP47b_Adverum_02"`, no `_run_` suffix of any kind), its regex never
matched, it returned `None`, and `handle_notification()` returned without
logging anything.

Investigating the harness codebase (`Countable.PCR`) directly found no code
path — Imaging or Reanalysis — that performs the stamping ADR-014
describes. Both `AcquisitionWorkflow.ExperimentName` and
`ReanalysisWorkflow.ExperimentName` derive the experiment name directly
from the workbook's own `RunInfo.ExperimentId`, unmodified, and that bare
name is what reaches `IapAnalyzer.AddWorkbook()` and, from there, the
`Reports` table. It is unclear whether this stamping step was removed at
some point or never actually implemented — either way, the payload
contract ADR-012/ADR-014 documented has never matched what the pipeline
actually sends, in either run mode.

A second, related gap found during the same investigation: the harness's
`LoadManifests()` globs every `context_manifest_*.json` file in
`manifests_dir` on every invocation and never archives one once its
experiments finish, so manifests accumulate indefinitely and are
reprocessed on every future run.

## Decision
Stop relying on `run_id` being encoded in any pipeline-supplied string.
The verification service now explicitly watches `manifests_dir` for new
manifest files (`src/orchestrator/manifest_watcher.py`, using the same
observer-first pattern as ADR-019's E: drive watch) and registers every
`experiment_id` a manifest declares as "expected" — building
`expected_experiment_to_run: {experiment_id: run_id}` — the moment the
file appears, before any pipeline notification for it has necessarily
arrived. A notification's bare `experiment_id` is now resolved with a
plain dictionary lookup against this map. `parse_experiment_notification()`
and its regex are removed entirely; `listener.py`'s only remaining job is
delivering a raw NOTIFY payload.

Once a run either completes verification or times out waiting on the E:
drive watch, its manifest is moved out of `manifests_dir` into a
`processed/` or `timed_out/` subfolder, so the folder stops accumulating
and a human can see at a glance which outcome a given run had.

This makes the manifest — already the system's documented contract
(ADR-001) — the sole mechanism for run correlation, rather than splitting
that responsibility between the manifest and an implicit pipeline-side
naming convention that had no enforcement and, in practice, was never
honored.

## Reasoning
The previous design required a naming convention to be independently
maintained correctly across two systems this codebase does not control —
the harness and, transitively, IAP — with no way to verify the assumption
held and no visibility when it silently didn't. The new design requires
nothing of the pipeline beyond what it already sends (a bare
`experiment_id`) and nothing of the harness beyond what ADR-015 already
assumed (a manifest appearing in `manifests_dir` before or as a run
starts).

It also resolves the multi-manifest correlation question raised while
designing this fix: since each manifest explicitly declares its own
experiment set the moment it's registered, two pending manifests can never
be silently confused with each other. A collision — the same
`experiment_id` pending under two different runs — is now something the
service detects and warns about loudly, instead of a passive listener
having no way to know it was even possible.

## What this supersedes / amends
- **Supersedes ADR-014** (Experiment folder naming convention and run_id
  stamping) — the run_id-in-folder-name convention and its parsing are
  removed. No harness change is required for this: the harness's current
  bare-experiment-id behavior, which turned out to be what it already
  does in both Imaging and Reanalysis modes, is correct as-is under the
  new contract.
- **Amends ADR-012's documented payload structure** — the `experimentId`
  field is now understood to be a bare experiment_id, not
  `{exp_id}_{run_id}_{timestamp}`. ADR-012's core decision (NOTIFY/LISTEN
  over polling) is unaffected.
- **Consistent with ADR-015** (decoupled entry point) — the manifest
  remains the sole interface regardless of what produces it or when; this
  decision only changes *when* the service reads that interface
  (proactively, on file arrival, rather than reactively inferring it from
  a notification).

## Consequences
- `listener.py` no longer does any experiment_id/run_id parsing.
- `main.py`'s `run_service()` runs a second concurrent watcher
  (`watch_manifests_dir`) alongside the Postgres listener for the
  lifetime of the service.
- A notification for an experiment_id with no pending manifest now prints
  a visible warning instead of returning silently — this alone would have
  surfaced session 14's incident immediately instead of after a full lost
  weekend.
- Manifests are archived (moved to `processed/` or `timed_out/`) once
  their run concludes on the verification-service side. The harness's own
  `LoadManifests()` still never archives — a related but separate gap,
  tracked as a follow-up, not fixed by this change.
- An unhandled exception inside a run's verification flow can still crash
  the whole service (observed session 14) — graceful per-run error
  isolation is tracked as an open design question, not addressed here.
- `result_file_suffix` (a related but separate manifest field, addressing
  which output CSV to read for a given experiment type) was added the
  same session — see `manifest-schema.md`. It is out of this ADR's scope,
  since it addresses a different problem than run correlation.

## Alternatives considered
- Fix `parse_experiment_notification()` to match the harness's actual
  (bare) format, and add real run_id stamping at the harness/IAP boundary
  instead — rejected as more invasive (touches IAP, a system this
  codebase doesn't own) and doesn't resolve the multi-manifest ambiguity
  question that prompted this redesign.
- Keep passive inference but disambiguate using timestamp proximity
  between a notification and pending manifests — rejected for the same
  reason ADR-014 originally rejected it: fragile, and two runs starting
  close together could produce ambiguous matches.
- Have the harness or a future entry point call the service directly (an
  API or socket) to register a run, rather than watching the filesystem —
  a heavier alternative, deferred since the filesystem-watch pattern is
  already established (ADR-019) and requires no new interface between the
  harness and the service.
