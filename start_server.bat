@echo off
title QuotaCloud Server
cd /d "%~dp0"

echo ================================================================
echo           QuotaCloud - Multi-User Cloud Storage SaaS
echo ================================================================
echo.

set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

if exist "%PYTHON_EXE%" (
    set "PY_CMD=%PYTHON_EXE%"
) else (
    set "PY_CMD=python"
)

echo Starting Flask server...
echo Access at: http://127.0.0.1:5000/
echo Admin Login:  username: admin  ^| password: Admin@123
echo User Login:   username: user1  ^| password: User@123
echo.

ping 127.0.0.1 -n 2 >nul
start "" "http://127.0.0.1:5000/"

"%PY_CMD%" run.py

pause
