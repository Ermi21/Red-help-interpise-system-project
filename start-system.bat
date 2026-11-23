@echo off
REM ==============================================================================
REM Red Cloud ICT Solutions - System Startup Wrapper
REM Bypasses PowerShell ExecutionPolicy restrictions automatically
REM ==============================================================================

if not exist "backend\.env" (
    copy "backend\.env.example" "backend\.env" >nul 2>&1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-system.ps1" %*
