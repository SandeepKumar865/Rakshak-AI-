@echo off
title Rakshak AI - Mentor Demo Console
cd /d "%~dp0"
echo ========================================================
echo Starting Rakshak AI One-Click Demo Console...
echo ========================================================
py launch_demo.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Launch failed. Trying with python...
    python launch_demo.py
)
pause
