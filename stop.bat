@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ========================================
echo   InkTrace Novel AI - Stop All Services
echo ========================================
echo.

set BACKEND_PORT=9527
set FRONTEND_PORT=3000
set "FOUND_ANY="

echo [1/3] Stopping backend on port %BACKEND_PORT%...
call :stop_port %BACKEND_PORT% "Backend"

echo.
echo [2/3] Stopping frontend on port %FRONTEND_PORT%...
call :stop_port %FRONTEND_PORT% "Frontend"

echo.
echo [3/3] Summary...
if defined FOUND_ANY (
    echo       Matching service processes have been stopped
) else (
    echo       No running backend/frontend processes were found on ports %BACKEND_PORT% / %FRONTEND_PORT%
)

echo.
echo ========================================
echo   Done
echo ========================================
pause
exit /b 0

:stop_port
set "TARGET_PORT=%~1"
set "SERVICE_NAME=%~2"
set "PORT_FOUND="

for /f "tokens=5" %%a in ('netstat -ano ^| findstr LISTENING ^| findstr :%TARGET_PORT%') do (
    if not "%%a"=="0" (
        set "PORT_FOUND=1"
        set "FOUND_ANY=1"
        echo       Found !SERVICE_NAME! PID: %%a
        taskkill /F /T /PID %%a >nul 2>&1
        if errorlevel 1 (
            echo       [Warning] Failed to stop PID %%a
        ) else (
            echo       !SERVICE_NAME! process tree stopped
        )
    )
)

if not defined PORT_FOUND (
    echo       No running !SERVICE_NAME! found on port %TARGET_PORT%
)

exit /b 0
