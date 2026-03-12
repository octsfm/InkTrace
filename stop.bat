@echo off
chcp 65001 >nul
echo ========================================
echo   InkTrace Novel AI 服务停止脚本
echo   作者：孔利群
echo ========================================
echo.

echo [1/2] 查找运行中的服务...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :9527 ^| findstr LISTENING') do (
    set PID=%%a
)

if defined PID (
    echo       找到服务进程 PID: %PID%
    echo.
    echo [2/2] 停止服务...
    taskkill /F /PID %PID% >nul 2>&1
    if errorlevel 1 (
        echo       [警告] 无法停止进程，可能需要管理员权限
    ) else (
        echo       服务已停止
    )
) else (
    echo       未找到运行中的服务
)

echo.
echo ========================================
echo   完成
echo ========================================
pause
