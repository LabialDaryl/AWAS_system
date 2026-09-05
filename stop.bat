@echo off
cd /d "%~dp0"

echo ===================================================
echo        AWAS - Stopping Development Server          
echo ===================================================
echo.

set "STOPPED=0"

:: 1. Terminate processes listening on port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /r ":8000\>" ^| findstr "LISTENING"') do (
    if not "%%a"=="" if not "%%a"=="0" (
        echo [INFO] Stopping process with PID %%a listening on port 8000...
        taskkill /F /PID %%a >nul 2>&1
        set "STOPPED=1"
    )
)

:: 2. Terminate any lingering manage.py runserver processes
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*manage.py*runserver*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo.
echo [SUCCESS] AWAS server processes on port 8000 have been stopped.
echo ===================================================
