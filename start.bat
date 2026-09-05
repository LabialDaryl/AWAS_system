@echo off
title AWAS Water Billing System - Server
cd /d "%~dp0"

echo ===================================================
echo        AWAS - Automated Water Billing System       
echo ===================================================
echo.

:: Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at .\venv
    echo Please create a virtual environment first:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Verify Python can run
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python could not be executed from the virtual environment.
    pause
    exit /b 1
)

echo [INFO] Virtual environment activated.
echo [INFO] Checking database migrations...
python manage.py migrate --check >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Applying pending migrations...
    python manage.py migrate
)

echo.
echo [INFO] Starting Django development server on http://127.0.0.1:8000/
echo [INFO] Press Ctrl+C in this terminal to stop, or run stop.bat
echo ===================================================
echo.

:: Run server directly in this terminal (single terminal execution)
python manage.py runserver 127.0.0.1:8000
