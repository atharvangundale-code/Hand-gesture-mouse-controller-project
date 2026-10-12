@echo off
title AI Hand Gesture Mouse Controller
cd /d "%~dp0"

echo ======================================================================
echo   AI-Based Hand Gesture Mouse Controller (Version 1.0)
echo ======================================================================
echo   [INIT] Checking Python environment...

if exist ".venv\Scripts\python.exe" (
    echo   [ENV] Using local virtual environment (.venv)
    set "PY_CMD=.venv\Scripts\python.exe"
) else (
    echo   [ENV] Using system Python
    set "PY_CMD=python"
)

echo   [START] Launching controller...
echo.
"%PY_CMD%" main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application closed with an error code.
    pause
)
