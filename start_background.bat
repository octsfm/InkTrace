@echo off
echo ========================================
echo   InkTrace Novel AI - Start Background
echo ========================================
echo.

set INKTRACE_PORT=9527
set INKTRACE_HOST=127.0.0.1

echo Starting service in background...
echo Address: http://%INKTRACE_HOST%:%INKTRACE_PORT%
echo.

start /b python main.py > logs\service.log 2>&1

echo Service started in background.
echo Log file: logs\service.log
echo.
echo Use stop.bat to stop the service.
pause
