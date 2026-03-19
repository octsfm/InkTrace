@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0\.."
for /f "tokens=5" %%a in ('netstat -ano ^| findstr LISTENING ^| findstr :9527') do (
  if not "%%a"=="0" (
    taskkill /PID %%a /F >nul 2>nul
  )
)
echo [DONE] 端口9527清理完成
exit /b 0
