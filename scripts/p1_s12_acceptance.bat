@echo off
setlocal
cd /d "%~dp0\.."

echo ========================================
echo P1-S12 Acceptance
echo ========================================
echo.
echo [1/4] Run P1 mainline E2E regression...
python -m pytest tests/ai/test_p1_e2e.py tests/ai/test_planning_api.py tests/ai/test_candidate_draft_api.py tests/ai/test_ai_review_api.py tests/ai/test_ai_suggestion_api.py tests/ai/test_conflicts_api.py tests/ai/test_memory_revision_api.py tests/ai/test_agent_trace_api.py -q
if %errorlevel% neq 0 (
  echo [ERROR] P1 mainline E2E regression failed: %errorlevel%
  exit /b %errorlevel%
)

echo.
echo [2/4] Run backend AI full regression...
python -m pytest tests/ai -q
if %errorlevel% neq 0 (
  echo [ERROR] Backend AI full regression failed: %errorlevel%
  exit /b %errorlevel%
)

echo.
echo [3/4] Run frontend full regression...
cd /d "%~dp0\..\frontend"
npm test
if %errorlevel% neq 0 (
  echo [ERROR] Frontend full regression failed: %errorlevel%
  exit /b %errorlevel%
)

echo.
echo [4/4] Build frontend production bundle...
npm run build
if %errorlevel% neq 0 (
  echo [ERROR] Frontend build failed: %errorlevel%
  exit /b %errorlevel%
)

echo.
echo [OK] P1-S12 acceptance passed.
echo ========================================
exit /b 0
