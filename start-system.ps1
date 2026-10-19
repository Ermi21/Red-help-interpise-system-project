# ==============================================================================
# Red Cloud ICT Solutions - Enterprise Operations & RAG Platform
# System Startup Script (PowerShell)
# ==============================================================================
param(
    [switch]$NoBrowser
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Red
Write-Host "    RED CLOUD ICT SOLUTIONS - SYSTEM STARTUP                     " -ForegroundColor White
Write-Host "    Enterprise RAG & Operations Monitoring Platform              " -ForegroundColor Gray
Write-Host "==================================================================" -ForegroundColor Red
Write-Host ""

# 1. Check Docker daemon availability
Write-Host "[1/4] Verifying Docker environment..." -ForegroundColor Cyan
try {
    $null = docker info 2>&1
    Write-Host "  -> Docker daemon is running." -ForegroundColor Green
} catch {
    Write-Host "  -> ERROR: Docker daemon is not running!" -ForegroundColor Red
    Write-Host "     Please start Docker Desktop and try running this script again." -ForegroundColor Yellow
    exit 1
}

# 2. Locate docker-compose.yml
Write-Host "[2/4] Locating Docker Compose configuration..." -ForegroundColor Cyan
$composePath = $null

if (Test-Path "$PSScriptRoot\docker-compose.yml") {
    $composePath = "$PSScriptRoot\docker-compose.yml"
} elseif (Test-Path "$PSScriptRoot\..\docker-compose.yml") {
    $composePath = "$PSScriptRoot\..\docker-compose.yml"
} elseif (Test-Path ".\docker-compose.yml") {
    $composePath = (Resolve-Path ".\docker-compose.yml").Path
} elseif (Test-Path ".\enterprise-db-rag-backend\docker-compose.yml") {
    $composePath = (Resolve-Path ".\enterprise-db-rag-backend\docker-compose.yml").Path
}

if (-not $composePath) {
    Write-Host "  -> ERROR: docker-compose.yml could not be found." -ForegroundColor Red
    exit 1
}

$composeDir = Split-Path -Parent $composePath
Write-Host "  -> Using compose file: $composePath" -ForegroundColor Green

# 3. Start containers
Write-Host "[3/4] Starting Docker services (Postgres, Redis, Ollama, Backend, Frontend)..." -ForegroundColor Cyan
Push-Location $composeDir
try {
    docker compose -f $composePath up -d
} finally {
    Pop-Location
}

# 4. Service readiness probe
Write-Host "[4/4] Verifying service readiness..." -ForegroundColor Cyan
$maxAttempts = 15
$attempt = 1
$backendReady = $false

while ($attempt -le $maxAttempts) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($response -and ($response.status -eq "ok" -or $response.status -eq "degraded")) {
            $backendReady = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 2
    }
    $attempt++
}

if ($backendReady) {
    Write-Host "  -> Backend API is healthy and answering queries." -ForegroundColor Green
} else {
    Write-Host "  -> Notice: Backend is still initializing, should be ready shortly." -ForegroundColor Yellow
}

# 5. Display banner & connection details
Write-Host ""
Write-Host "------------------------------------------------------------------" -ForegroundColor Green
Write-Host "  SYSTEM READY - RED CLOUD ICT SOLUTIONS" -ForegroundColor White
Write-Host "------------------------------------------------------------------" -ForegroundColor Green
Write-Host "  * Web Application (UI) : http://localhost:3000" -ForegroundColor White
Write-Host "  * Alternate Port       : http://localhost:5173" -ForegroundColor Gray
Write-Host "  * Backend API          : http://localhost:8000" -ForegroundColor White
Write-Host "  * Interactive Swagger  : http://localhost:8000/docs" -ForegroundColor White
Write-Host "  * Liveness Probe       : http://localhost:8000/health" -ForegroundColor Gray
Write-Host ""
Write-Host "  DEFAULT LOGIN CREDENTIALS:" -ForegroundColor Yellow
Write-Host "    Username / Email : superadmin@company.com  (or 'admin')" -ForegroundColor White
Write-Host "    Password         : admin123" -ForegroundColor White
Write-Host "------------------------------------------------------------------" -ForegroundColor Green
Write-Host ""

# Open in browser if not explicitly suppressed
if (-not $NoBrowser) {
    if ([Environment]::UserInteractive -and -not [Console]::IsInputRedirected) {
        $openBrowser = Read-Host "Would you like to open the application in your browser now? (Y/n)"
        if ($openBrowser -eq "" -or $openBrowser -match "^[Yy]") {
            Start-Process "http://localhost:3000"
        }
    } else {
        Start-Process "http://localhost:3000"
    }
}
