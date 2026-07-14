# Windows Phase-1 acceptance (Section V.1). Runs the isolated end-to-end check.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\accept_phase1.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python -m jobsearch_os.cli accept-phase1
exit $LASTEXITCODE
