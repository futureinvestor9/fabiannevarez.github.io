# Windows setup (Invariant 11). Creates a venv and installs the package.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m jobsearch_os.cli doctor
Write-Host "`nSetup complete. Try:  python -m jobsearch_os.cli accept-phase1"
