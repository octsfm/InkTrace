@echo off
chcp 65001 >nul
echo ========================================
echo   InkTrace Novel AI 前端启动脚本
echo   作者：孔利群
echo ========================================
echo.

cd frontend

echo [1/3] 检查Node.js环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Node.js，请先安装Node.js 18+
    pause
    exit /b 1
)
echo       Node.js环境正常

echo.
echo [2/3] 检查依赖包...
if not exist "node_modules" (
    echo       正在安装依赖包...
    npm install
)
echo       依赖包已就绪

echo.
echo [3/3] 启动前端服务...
echo       地址: http://localhost:3000
echo.
echo ========================================
echo   按 Ctrl+C 停止服务
echo ========================================
echo.

npm run dev
