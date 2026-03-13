@echo off
REM InkTrace Desktop Build Script
REM Author: Kong Liqun

echo ========================================
echo InkTrace Desktop Build Script
echo ========================================

echo.
echo [1/4] Building frontend...
cd frontend
call npm install
call npm run build
cd ..

echo.
echo [2/4] Installing Electron dependencies...
call npm install

echo.
echo [3/4] Building backend with PyInstaller...
pip install pyinstaller
pyinstaller --onefile --name inktrace-backend --distpath backend --workpath build --specpath build main.py

echo.
echo [4/4] Building Electron app...
call npm run build:win

echo.
echo ========================================
echo Build completed!
echo Output: dist/
echo ========================================
pause
