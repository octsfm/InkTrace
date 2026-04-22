@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0\.."
echo ========================================
echo 一键恢复 9527：清理 + 启动 + 冒烟
echo ========================================

echo.
echo [1/3] 清理端口9527残留进程...
call ".\scripts\one_click_stop_9527.bat" >nul 2>nul
for /f %%a in ('netstat -ano ^| findstr LISTENING ^| findstr :9527') do (
  echo [ERROR] 端口9527仍被占用，请以管理员权限重试
  exit /b 21
)

if not exist ".\logs" mkdir ".\logs"
del /q ".\logs\backend_stdout.log" ".\logs\backend_stderr.log" >nul 2>nul

echo.
echo [2/3] 启动后端...
start "" /b python main.py 1>".\logs\backend_stdout.log" 2>".\logs\backend_stderr.log"

echo.
echo [3/3] 等待健康检查并冒烟...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop'; $ok=$false; $deadline=(Get-Date).AddSeconds(45); while((Get-Date)-lt $deadline){ try{ $r=Invoke-RestMethod -Uri 'http://127.0.0.1:9527/health' -TimeoutSec 3 -ErrorAction Stop; if($r.status -eq 'healthy'){ $ok=$true; break } } catch {}; Start-Sleep -Milliseconds 600 }; if(-not $ok){ exit 28 }; Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:9527/api/projects' -TimeoutSec 8 -ErrorAction Stop | Out-Null; Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:9527/api/novels/' -TimeoutSec 8 -ErrorAction Stop | Out-Null; exit 0"
if %errorlevel% neq 0 (
  echo [ERROR] 后端恢复或冒烟失败，错误码=%errorlevel%
  echo ---- backend stderr tail ----
  powershell -NoProfile -ExecutionPolicy Bypass -Command "if(Test-Path '.\logs\backend_stderr.log'){ Get-Content '.\logs\backend_stderr.log' -Tail 80 }"
  exit /b %errorlevel%
)

echo [OK] 一键恢复完成，后端已就绪：http://127.0.0.1:9527
