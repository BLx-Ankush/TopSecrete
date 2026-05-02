@echo off
:: Alice Security Launcher - Windows Batch Version
:: Quick launcher for Alice with 4-digit code protection

title Alice Security Launcher

:: Navigate to Alice directory
cd /d "%~dp0"

:: Start the Python trigger script
python alice_trigger.py

:: Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Press any key to exit...
    pause >nul
)