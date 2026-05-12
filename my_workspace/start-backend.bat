@echo off
title MTSecurity — Backend
cd /d "%~dp0backend"

set "VENV=D:\dev\MTSecurity\my_env"

if not exist "%VENV%\Scripts\python.exe" (
    echo [ERROR] Virtualenv not found at %VENV%
    echo Run: python -m venv D:\dev\MTSecurity\my_env
    pause
    exit /b 1
)

if not exist ".env" (
    echo [WARN] .env not found — copy .env.example and fill in secrets first.
    pause
    exit /b 1
)

echo [MTSecurity] Starting backend on http://localhost:8000 ...
echo.
echo   Default login: admin / Admin1234
echo   Change password: python scripts\create_admin.py
echo.
"%VENV%\Scripts\python" main.py
pause
