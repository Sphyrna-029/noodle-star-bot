@echo off
cd /d "%~dp0"
python console_test.py
if errorlevel 1 (
    echo.
    echo An error occurred. See above for details.
    pause
)
