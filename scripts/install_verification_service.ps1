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
  If set, starts the service immediately after registering it. Otherwise
  the service is left stopped so you can review it in services.msc first.
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

Write-Host "Repo root:   $RepoRoot"
Write-Host "Service name: $ServiceName"

# --- Sanity checks -----------------------------------------------------

try {
    & $NssmPath version | Out-Null
} catch {
    $msg = "Could not run '$NssmPath'. Install NSSM (https://nssm.cc) and " +
        "either put nssm.exe on PATH or pass -NssmPath <path-to-nssm.exe>."
    Write-Error $msg
    exit 1
}

if (-not (Test-Path $PythonExe)) {
    Write-Host "No .venv found at $PythonExe — creating one and installing dependencies..."
    python -m venv (Join-Path $RepoRoot ".venv")
    & $PythonExe -m pip install --quiet -r (Join-Path $RepoRoot "requirements.txt")
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

# --- Install or reconfigure ---------------------------------------------

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Service '$ServiceName' already exists — reconfiguring in place."
    if ($existing.Status -eq "Running") {
        Write-Host "Stopping it first..."
        & $NssmPath stop $ServiceName
    }
} else {
    Write-Host "Installing new service '$ServiceName'..."
    & $NssmPath install $ServiceName $PythonExe "-m src.main --run"
}

# These `nssm set` calls run regardless of whether the service was just
# installed or already existed, so re-running this script always leaves
# the service in the same known configuration.
& $NssmPath set $ServiceName AppDirectory $RepoRoot
& $NssmPath set $ServiceName AppParameters "-m src.main --run"
& $NssmPath set $ServiceName DisplayName "Countable PCR Results Verification Service"
& $NssmPath set $ServiceName Description "Always-on listener/orchestrator for the PCR regression verification service (ADR-015). See docs/adr in the repo."
& $NssmPath set $ServiceName Start SERVICE_AUTO_START

# Logs — NSSM redirects the child process's stdout/stderr (main.py's
# plain print() calls) to these files, with basic rotation so they don't
# grow forever.
& $NssmPath set $ServiceName AppStdout (Join-Path $LogsDir "service_stdout.log")
& $NssmPath set $ServiceName AppStderr (Join-Path $LogsDir "service_stderr.log")
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName AppRotateOnline 1
& $NssmPath set $ServiceName AppRotateBytes 10485760   # 10 MB per file

# Stop behavior: try a Ctrl+C-style console signal first (main.py now
# catches this cleanly — see the run() docstring) and give it up to 60s,
# since asyncio.run()'s shutdown waits for any in-flight verify_run() to
# actually finish before returning. Window-message and thread-message
# stop methods don't apply to a console app with no window, so leave
# their (short) defaults — NSSM will fall through them quickly and, if
# the process still hasn't exited after all methods are tried, terminate
# it outright as a last resort.
& $NssmPath set $ServiceName AppStopMethodConsole 60000

# Crash recovery: if the process exits on its own (not via a deliberate
# `nssm stop`/`Stop-Service`), restart it after a short delay rather than
# immediately — avoids a tight crash loop if something is wrong at
# startup (e.g. the pipeline DB is unreachable).
& $NssmPath set $ServiceName AppExit Default Restart
& $NssmPath set $ServiceName AppRestartDelay 15000

Write-Host ""
Write-Host "Service '$ServiceName' configured."
Write-Host "  Logs:   $LogsDir"
Write-Host "  Review it in services.msc, or:"
Write-Host "    Start-Service $ServiceName"
Write-Host "    Get-Service $ServiceName"
Write-Host "    Stop-Service $ServiceName"

if ($Start) {
    Write-Host "Starting service..."
    Start-Service $ServiceName
    Start-Sleep -Seconds 2
    Get-Service $ServiceName
}
