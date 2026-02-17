<#
.SYNOPSIS
    Bhutan Forest Stratification Pipeline - PowerShell Launcher

.DESCRIPTION
    Activates the virtual environment and runs the pipeline.
    Must be run from the project root directory.

.PARAMETER Modules
    Specific module IDs to run (e.g. "01 02 03" or "05").

.PARAMETER From
    Start module ID (inclusive range).

.PARAMETER To
    End module ID (inclusive range).

.PARAMETER LogLevel
    Logging verbosity: DEBUG, INFO, WARNING, ERROR. Default: INFO.

.PARAMETER DryRun
    Preview execution plan without running any modules.

.PARAMETER Sequential
    Force single-threaded execution (useful for debugging).

.PARAMETER ContinueOnError
    Continue executing independent modules even if some fail.

.PARAMETER MaxWorkers
    Maximum parallel workers. Default: auto (CPU cores - 1).

.PARAMETER NoProgress
    Suppress progress bars (useful in CI / log-only mode).

.PARAMETER NoCache
    Disable caching, force full rebuild of all modules.

.PARAMETER ClearCache
    Clear module cache before running.

.PARAMETER Profile
    Enable detailed function-level performance profiling.

.EXAMPLE
    # Run full pipeline (parallel by default)
    .\run.ps1

.EXAMPLE
    # Run specific modules
    .\run.ps1 -Modules "05 06 07"

.EXAMPLE
    # Run a range of modules
    .\run.ps1 -From 03 -To 08

.EXAMPLE
    # Dry run to preview execution plan
    .\run.ps1 -DryRun

.EXAMPLE
    # Run with debug logging and continue on error
    .\run.ps1 -LogLevel DEBUG -ContinueOnError

.EXAMPLE
    # Sequential mode (single-threaded, for debugging)
    .\run.ps1 -Sequential -LogLevel DEBUG

.EXAMPLE
    # Clear cache and rerun
    .\run.ps1 -ClearCache

.EXAMPLE
    # Run single module with no cache
    .\run.ps1 -Modules "05" -NoCache
#>

[CmdletBinding()]
param(
    [string]   $Modules       = "",
    [string]   $From          = "",
    [string]   $To            = "",
    [ValidateSet("DEBUG","INFO","WARNING","ERROR")]
    [string]   $LogLevel      = "INFO",
    [switch]   $DryRun,
    [switch]   $Sequential,
    [switch]   $ContinueOnError,
    [int]      $MaxWorkers    = 0,
    [switch]   $NoProgress,
    [switch]   $NoCache,
    [switch]   $ClearCache,
    [switch]   $Profile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Locate project root ──────────────────────────────────────────────────────
$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) {
    $ProjectRoot = (Get-Location).Path
}

# ── Locate virtual environment ───────────────────────────────────────────────
$VenvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
$VenvPython   = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvActivate)) {
    Write-Error @"
Virtual environment not found at: $VenvActivate

Please create it first:
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -e .
"@
    exit 1
}

if (-not (Test-Path $VenvPython)) {
    Write-Error "Python executable not found at: $VenvPython"
    exit 1
}

Write-Host ""
Write-Host "=== Bhutan Forest Stratification Pipeline ===" -ForegroundColor Cyan
Write-Host "Project root : $ProjectRoot"
Write-Host "Python       : $VenvPython"
Write-Host "Log level    : $LogLevel"
Write-Host ""

# ── Build argument list ──────────────────────────────────────────────────────
$PythonArgs = @("-m", "python.run_pipeline")

if ($Modules -ne "") {
    $PythonArgs += "--modules"
    $PythonArgs += ($Modules -split "\s+")
}

if ($From -ne "") {
    $PythonArgs += "--from"
    $PythonArgs += $From
}

if ($To -ne "") {
    $PythonArgs += "--to"
    $PythonArgs += $To
}

$PythonArgs += "--log-level"
$PythonArgs += $LogLevel

if ($DryRun)         { $PythonArgs += "--dry-run" }
if ($Sequential)     { $PythonArgs += "--sequential" }
if ($ContinueOnError){ $PythonArgs += "--continue-on-error" }
if ($NoProgress)     { $PythonArgs += "--no-progress" }
if ($NoCache)        { $PythonArgs += "--no-cache" }
if ($ClearCache) {
    # Clear cache first, then run pipeline (two-step because --clear-cache alone exits)
    Write-Host "Clearing module cache..." -ForegroundColor Yellow
    & $VenvPython -m python.run_pipeline --clear-cache
    Write-Host "Cache cleared. Starting pipeline..." -ForegroundColor Yellow
    $PythonArgs += "--no-cache"
}
if ($Profile)        { $PythonArgs += "--profile" }

if ($MaxWorkers -gt 0) {
    $PythonArgs += "--max-workers"
    $PythonArgs += $MaxWorkers
}

# ── Activate venv and run ────────────────────────────────────────────────────
Push-Location $ProjectRoot
try {
    & $VenvActivate

    Write-Host "Running: python $($PythonArgs -join ' ')" -ForegroundColor Yellow
    Write-Host ""

    & $VenvPython @PythonArgs
    $ExitCode = $LASTEXITCODE

    Write-Host ""
    if ($ExitCode -eq 0) {
        Write-Host "Pipeline finished successfully." -ForegroundColor Green
    } else {
        Write-Host "Pipeline exited with code $ExitCode. Check outputs/_run_logs/ for details." -ForegroundColor Red
    }
    exit $ExitCode
}
finally {
    Pop-Location
}
