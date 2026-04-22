@echo off
setlocal
cd /d "%~dp0\.."

echo ========================================
echo Workspace Final Acceptance
echo ========================================
echo.
echo [1/4] Recover backend on 9527...
call ".\scripts\one_click_recover_9527.bat"
if %errorlevel% neq 0 (
  echo [ERROR] Backend recover failed: %errorlevel%
  exit /b %errorlevel%
)

echo.
echo [2/4] Check runtime metrics endpoint...
python -c "import json,urllib.request;d=json.loads(urllib.request.urlopen('http://127.0.0.1:9527/metrics/runtime',timeout=8).read().decode());assert 'runtime' in d and 'sqlite' in d;print('metrics ok')"
if %errorlevel% neq 0 (
  echo [ERROR] Metrics endpoint is unavailable
  exit /b %errorlevel%
)

echo.
echo [3/4] Run 10-loop workspace replay...
python ".\scripts\workspace_enter_exit_replay.py" --base-url http://127.0.0.1:9527 --loops 10 --max-p95-ms 800
if %errorlevel% neq 0 (
  echo [ERROR] Replay failed: %errorlevel%
  exit /b %errorlevel%
)

echo.
echo [4/4] PASS
echo [OK] Workspace anti-freeze acceptance passed.
echo ========================================
exit /b 0
