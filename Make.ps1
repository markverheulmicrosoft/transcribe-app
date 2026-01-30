<#
.SYNOPSIS
    PowerShell equivalent of Makefile for Windows users.

.DESCRIPTION
    Run development commands using: .\Make.ps1 <target>
    Example: .\Make.ps1 run

.PARAMETER Target
    The command to run. Default: help
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("help", "install", "dev", "run", "test", "test-cov", "lint", "format", "typecheck", "clean")]
    [string]$Target = "help"
)

function Show-Help {
    Write-Host ""
    Write-Host "Transcribe App - Development Commands" -ForegroundColor Cyan
    Write-Host "=====================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\Make.ps1 <target>" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Targets:"
    Write-Host "  help       Show this help message"
    Write-Host "  install    Install production dependencies"
    Write-Host "  dev        Install all dependencies (including dev)"
    Write-Host "  run        Start the application with hot reload"
    Write-Host "  test       Run tests"
    Write-Host "  test-cov   Run tests with coverage"
    Write-Host "  lint       Run linter (ruff)"
    Write-Host "  format     Format code (ruff)"
    Write-Host "  typecheck  Run type checker (mypy)"
    Write-Host "  clean      Remove cache files and uploads"
    Write-Host ""
}

function Invoke-Install {
    Write-Host "Installing production dependencies..." -ForegroundColor Green
    uv sync --no-dev
}

function Invoke-Dev {
    Write-Host "Installing all dependencies..." -ForegroundColor Green
    uv sync
}

function Invoke-Run {
    Write-Host "Starting application..." -ForegroundColor Green
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

function Invoke-Test {
    Write-Host "Running tests..." -ForegroundColor Green
    uv run pytest -v
}

function Invoke-TestCov {
    Write-Host "Running tests with coverage..." -ForegroundColor Green
    uv run pytest --cov=app --cov-report=term-missing --cov-report=html
}

function Invoke-Lint {
    Write-Host "Running linter..." -ForegroundColor Green
    uv run ruff check app tests
}

function Invoke-Format {
    Write-Host "Formatting code..." -ForegroundColor Green
    uv run ruff format app tests
    uv run ruff check --fix app tests
}

function Invoke-Typecheck {
    Write-Host "Running type checker..." -ForegroundColor Green
    uv run mypy app
}

function Invoke-Clean {
    Write-Host "Cleaning up..." -ForegroundColor Green
    
    $foldersToRemove = @(
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "htmlcov",
        ".ruff_cache"
    )
    
    foreach ($folder in $foldersToRemove) {
        Get-ChildItem -Path . -Recurse -Directory -Filter $folder -ErrorAction SilentlyContinue | 
            ForEach-Object {
                Write-Host "  Removing $($_.FullName)"
                Remove-Item -Recurse -Force $_.FullName
            }
    }
    
    # Remove .coverage file
    if (Test-Path ".coverage") {
        Write-Host "  Removing .coverage"
        Remove-Item -Force ".coverage"
    }
    
    # Clean uploads folder (keep folder, remove contents)
    if (Test-Path "uploads") {
        Get-ChildItem -Path "uploads" -File | ForEach-Object {
            Write-Host "  Removing uploads/$($_.Name)"
            Remove-Item -Force $_.FullName
        }
    }
    
    # Remove .venv
    if (Test-Path ".venv") {
        Write-Host "  Removing .venv"
        Remove-Item -Recurse -Force ".venv"
    }
    
    Write-Host "Clean complete!" -ForegroundColor Green
}

# Execute the selected target
switch ($Target) {
    "help"      { Show-Help }
    "install"   { Invoke-Install }
    "dev"       { Invoke-Dev }
    "run"       { Invoke-Run }
    "test"      { Invoke-Test }
    "test-cov"  { Invoke-TestCov }
    "lint"      { Invoke-Lint }
    "format"    { Invoke-Format }
    "typecheck" { Invoke-Typecheck }
    "clean"     { Invoke-Clean }
    default     { Show-Help }
}
