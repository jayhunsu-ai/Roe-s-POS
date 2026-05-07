@echo off
REM Build the Administrator Tkinter app into a single Windows executable.
cd /d "%~dp0"
echo Installing PyInstaller if needed...
python -m pip install --user pyinstaller
echo Building Administrator executable...
python -m PyInstaller --noconfirm --onefile --windowed --icon="Roe's.ico" --name "roes-admin" "admin_app.py"
if errorlevel 1 (
    echo.
    echo ERROR: Build failed.
    pause
    exit /b 1
)
echo.
echo Build complete. Executable is in "%~dp0dist\roes-admin.exe"
pause
