@echo off
echo ========================================
echo   InkTrace Novel AI - Start Service
echo ========================================
echo.

REM Set port (can be modified)
set INKTRACE_PORT=9527
set INKTRACE_HOST=127.0.0.1

echo [1/3] Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not found, please install Python 3.11+
    pause
    exit /b 1
)
echo       Python OK

echo.
echo [2/3] Checking dependencies...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo       Installing dependencies...
    pip install fastapi uvicorn httpx pydantic -q
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

python main.py
