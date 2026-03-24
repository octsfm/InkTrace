@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set "PYTHON_CMD="
echo ========================================
echo   InkTrace Novel AI - Start All
echo ========================================
echo.

set INKTRACE_PORT=9527
set INKTRACE_HOST=127.0.0.1
set FRONTEND_PORT=3000

echo [1/5] Checking Python...
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
echo       Python OK

echo.
echo [2/5] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Node.js not found
    pause
    exit /b 1
)
echo       Node.js OK

echo.
echo [3/5] Recovering ports...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr LISTENING ^| findstr :%INKTRACE_PORT%') do (
    if not "%%a"=="0" (
        taskkill /PID %%a /F >nul 2>nul
    )
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr LISTENING ^| findstr :%FRONTEND_PORT%') do (
    if not "%%a"=="0" (
        taskkill /PID %%a /F >nul 2>nul
    )
)
echo       Port %INKTRACE_PORT% and %FRONTEND_PORT% recovered

echo.
echo [4/5] Starting backend service...
echo       Backend: http://%INKTRACE_HOST%:%INKTRACE_PORT%
start "InkTrace Backend" /min %PYTHON_CMD% main.py

echo       Waiting for backend health check...
set "BACKEND_READY="
for /l %%i in (1,1,90) do (
    %PYTHON_CMD% -c "import sys, urllib.request; r=urllib.request.urlopen('http://%INKTRACE_HOST%:%INKTRACE_PORT%/health', timeout=2); sys.exit(0 if getattr(r, 'status', 200)==200 else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "BACKEND_READY=1"
        goto backend_ready
    )
    timeout /t 1 /nobreak >nul
)
:backend_ready
if defined BACKEND_READY (
    echo       Backend is healthy
) else (
    echo       [Error] Backend health check timed out, startup aborted
    echo       Please run scripts\one_click_recover_9527.bat and retry
    pause
    exit /b 1
)

echo.
echo [5/5] Starting frontend...
echo       Frontend: http://localhost:%FRONTEND_PORT%
cd frontend
start "InkTrace Frontend" /min cmd /c "chcp 65001 >nul && npm run dev -- --port %FRONTEND_PORT% --strictPort"
cd ..

echo.
echo ========================================
echo   Services started!
echo   Backend:  http://127.0.0.1:9527
echo   Frontend: http://localhost:%FRONTEND_PORT%
echo ========================================
echo.
echo Use stop.bat to stop all services.
pause
