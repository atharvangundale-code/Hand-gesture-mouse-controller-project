@echo off
title AI Hand Gesture Mouse Activator
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
) else (
    set "PY_CMD=python"
)

start "" "%PY_CMD%" activator.py
