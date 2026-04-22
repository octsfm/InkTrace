@echo off
setlocal
cd /d "%~dp0\.."

echo ========================================
echo Long Form Strategy Acceptance
echo ========================================
echo.
echo [1/3] Recover backend on 9527...
call ".\scripts\one_click_recover_9527.bat"
if %errorlevel% neq 0 (
  echo [ERROR] Backend recover failed: %errorlevel%
  exit /b %errorlevel%
)

echo.
echo [2/3] Run long-form strategy replay (8k/32k compare)...
python ".\scripts\long_form_strategy_replay.py" --base-url http://127.0.0.1:9527 --compare --timeout-sec 1200
if %errorlevel% neq 0 (
  echo [ERROR] Long-form replay failed: %errorlevel%
  exit /b %errorlevel%
)

echo.
echo [3/3] PASS
echo [OK] Long-form strategy acceptance passed.
echo ========================================
exit /b 0
