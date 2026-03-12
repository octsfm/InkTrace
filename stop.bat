@echo off
echo ========================================
echo   InkTrace Novel AI - Stop Service
echo ========================================
echo.

echo [1/2] Finding running service...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :9527 ^| findstr LISTENING') do (
    set PID=%%a
)

if defined PID (
    echo       Found service PID: %PID%
    echo.
    echo [2/2] Stopping service...
    taskkill /F /PID %PID% >nul 2>&1
    if errorlevel 1 (
        echo       [Warning] Cannot stop process, may need admin rights
    ) else (
        echo       Service stopped
    )
) else (
    echo       No running service found on port 9527
)

echo.
echo ========================================
echo   Done
echo ========================================
pause
