@echo off
title MTSecurity — Launcher
echo.
echo  ╔══════════════════════════════════════╗
echo  ║   MTSecurity v2 — Starting up...    ║
echo  ╚══════════════════════════════════════╝
echo.

set "ROOT=%~dp0"
set "VENV=D:\dev\MTSecurity\my_env"

:: Check virtualenv
if not exist "%VENV%\Scripts\python.exe" (
    echo [ERROR] Virtualenv not found at %VENV%
    echo         Run: python -m venv D:\dev\MTSecurity\my_env
    pause
    exit /b 1
)

if not exist "%ROOT%backend\.env" (
    echo [ERROR] backend\.env not found. Copy backend\.env.example and fill in secrets.
    pause
    exit /b 1
)

:: Check Node
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install from https://nodejs.org
    pause
    exit /b 1
)

:: Start backend in a new window
echo [1/2] Starting Backend   ^(http://localhost:8000^)
start "MTSecurity Backend" cmd /k "cd /d "%ROOT%backend" && "%VENV%\Scripts\python" main.py"

:: Brief pause so backend gets a head start
timeout /t 3 /nobreak >nul

:: Start frontend in a new window
echo [2/2] Starting Frontend  ^(http://localhost:5173^)
start "MTSecurity Frontend" cmd /k "cd /d "%ROOT%frontend" && npm run dev"

echo.
echo  Both services are starting in separate windows.
echo.
echo  Frontend : http://localhost:5173
echo  Backend  : http://localhost:8000
echo  API Docs : http://localhost:8000/docs
echo.
echo  Close the service windows to stop.
echo.
pause
