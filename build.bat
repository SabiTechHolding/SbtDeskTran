@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================
echo   SbtDeskTran - Build Release EXE
echo ============================================
echo.

:: ── Check Python ─────────────────────────────
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Download from https://www.python.org/
    pause & exit /b 1
)

:: ── Install / upgrade PyInstaller ────────────
echo [1/4] Checking PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       Installing PyInstaller...
    python -m pip install pyinstaller --quiet
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install PyInstaller.
        pause & exit /b 1
    )
)
echo       OK

:: ── Generate icon if missing ─────────────────
echo [2/4] Checking icon...
if not exist "icon.ico" (
    echo       Generating icon.ico ...
    python create_icon.py
    if %ERRORLEVEL% NEQ 0 (
        echo [WARN]  Icon generation failed, building without icon.
        set ICON_ARG=
    ) else (
        set ICON_ARG=--icon=icon.ico
    )
) else (
    echo       icon.ico found.
    set ICON_ARG=--icon=icon.ico
)

:: ── Clean previous build ─────────────────────
echo [3/4] Cleaning previous build...
if exist "dist\SbtDeskTran" rmdir /s /q "dist\SbtDeskTran"
if exist "dist\SbtDeskTran.exe" del /q "dist\SbtDeskTran.exe"
if exist "build" rmdir /s /q "build"
if exist "SbtDeskTran.spec" del /q "SbtDeskTran.spec"
echo       Done.

:: ── Run PyInstaller ──────────────────────────
echo [4/4] Building EXE (this may take a minute)...
echo.

python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "SbtDeskTran" ^
    %ICON_ARG% ^
    --add-data "icon.ico;." ^
    --collect-all tkinter ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import json ^
    --hidden-import threading ^
    --hidden-import urllib.request ^
    --hidden-import urllib.parse ^
    --hidden-import urllib.error ^
    --noconfirm ^
    main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build failed. Check the output above for details.
    pause & exit /b 1
)

echo.
echo ============================================
echo   Build complete!
echo   Output: dist\SbtDeskTran.exe
echo ============================================
echo.

:: Open dist folder
if exist "dist\SbtDeskTran.exe" (
    explorer /select,"dist\SbtDeskTran.exe"
)

pause
endlocal
