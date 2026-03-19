@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0\.."

echo ========================================
echo InkTrace 一键打包 + 冒烟检查
echo ========================================

echo.
echo [1/3] 执行桌面打包...
call build-desktop.bat
if %errorlevel% neq 0 (
  echo.
  echo [ERROR] 打包失败，错误码=%errorlevel%
  pause
  exit /b %errorlevel%
)

echo.
echo [2/3] 清理9527残留并启动后端...
call ".\scripts\one_click_recover_9527.bat"
if %errorlevel% neq 0 (
  echo.
  echo [ERROR] 后端恢复失败，错误码=%errorlevel%
  pause
  exit /b %errorlevel%
)

echo.
echo [3/3] 完成：打包成功且接口冒烟通过
echo 可执行文件请查看 dist 目录
echo ========================================
pause
