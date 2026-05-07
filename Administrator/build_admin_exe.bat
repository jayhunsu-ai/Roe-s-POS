@echo off
REM Build the Administrator Tkinter app into a single Windows executable.
cd /d "%~dp0"
echo Installing PyInstaller if needed...
python -m pip install --user pyinstaller

echo Preparing icon file...
set "ICON_SOURCE=Roe's.ico"
set "ICON_SAFE=Roes.ico"
if exist "%ICON_SOURCE%" copy /y "%ICON_SOURCE%" "%ICON_SAFE%" >nul

echo Building Administrator executable...
python -m PyInstaller --noconfirm --onefile --windowed --icon="%ICON_SAFE%" --name "roes-admin" "admin_app.py"
set "BUILD_EXIT=%ERRORLEVEL%"
if exist "%ICON_SAFE%" del "%ICON_SAFE%"
if %BUILD_EXIT% neq 0 (
    echo.
    echo ERROR: Build failed.
    pause
    exit /b %BUILD_EXIT%
)
echo.
echo Build complete. Executable is in "%~dp0dist\roes-admin.exe"
pause
