@echo off
echo ========================================
echo   InkTrace Novel AI - Start Frontend
echo ========================================
echo.

echo [1/2] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Node.js not found, please install Node.js 18+
    pause
    exit /b 1
)
echo       Node.js OK

echo.
echo [2/2] Starting frontend...
echo       Address: http://localhost:3000
echo.

cd frontend
npm run dev
