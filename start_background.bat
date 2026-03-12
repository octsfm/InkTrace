@echo off
chcp 65001 >nul
echo ========================================
echo   InkTrace Novel AI 后台启动脚本
echo   作者：孔利群
echo ========================================
echo.

REM 设置端口（可修改）
set INKTRACE_PORT=9527
set INKTRACE_HOST=127.0.0.1

echo [1/2] 检查服务是否已运行...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%INKTRACE_PORT% ^| findstr LISTENING') do (
    echo [警告] 端口 %INKTRACE_PORT% 已被占用
    pause
    exit /b 1
)

echo [2/2] 后台启动服务...
echo       地址: http://%INKTRACE_HOST%:%INKTRACE_PORT%
echo       文档: http://%INKTRACE_HOST%:%INKTRACE_PORT%/docs
echo       日志: logs\inktrace.log
echo.

if not exist logs mkdir logs
start /B python main.py > logs\inktrace.log 2>&1

timeout /t 2 >nul
echo       服务已后台启动
echo.
echo ========================================
echo   使用 stop.bat 停止服务
echo ========================================
pause
