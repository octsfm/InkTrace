@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set "PYTHON_CMD="
echo ========================================
echo   InkTrace Novel AI - Start Background
echo ========================================
echo.

set INKTRACE_PORT=9527
set INKTRACE_HOST=127.0.0.1

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
) else (
    python --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo [Error] Python not found
    pause
    exit /b 1
)

echo Starting service in background...
echo Address: http://%INKTRACE_HOST%:%INKTRACE_PORT%
echo.

if not exist logs mkdir logs

start /b %PYTHON_CMD% main.py > logs\service.log 2>&1

echo Service started in background.
echo Log file: logs\service.log
echo.
echo Use stop.bat to stop the service.
pause
