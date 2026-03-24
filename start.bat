@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set "PYTHON_CMD="
echo ========================================
echo   InkTrace Novel AI - Start Service
echo ========================================
echo.

REM Set port (can be modified)
set INKTRACE_PORT=9527
set INKTRACE_HOST=127.0.0.1

echo [1/3] Checking Python environment...
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
) else (
    python --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    echo [Error] Python not found, please install Python 3.11+ or Python Launcher
    pause
    exit /b 1
)
echo       Python OK

echo.
echo [2/3] Checking dependencies...
%PYTHON_CMD% -m pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo       Installing dependencies...
    %PYTHON_CMD% -m pip install fastapi uvicorn httpx pydantic -q
)
echo       Dependencies OK

echo.
echo [3/3] Starting service...
echo       Address: http://%INKTRACE_HOST%:%INKTRACE_PORT%
echo       API Docs: http://%INKTRACE_HOST%:%INKTRACE_PORT%/docs
echo.
echo ========================================
echo   Press Ctrl+C to stop
echo ========================================
echo.

%PYTHON_CMD% main.py
