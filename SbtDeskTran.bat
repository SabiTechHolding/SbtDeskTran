@echo off
cd /d "%~dp0"
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Python not found. Download from https://www.python.org/downloads/
    pause
)
