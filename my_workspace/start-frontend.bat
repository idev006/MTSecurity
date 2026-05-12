@echo off
title MTSecurity — Frontend
cd /d "%~dp0frontend"

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install from https://nodejs.org
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo [INFO] Installing npm packages...
    npm install
)

echo [MTSecurity] Starting frontend on http://localhost:5173 ...
npm run dev
pause
