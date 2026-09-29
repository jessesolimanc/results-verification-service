<#
.SYNOPSIS
  Stops and removes the results-verification-service Windows Service
  (see install_verification_service.ps1 / ADR-024).

  Does NOT touch the repo, the venv, the database, or any manifests/
  reports — only the NSSM-registered service entry itself.
#>
param(
    [string]$ServiceName = "ResultsVerificationService",
    [string]$NssmPath = "nssm"
)

$ErrorActionPreference = "Stop"

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $existing) {
    Write-Host "No service named '$ServiceName' found — nothing to do."
    exit 0
}

if ($existing.Status -eq "Running") {
    Write-Host "Stopping '$ServiceName'..."
    & $NssmPath stop $ServiceName
    Start-Sleep -Seconds 2
}

Write-Host "Removing '$ServiceName'..."
& $NssmPath remove $ServiceName confirm

Write-Host "Done. Service '$ServiceName' removed. Logs under the repo's logs\ directory were left in place."
