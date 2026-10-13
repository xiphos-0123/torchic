@echo off
setlocal
cd /d "%~dp0"
title Torchic Setup

echo ============================================================
echo  TORCHIC - FIRST-TIME SETUP
echo ============================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher ^(py.exe^) was not found.
    echo Install 64-bit Python 3.10 or newer, then run this again.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python environment...
    py -3 -m venv .venv
    if errorlevel 1 goto :fail
)

echo Updating pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo Installing Torchic requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo.
echo Setup complete.
echo Double-click Torchic.pyw to open the application.
echo.
pause
exit /b 0

:fail
echo.
echo Setup failed. Review the error above.
pause
exit /b 1
