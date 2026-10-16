# =====================================================================
# Redcloud Enterprise DB RAG Assistant - Startup Script
# Run this script every time you start your PC and open VS Code:
#   .\start-system.ps1
# =====================================================================

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host " Starting Redcloud Enterprise DB RAG System...        " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# 1. Check if Docker is running
docker info > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker Desktop is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop on your PC and run this command again." -ForegroundColor Yellow
    exit 1
}

# 2. Start all containers in the background
Write-Host "`n[1/3] Starting Docker containers..." -ForegroundColor Green
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to start containers." -ForegroundColor Red
    exit 1
}

# Start local host metrics daemon on port 9900 if not already running
try {
    $tcp = Get-NetTCPConnection -LocalPort 9900 -ErrorAction SilentlyContinue
    if (-not $tcp) {
        Write-Host " Starting host server metrics telemetry daemon on port 9900..." -ForegroundColor Gray
        Start-Process python -ArgumentList "frontend/local_metrics_server.py" -WindowStyle Hidden
    }
} catch {}

# 3. Wait for services to be ready
Write-Host "`n[2/3] Checking system health..." -ForegroundColor Green
Start-Sleep -Seconds 3

$backendHealthy = $false
for ($i = 1; $i -le 10; $i++) {
    try {
        $res = Invoke-RestMethod -Uri "http://localhost:8000/healthz" -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($res.status -eq "ok") {
            $backendHealthy = $true
            break
        }
    } catch {
        Write-Host "  Waiting for backend service to become ready ($i/10)..." -ForegroundColor Gray
        Start-Sleep -Seconds 2
    }
}

# 4. Display Status & Info
Write-Host "`n[3/3] System Status:" -ForegroundColor Green
docker compose ps

Write-Host "`n======================================================" -ForegroundColor Cyan
if ($backendHealthy) {
    Write-Host " [SUCCESS] Full system is running and ready!          " -ForegroundColor Green
} else {
    Write-Host " [NOTICE] Containers started, backend warming up...   " -ForegroundColor Yellow
}
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host " Frontend Web UI:  http://localhost:5173/Redcloud/login" -ForegroundColor White
Write-Host " Backend API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host " Username:         admin (or admin@company.com)" -ForegroundColor White
Write-Host " Password:         admin123" -ForegroundColor White
Write-Host "======================================================" -ForegroundColor Cyan

# 5. Automatically open the frontend dashboard in the default browser
Start-Process "http://localhost:5173/Redcloud/login"
