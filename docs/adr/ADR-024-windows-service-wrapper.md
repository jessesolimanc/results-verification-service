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
