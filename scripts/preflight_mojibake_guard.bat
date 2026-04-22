@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0\.."

echo [mojibake-guard] scanning source literals...
python ".\scripts\detect_mojibake_literals.py" .
if %errorlevel% neq 0 (
  echo [mojibake-guard] failed
  exit /b %errorlevel%
)

echo [mojibake-guard] passed
exit /b 0
