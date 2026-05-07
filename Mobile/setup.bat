@echo off
echo ========================================
echo    Roe's POS Mobile App Setup Script
echo ========================================
echo.

cd /d "%~dp0"

echo Checking Node.js installation...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed. Please install Node.js 16+ first.
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)

echo Checking npm installation...
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: npm is not installed. Please reinstall Node.js.
    pause
    exit /b 1
)

echo.
echo Installing dependencies...
npm install

if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Configure API endpoint in Redux slices
echo 2. For Android: Install Android Studio and SDK
echo 3. For iOS: Install Xcode (macOS only)
echo 4. Run: npm run android  (or npm run ios)
echo.
echo See README.md for detailed instructions.
echo.
pause