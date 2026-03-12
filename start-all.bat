@echo off
echo ========================================
echo   InkTrace Novel AI - Start All
echo ========================================
echo.

set INKTRACE_PORT=9527
set INKTRACE_HOST=127.0.0.1

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not found
    pause
    exit /b 1
)
echo       Python OK

echo.
echo [2/4] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Node.js not found
    pause
    exit /b 1
)
echo       Node.js OK

echo.
echo [3/4] Starting backend service...
echo       Backend: http://%INKTRACE_HOST%:%INKTRACE_PORT%
start "InkTrace Backend" /min cmd /c "set INKTRACE_PORT=9527 && python main.py"

echo.
echo [4/4] Starting frontend...
echo       Frontend: http://localhost:3000
cd frontend
start "InkTrace Frontend" /min cmd /c "npm run dev"
cd ..

echo.
echo ========================================
echo   Services started!
echo   Backend:  http://127.0.0.1:9527
echo   Frontend: http://localhost:3000
echo ========================================
echo.
echo Use stop.bat to stop all services.
pause
