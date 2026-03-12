@echo off
chcp 65001 >nul
echo ========================================
echo   InkTrace Novel AI 一键启动脚本
echo   作者：孔利群
echo ========================================
echo.

echo [1/2] 启动后端服务...
start "InkTrace Backend" cmd /c "python main.py"
timeout /t 3 >nul

echo [2/2] 启动前端服务...
start "InkTrace Frontend" cmd /c "cd frontend && npm run dev"

echo.
echo ========================================
echo   服务已启动
echo   后端API: http://127.0.0.1:9527
echo   前端界面: http://localhost:3000
echo ========================================
echo.
pause
