# =====================================================================
# Redcloud Enterprise DB RAG Assistant - Stop Script
# Run this script whenever you want to stop the system:
#   .\stop-system.ps1
# =====================================================================

Write-Host "Stopping Redcloud Enterprise DB RAG containers..." -ForegroundColor Yellow
docker compose stop
Write-Host "All services stopped cleanly." -ForegroundColor Green
