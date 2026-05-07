@echo off
REM Build both Administrator and Client Tkinter executables.
cd /d "%~dp0"
echo Building Administrator executable...
pushd "Administrator"
call build_admin_exe.bat
if errorlevel 1 (
    echo Administrator build failed.
    popd
    exit /b 1
)
popd

echo Building Client executable...
pushd "Client"
call build_client_exe.bat
if errorlevel 1 (
    echo Client build failed.
    popd
    exit /b 1
)
popd
echo.
echo All Tkinter executables built successfully.
pause
