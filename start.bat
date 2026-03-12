@echo off
chcp 65001 >nul
echo ========================================
echo   InkTrace Novel AI 服务启动脚本
echo   作者：孔利群
echo ========================================
echo.

REM 设置端口（可修改）
set INKTRACE_PORT=9527
set INKTRACE_HOST=127.0.0.1

echo [1/3] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.11+
    pause
    exit /b 1
)
echo       Python环境正常

echo.
echo [2/3] 检查依赖包...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo       正在安装依赖包...
    pip install fastapi uvicorn httpx pydantic -q
)
echo       依赖包已就绪

echo.
echo [3/3] 启动服务...
echo       地址: http://%INKTRACE_HOST%:%INKTRACE_PORT%
echo       文档: http://%INKTRACE_HOST%:%INKTRACE_PORT%/docs
echo.
echo ========================================
echo   按 Ctrl+C 停止服务
echo ========================================
echo.

python main.py
