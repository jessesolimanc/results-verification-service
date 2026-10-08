# ADR-024: NSSM-wrapped Windows Service for the verification service

## Status
Accepted

## Context
The verification service (`python -m src.main --run`) is an always-on
process by design (ADR-015: the entry point is decoupled precisely
because the service is supposed to just always be listening). In
practice, up through session 14, it has only ever run because someone
had a terminal open with the venv activated on the regression machine —
this is exactly what let a full weekend's runs sit unpicked-up
undetected (session 14's original incident).

With ADR-023 adding a one-click GitHub Actions trigger for starting a
run, the service being reliably running in the background stops being
optional — a dispatched workflow that stamps a manifest and starts the
harness is silently useless if nothing is listening for the resulting
NOTIFY events. STATUS.md's Phase 4 checklist already named this:
"Windows Service wrapper."

Every other piece of software this project depends on that runs as a
Windows service — the pipeline's own `CountableAnalysisService` — is a
proper .NET service, using .NET's native Windows Service hosting. That
tells us nothing about how to run a *Python* process as a service:
`python.exe` doesn't speak the Service Control Manager's (SCM) protocol
at all, .NET's native support doesn't apply here, and there's no
existing non-.NET service convention on this machine to match.

## Decision
Wrap `python -m src.main --run` as a Windows Service using NSSM
(https://nssm.cc), installed via a new `scripts/install_verification_service.ps1`.

NSSM's job is narrow and mechanical: it registers *itself* with the SCM
as the actual service, and only NSSM ever talks to the SCM (start,
stop, status, crash detection). Underneath, NSSM launches and supervises
the real command (`.venv\Scripts\python.exe -m src.main --run`) as a
plain child process, and translates the SCM's requests into things that
process can understand — a stop request becomes a Ctrl+C-style console
signal (configurable, with a fallback escalation to terminating the
process outright if it doesn't exit in time).

This is a wrapper, not a code change to make `main.py` "service-aware"
in any deep sense. `main.py` still runs exactly the way it always has
when invoked manually — the only change made to it is catching
`KeyboardInterrupt` for a clean log line (see below), which also makes
manual Ctrl+C during interactive development nicer.

### Why NSSM and not a native `pywin32` service
The alternative is writing `main.py` (or a small wrapper module) as a
real `pywin32` `win32serviceutil.ServiceFramework` subclass, which talks
to the SCM directly instead of through a middleman. Rejected for now:

- It requires bridging the SCM's stop callback (delivered on a Windows
  service control thread) into the asyncio event loop that
  `run_service()` actually runs on — today's `token: asyncio.Event` was
  clearly built with exactly this kind of cross-thread signal in mind,
  but nothing currently sets it (dead code). Wiring this correctly is
  meaningfully more work than an NSSM install.
- NSSM is genuinely simpler to install, review, and undo — one binary,
  no code changes to the service's shutdown model, and a plain
  `nssm remove` to walk it back.
- Nothing about the NSSM choice forecloses moving to `pywin32` later if
  a real need shows up (e.g. the SCM's richer status reporting, or
  service-to-service dependencies) — NSSM and `pywin32` both end up
  running the identical `python -m src.main --run`, so switching later
  doesn't touch `main.py`'s actual logic.

### Graceful-ish shutdown
`main.py`'s `run()` now catches `KeyboardInterrupt` around `asyncio.run(...)`
and prints a clean shutdown message instead of letting the traceback
through. The substantive shutdown behavior underneath is *not* new code
— it's `asyncio.run()`'s own documented cleanup sequence: on interrupt,
it cancels the still-running `run_service()` coroutine at its current
suspend point (letting `run_service()`'s own
`finally: manifest_watch_task.cancel()` run, which lets
`watch_manifests_dir()`'s own `finally` — `observer.stop()`/`join()` —
run too), separately cancels `manifest_watch_task`, and — since Python
3.9 — calls `loop.shutdown_default_executor()`, which waits for any
`verify_run()` currently in flight on its `asyncio.to_thread` worker
thread to actually finish before returning, rather than abandoning it
mid-write. This analysis has not been exercised against a live NSSM stop
on the real regression machine — it rests on Python's documented
`asyncio.run()` behavior, not on an observed test run, and is worth
confirming once the service is actually deployed this way.

The install script configures NSSM's `AppStopMethodConsole` timeout to
60 seconds specifically to give that executor drain time to complete
before NSSM escalates to terminating the process outright.

### Crash recovery, not stop recovery
The install script sets `AppExit Default Restart` with a 15-second
delay: if the Python process exits on its own (a crash — Phase 3's
per-run exception handling, ADR-022's addendum, means this should mostly
be run-level failures now, not whole-service crashes, but it's not
impossible), NSSM restarts it. This does **not** apply to a deliberate
`nssm stop` / `Stop-Service` — NSSM only invokes the exit-action policy
when the monitored process exits while the service isn't being
intentionally stopped, so stopping the service for maintenance behaves
as expected (it stays stopped).

### Logging
NSSM redirects the child process's stdout/stderr — which is everything
`main.py` currently communicates with, since it only ever uses
`print()` — to `logs/service_stdout.log` / `logs/service_stderr.log`
under the repo root, with basic size-based rotation (10 MB). `logs/` is
gitignored. This is the only way to see what the service is doing once
it's not running in a visible terminal; there is no structured logging
today (everything is a `print()` call) — worth a future improvement, but
out of scope here.

## Addendum (session 15, GitHub Copilot PR review)

A round of PR review surfaced five comments on the shutdown handling and
both scripts.

**Comment on `main.py`'s shutdown (raised, not yet fixed — open
decision):** on Ctrl+C, `asyncio.run()` cancels the task awaiting
`asyncio.to_thread(verify_run, ...)` even though executor shutdown still
waits for the worker thread to finish. `verify_run()`'s DB writes
complete (nothing is lost), but the cancellation unwinds past
`on_confirmed()`'s `try/except Exception`/`else` entirely —
`CancelledError` is a `BaseException`, not an `Exception` — so
`_archive(run_id, processed_dir)` never runs. The manifest is left
unarchived even though the DB already has the run recorded, and
`stamp_manifest_for_run.py`'s safety check then refuses every future
dispatch until a human notices and moves the file by hand.

Discussed rather than immediately fixed: is this worth the cost of
proper in-flight-task tracking, given the service is meant to run
unattended in the background? Conclusion: yes, it can still matter,
because a stop signal doesn't require anyone to be paying attention —
a Windows Update reboot sends every service a stop signal automatically,
translated by NSSM into the same Ctrl+C-style signal this service
catches. But the actual damage is bounded: no data is lost (verify_run's
writes already completed), and the failure isn't silent forever — the
next dispatch attempt fails loudly, naming the stuck file.

**Fixed (session 16)** with the cheaper, more general mitigation
discussed above rather than full task-tracking through shutdown: a new
`_reconcile_processed_manifests()` in `run_service()`, run once at
startup before anything is registered as "expected." It scans
`manifests_dir`'s top level (same `context_manifest_*.json` glob as
`manifest_watcher.py` — not narrowed to `*_run_*` names) and, for any
manifest whose `run_id` is already in `processed_run_ids`, moves it
straight to `processed/`. A malformed/unreadable file is skipped rather
than erroring — that's `handle_new_manifest`'s own retry-with-backoff
logic's job once the live watcher picks it up normally, not this
function's. This recovers from any cause of an orphaned-but-actually-done
manifest, not just the Ctrl+C race this comment specifically raised (a
hard kill would leave the exact same symptom). Verified against a
scratch manifests_dir with three files — an already-processed run (gets
archived), a still-pending run (correctly left alone), and a malformed
file (skipped without crashing) — all behaving as intended.

**Fixed the same session:**

- **No exit-code checking on any native command.** `$ErrorActionPreference = "Stop"`
  only converts PowerShell's own terminating errors — it does not turn a
  native command's (here, every `nssm` call, plus `python -m venv` and
  `pip install`) nonzero exit code into anything that stops the script.
  A failed `nssm install`/`set`/`stop` could leave the service missing or
  half-configured while `install_verification_service.ps1` still printed
  "configured." Fixed with an `Invoke-Nssm` helper (and a generic
  `Invoke-Checked` for the venv/pip calls) that checks `$LASTEXITCODE`
  immediately after every native call and throws before the script can
  proceed or report success. Verified against a fake `nssm` binary
  returning a controlled nonzero exit code — confirmed the script aborts
  with a clear message rather than continuing.
- **Reconfiguring a running service silently left it stopped.** The
  script always stopped a running service before reconfiguring it, but
  only restarted afterward if `-Start` was explicitly passed — so a
  routine "let me adjust the stop timeout" re-run would leave this
  always-on listener stopped, with dispatched runs never processed,
  until someone happened to notice. Fixed by recording whether the
  service was running before the script touched it and restoring that
  state afterward, independent of `-Start` (which now only matters for a
  fresh install or a service that was already stopped). Verified all five
  state-transition cases (fresh install with/without `-Start`; reconfigure
  of a running/stopped service with/without `-Start`) against the exact
  decision logic in isolation.
- **Buffered stdout hid live log output.** NSSM redirects stdout/stderr
  to a file rather than a terminal, and Python's stdout is block-buffered
  (not line-buffered) whenever it isn't attached to a real terminal — so
  `main.py`'s only form of logging (`print()`) could sit invisibly in a
  buffer well after the fact it describes, undermining the log files as
  a live view into the service. Fixed by adding `-u` (unbuffered) to the
  Python invocation, applied consistently to both the initial `nssm
  install` and the `nssm set ... AppParameters` call that actually takes
  effect either way.
- **Same missing exit-code checks in the uninstall script.** A failed
  `nssm stop` didn't stop the script from attempting `nssm remove`
  anyway, and a failed `nssm remove` didn't stop it from printing "Done"
  with the service still registered. Fixed with the same `Invoke-Nssm`
  pattern. Verified end-to-end against a mocked `nssm`/`Get-Service`: a
  failing stop aborts before remove ever runs, a failing remove aborts
  without ever printing "Done," and the success path behaves as before.

Unlike the previous round (ADR-023's PR review), these fixes were
actually exercised with a real PowerShell interpreter (PowerShell 7,
installed temporarily into this session's own Linux environment) rather
than reasoned through by inspection alone — both scripts parse-check
cleanly, `Invoke-Nssm`'s exit-code handling was tested against a fake
`nssm` returning a controlled failure, and the start/stop state logic was
tested against all five relevant cases in isolation. This still isn't
the same as running the real script against real NSSM and a real Windows
service, which remains unverified.

## Addendum (session 17, GitHub Copilot PR review)

Two more Copilot comments, this time on `_reconcile_processed_manifests()`
itself (the session-16 reconciliation fix above):

- **A structurally malformed-but-valid-JSON manifest crashed startup.**
  The original `except (json.JSONDecodeError, OSError, KeyError)` doesn't
  catch `TypeError`, which is exactly what `manifest["run"]["run_id"]`
  raises when `manifest["run"]` is present but not a dict — `{"run":
  null}` being the concrete example. That contradicts the function's own
  stated promise that a malformed file is skipped, not fatal: one bad
  manifest sitting in `manifests_dir` would abort `run_service()` on
  every single restart. Fixed by adding `TypeError` to the except tuple.
  Verified with a scratch manifest containing `{"run": null}` (skipped,
  no crash) alongside truly invalid JSON and a manifest missing the
  `"run"` key entirely (both still skipped as before).

- **Reconciliation could archive a manifest whose report was never
  written.** `processed_run_ids` only proves `insert_run()` committed.
  `verify_run()` commits `runs`/`experiment_results`/`sample_results` in
  one transaction and calls `write_report()` afterward, separately —
  `write_report()` writes the CSVs and then inserts into `reports` in its
  own transaction (confirmed by reading `src/reporter/reporter.py` and
  `src/database/models.py` directly). A hard kill between those two
  points leaves a `runs` row with no report. Reconciliation was
  archiving on `processed_run_ids` alone, which would have permanently
  hidden that half-finished state — nothing else ever revisits an
  archived manifest.

  Fixed by adding `get_all_reported_run_ids(conn)` to
  `src/database/models.py` (`SELECT DISTINCT run_id FROM reports`,
  backed by the existing `idx_reports_run` index) and loading it in
  `run_service()` alongside `processed_run_ids`, from the same
  connection. `_reconcile_processed_manifests()` now only archives a
  manifest when its `run_id` is in *both* sets; a `run_id` in
  `processed_run_ids` but not `reported_run_ids` is left unarchived and
  logged as a warning for a human to investigate, rather than silently
  disappearing. Leaving it unarchived also means
  `stamp_manifest_for_run.py`'s safety check keeps refusing new runs
  until someone resolves it — the same behavior as before reconciliation
  existed, which is the right default for a state that needs a decision,
  not automatic cleanup.

  Verified against a scratch `manifests_dir` with four cases: a run with
  both a `runs` row and a report (archived), a run with a `runs` row but
  no report (left in place, warning logged), a run in neither set (left
  alone, no warning — the normal still-pending case), and the malformed
  manifests from the fix above (skipped, not crashed) — all in the same
  test run, all behaving as intended.

## Addendum (session 18, GitHub Copilot PR review)

Three more comments; all verified against the code and accurate.

- **State restore skipped on failure (install script).** The "restore the
  prior running state" step only ran on the success path, so a later
  `nssm set` throwing after the service was stopped left the always-on
  listener down. The stop/configure block is now in `try { } finally { }`;
  the `finally` restarts a service that was running before (best-effort,
  never masking the original error) and the original error still
  propagates. `-Start` only applies on success, so a failed configuration
  never starts a service that was stopped. Tested with PowerShell 7 and
  mocked `nssm`/`Get-Service`/`Start-Service` over six cases (running or
  stopped x `set` failing or not x `-Start`); the key case (running, `set`
  fails) ends Running with the error still thrown.
- **Failed restore was only a warning.** If configuration succeeded but
  the restart in the `finally` failed, the script printed a warning and
  still exited successfully with the listener stopped. The failure is now
  recorded and thrown on the success path (when configuration itself
  failed, the original error still propagates untouched). The success
  path also verifies the service is actually `Running` after starting it,
  since NSSM can report a start and the child process still exit at once.
  Tested over nine mock cases, including restart failing, restart
  "succeeding" but the service stopping, and both combined with a
  configuration failure.
- **Malformed manifest hung startup.** Skipping a bad file during
  reconciliation left it in place, so the catch-up watcher passed it to
  `handle_new_manifest()`, which still indexed `manifest["run"]["run_id"]`.
  `{"run": null}` raised `TypeError` before `ready_event.set()` and
  `run_service()` waited forever. Fixed in three layers: a shared
  `_manifest_identity()` validator (raises `ValueError` for any bad shape)
  used by both reconciliation and the handler, which now logs and skips;
  `watch_manifests_dir()` catches per-file callback errors in its startup
  scan so ready is always signalled; and `run_service()` waits on
  "ready or watcher task finished", re-raising the watcher's error instead
  of hanging.
- **Invalid UTF-8.** `read_text()` raises `UnicodeDecodeError`, which is
  neither `JSONDecodeError` nor `OSError`. Reconciliation now catches
  `ValueError` (covers it) and the handler's retry loop catches
  `UnicodeError` (a truncated mid-write multibyte sequence is retryable).

Tested standalone: 12 malformed shapes rejected, invalid-UTF-8 and
`{"run": null}` files skipped, and the real watcher became ready despite a
callback that raised. Not run against the live service or real NSSM.

## What this doesn't do
- **Does not touch `--init` or `--register`.** Those remain interactive,
  manually-run commands — the service wrapper only wraps `--run`.
- **Does not add real service-awareness to `main.py`.** See "Why NSSM"
  above — this is the deliberately shallow option.
- **Does not add structured logging, health checks, or a status
  endpoint.** The service can be observed via `Get-Service`,
  `services.msc`, and the two log files — nothing richer.
- **Does not automate NSSM's own installation.** Installing NSSM itself
  on the regression machine is a one-time manual tooling step, the same
  category of action as installing Python or the pipeline build — not
  something `install_verification_service.ps1` does for you. This is a
  new, additional piece of infrastructure on that machine beyond what
  was already there (the existing services are all native .NET), and
  it's being called out explicitly here and in the README rather than
  buried in a script comment, since a future person setting this machine
  up from scratch needs to know it's required.
- **Does not package any of this into an installer.** The regression
  machine's setup — Python, the venv, NSSM, this service registration,
  the self-hosted GitHub Actions runner (ADR-023) — is currently a
  sequence of manual one-time steps and now some scripts to run by hand.
  Bundling all of this into a proper installer (an MSI, or even just a
  single bootstrap script) is a reasonable future direction once the
  machine's setup requirements stabilize, but is speculative work
  without a second machine to actually validate portability against —
  tracked in STATUS.md, not built here.

## Consequences
- New `scripts/install_verification_service.ps1` and
  `scripts/uninstall_verification_service.ps1`, run manually (as
  Administrator) on the regression machine — not invoked by any GitHub
  Actions workflow, since registering a Windows service is a one-time
  machine-setup action, not a per-run action.
- `src/main.py`'s `run()` now catches `KeyboardInterrupt` for a clean
  shutdown message. No behavior change for `--init` or `--register`.
- `logs/` added to `.gitignore`.
- NSSM must be installed on the regression machine — a new manual
  prerequisite, documented in the README, not present today.
- Once installed, the verification service survives the regression
  machine rebooting and no longer depends on anyone having a terminal
  session open — directly closing the gap that caused session 14's
  original incident.
- Not yet deployed: this has not been run against the real regression
  machine. The PowerShell was written and reasoned through carefully,
  but — same caveat as ADR-023's scripts — nothing here could be
  executed or verified from this session; only the surrounding Python
  (`main.py`'s change) was compile-checked.

## Alternatives considered
- **Task Scheduler** (run at startup / on logon, restart on failure) —
  genuinely simpler (no third-party download), but doesn't produce an
  actual Windows service (no `services.msc` entry, no `Get-Service`
  visibility, no SCM-level stop signal), and doesn't match what
  STATUS.md's Phase 4 checklist already called for. Rejected once it was
  confirmed no existing non-.NET service wrapper convention already
  exists on this machine that Task Scheduler might have better matched.
- **`pywin32` native service** — see "Why NSSM" above. Not rejected
  outright, just deferred; nothing here blocks moving to it later.
- **WinSW** (another generic process-to-service wrapper, common in the
  Java/Jenkins ecosystem) — functionally similar to NSSM. No reason
  surfaced to prefer it over NSSM specifically; NSSM was chosen mainly
  for being the most commonly reached-for tool in this role. If the team
  already has WinSW conventions elsewhere that weren't surfaced during
  this discussion, swapping it in would not require rethinking this
  ADR's actual decisions (stop-method timeout, restart policy, logging),
  only the install script's tool-specific commands.
