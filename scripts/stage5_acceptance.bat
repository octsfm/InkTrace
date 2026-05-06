@echo off
setlocal
cd /d "%~dp0\.."

echo ========================================
echo Stage 5 Acceptance
echo ========================================
echo.
echo [1/4] Run backend Stage 5 regression...
python -m pytest tests/test_v1_work_service.py tests/test_v1_chapter_service.py tests/test_v1_routes_smoke.py
if %errorlevel% neq 0 (
  echo [ERROR] Backend Stage 5 regression failed: %errorlevel%
  exit /b %errorlevel%
)

echo.
echo [2/4] Run frontend Stage 5 regression...
cd /d "%~dp0\..\frontend"
npm test -- src/stores/__tests__/useSaveStateStore.spec.js src/stores/__tests__/useWritingAssetStore.spec.js src/utils/__tests__/localCache.spec.js src/components/workspace/__tests__/OutlinePanel.spec.js src/components/workspace/__tests__/TimelinePanel.spec.js src/components/workspace/__tests__/ForeshadowPanel.spec.js src/components/workspace/__tests__/CharacterPanel.spec.js src/components/workspace/__tests__/VersionConflictModal.spec.js src/views/__tests__/WritingStudio.spec.js
if %errorlevel% neq 0 (
  echo [ERROR] Frontend Stage 5 regression failed: %errorlevel%
  exit /b %errorlevel%
)

echo.
echo [3/4] Run Workbench boundary smoke...
cd /d "%~dp0\.."
python -c "from pathlib import Path; import sys; bad=[]; keywords=('legacy','modelrolerouter','global_memory_summary','outline_draft','used_fallback'); files=list(Path('frontend/src/views').rglob('*.vue'))+list(Path('frontend/src/stores').rglob('*.js'))+list(Path('presentation/api/routers/v1').rglob('*.py'))+list(Path('application/services/v1').rglob('*.py')); [bad.append(f'{path}:{key}') for path in files for key in keywords if key in path.read_text(encoding='utf-8-sig').lower()]; print('boundary smoke ok' if not bad else '\n'.join(bad)); sys.exit(1 if bad else 0)"
if %errorlevel% neq 0 (
  echo [ERROR] Boundary smoke failed: %errorlevel%
  exit /b %errorlevel%
)

echo.
echo [4/4] PASS
echo [OK] Stage 5 acceptance passed.
echo ========================================
exit /b 0
