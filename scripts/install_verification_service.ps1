<#
.SYNOPSIS
  Registers the results-verification-service as a Windows Service, using
  NSSM (https://nssm.cc) as the wrapper. See ADR-024 for why NSSM and not
  a native pywin32 service.

.DESCRIPTION
  NSSM's job is to give the Service Control Manager (SCM) something that
  actually speaks its protocol (start/stop/status), since plain
  `python.exe` does not. NSSM registers ITSELF as the service and, under
  the hood, launches and supervises `python -m src.main --run` as a
  child process — the SCM only ever talks to NSSM, never to Python
  directly.

  This script is idempotent: re-running it against an already-registered
  service reconfigures it in place (via `nssm set`) rather than failing.
  A service that was running before this script touched it is restarted
  afterward; one that was stopped is left stopped unless -Start is
  passed — reconfiguring should never silently leave an always-on
  listener stopped (PR review, session 15).

  Every native command (nssm, python, pip) has its exit code checked
  immediately — PowerShell's $ErrorActionPreference does NOT turn a
  nonzero exit code from a native command into a terminating error on
  its own, so without this, a failed nssm call could leave the service
  missing or half-configured while the script still prints success
  (PR review, session 15).

  Run this ONCE per machine, as Administrator, after:
    1. NSSM is installed (see ADR-024 / README — this is a manual,
       one-time tooling setup step, not something this script installs
       for you).
    2. `python -m src.main --init` has been run at least once (the
       database must already exist — this script does not initialise
       it).

.PARAMETER ServiceName
  Windows service name. Shows up in services.msc and `Get-Service`.

.PARAMETER NssmPath
  Path to nssm.exe. Defaults to assuming it's on PATH.

.PARAMETER Start
  Start the service after registering it, even if it was stopped before
  this script ran (e.g. a first-ever install). Has no effect on whether
  a service that WAS already running gets restarted — that always
  happens regardless of this switch, so a routine reconfigure never
  leaves the service stopped.
#>
param(
    [string]$ServiceName = "ResultsVerificationService",
    [string]$NssmPath = "nssm",
    [switch]$Start
)

$ErrorActionPreference = "Stop"

# Repo root is this script's parent directory (scripts/ lives at the repo
# top level).
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$LogsDir = Join-Path $RepoRoot "logs"

# -u: run Python unbuffered. NSSM redirects stdout/stderr to a file, not
# a terminal, and Python's stdout is block-buffered (not line-buffered)
# whenever it isn't attached to a real terminal — so without -u, print()
# output (main.py's only form of logging) can sit invisibly in a buffer
# for a long time before it's actually written to the log file, making
# the only live view into the running service unreliable (PR review,
# session 15).
$ServiceArgs = "-u -m src.main --run"

Write-Host "Repo root:    $RepoRoot"
Write-Host "Service name: $ServiceName"

# --- Helpers -------------------------------------------------------------

function Invoke-Nssm {
    # Runs nssm with the given arguments and aborts the whole script if
    # it returns a nonzero exit code. $LASTEXITCODE reflects only the
    # most recently run *native* command, so this check must happen
    # immediately after the call, before any other native command runs.
    & $NssmPath @Args
    if ($LASTEXITCODE -ne 0) {
        throw "nssm $($Args -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory)][string]$Description,
        [Parameter(Mandatory)][scriptblock]$ScriptBlock
    )
    & $ScriptBlock
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE"
    }
}

# --- Sanity checks ---------------------------------------------------------

try {
    Invoke-Nssm version | Out-Null
} catch {
    $msg = "Could not run '$NssmPath'. Install NSSM (https://nssm.cc) and " +
        "either put nssm.exe on PATH or pass -NssmPath <path-to-nssm.exe>."
    Write-Error $msg
    exit 1
}

if (-not (Test-Path $PythonExe)) {
    Write-Host "No .venv found at $PythonExe — creating one and installing dependencies..."
    Invoke-Checked "python -m venv" { python -m venv (Join-Path $RepoRoot ".venv") }
    Invoke-Checked "pip install" {
        & $PythonExe -m pip install --quiet -r (Join-Path $RepoRoot "requirements.txt")
    }
}

$ConfigPath = Join-Path $RepoRoot "config\local_config.yaml"
if (-not (Test-Path $ConfigPath)) {
    $configMsg = "config\local_config.yaml not found - the service will fall " +
        "back to config\config.yaml. If this machine needs its own local " +
        "overrides (it almost certainly does - see README), create " +
        "local_config.yaml before starting the service."
    Write-Warning $configMsg
}

New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

# --- Install or reconfigure ------------------------------------------------

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
$wasRunning = $false

if ($existing) {
    Write-Host "Service '$ServiceName' already exists — reconfiguring in place."
    $wasRunning = ($existing.Status -eq "Running")
    if ($wasRunning) {
        Write-Host "Stopping it first..."
        Invoke-Nssm stop $ServiceName
    }
} else {
    Write-Host "Installing new service '$ServiceName'..."
    Invoke-Nssm install $ServiceName $PythonExe $ServiceArgs
}

# These `nssm set` calls run regardless of whether the service was just
# installed or already existed, so re-running this script always leaves
# the service in the same known configuration.
Invoke-Nssm set $ServiceName AppDirectory $RepoRoot
Invoke-Nssm set $ServiceName AppParameters $ServiceArgs
Invoke-Nssm set $ServiceName DisplayName "Countable PCR Results Verification Service"
Invoke-Nssm set $ServiceName Description "Always-on listener/orchestrator for the PCR regression verification service (ADR-015). See docs/adr in the repo."
Invoke-Nssm set $ServiceName Start SERVICE_AUTO_START

# Logs — NSSM redirects the child process's stdout/stderr (main.py's
# plain print() calls) to these files, with basic rotation so they don't
# grow forever.
Invoke-Nssm set $ServiceName AppStdout (Join-Path $LogsDir "service_stdout.log")
Invoke-Nssm set $ServiceName AppStderr (Join-Path $LogsDir "service_stderr.log")
Invoke-Nssm set $ServiceName AppRotateFiles 1
Invoke-Nssm set $ServiceName AppRotateOnline 1
Invoke-Nssm set $ServiceName AppRotateBytes 10485760   # 10 MB per file

# Stop behavior: try a Ctrl+C-style console signal first (main.py now
# catches this cleanly — see the run() docstring) and give it up to 60s,
# since asyncio.run()'s shutdown waits for any in-flight verify_run() to
# actually finish before returning. Window-message and thread-message
# stop methods don't apply to a console app with no window, so leave
# their (short) defaults — NSSM will fall through them quickly and, if
# the process still hasn't exited after all methods are tried, terminate
# it outright as a last resort.
Invoke-Nssm set $ServiceName AppStopMethodConsole 60000

# Crash recovery: if the process exits on its own (not via a deliberate
# `nssm stop`/`Stop-Service`), restart it after a short delay rather than
# immediately — avoids a tight crash loop if something is wrong at
# startup (e.g. the pipeline DB is unreachable).
Invoke-Nssm set $ServiceName AppExit Default Restart
Invoke-Nssm set $ServiceName AppRestartDelay 15000

Write-Host ""
Write-Host "Service '$ServiceName' configured."
Write-Host "  Logs:   $LogsDir"
Write-Host "  Review it in services.msc, or:"
Write-Host "    Get-Service $ServiceName"
Write-Host "    Stop-Service $ServiceName"

# Restore whatever running state the service had before this script
# touched it — a routine reconfigure of an already-running service must
# not silently leave this always-on listener stopped, since dispatched
# regression runs would then never be picked up (PR review, session 15).
# -Start additionally forces a start for a fresh install / one that was
# already stopped; it has no effect on a service that was already running
# (that case always restarts regardless).
if ($wasRunning -or $Start) {
    Write-Host "Starting service..."
    Start-Service $ServiceName
    Start-Sleep -Seconds 2
    Get-Service $ServiceName
} else {
    Write-Host "Service left stopped (it wasn't running before this script ran, and -Start wasn't passed)."
    Write-Host "  Start it with: Start-Service $ServiceName"
}
