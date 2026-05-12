# MTSecurity v2 — Windows Service Installer (NSSM)
# Run as Administrator in PowerShell from the repo root:
#   .\scripts\install-services.ps1
#
# Prerequisites:
#   - NSSM (Non-Sucking Service Manager) installed and in PATH
#     Download: https://nssm.cc/download
#   - Python venv created:  python -m venv backend\.venv
#   - Dependencies installed: backend\.venv\Scripts\pip install -r backend\requirements.txt
#   - backend\.env configured (copy from backend\.env.example)
#   - Frontend built: cd frontend && npm run build
#   - Node.js / serve installed OR use nginx for frontend (recommended)

param(
    [string]$InstallDir  = "C:\MTSecurity",
    [string]$BackendPort = "8000",
    [string]$FrontendPort = "5000"
)

# ── Helpers ──────────────────────────────────────────────────────────────────

function Ensure-Admin {
    $current = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($current)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Error "This script must be run as Administrator."
        exit 1
    }
}

function Check-Nssm {
    if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
        Write-Error "NSSM not found in PATH. Download from https://nssm.cc/download and add to PATH."
        exit 1
    }
}

function Remove-ServiceIfExists([string]$name) {
    $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
    if ($svc) {
        Write-Host "Stopping and removing existing service: $name" -ForegroundColor Yellow
        nssm stop $name confirm 2>$null
        nssm remove $name confirm 2>$null
    }
}

# ── Main ─────────────────────────────────────────────────────────────────────

Ensure-Admin
Check-Nssm

$scriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot    = Split-Path -Parent $scriptDir
$backendDir  = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$logsDir     = Join-Path $InstallDir "logs"

# Create log directory
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MTSecurity v2 — Service Installer     " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Install dir : $InstallDir"
Write-Host "Repo root   : $repoRoot"
Write-Host "Backend dir : $backendDir"
Write-Host ""

# ── 1. Backend Service (FastAPI / uvicorn) ────────────────────────────────────

$backendSvc  = "MTSecurityBackend"
$pythonExe   = Join-Path $backendDir ".venv\Scripts\python.exe"
$backendArgs = "main.py"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python venv not found at $pythonExe`nRun:  python -m venv backend\.venv && backend\.venv\Scripts\pip install -r backend\requirements.txt"
    exit 1
}

if (-not (Test-Path (Join-Path $backendDir ".env"))) {
    Write-Warning "backend\.env not found — copy backend\.env.example and fill in secrets before starting the service."
}

Remove-ServiceIfExists $backendSvc

Write-Host "Installing backend service: $backendSvc" -ForegroundColor Green
nssm install $backendSvc $pythonExe $backendArgs
nssm set $backendSvc AppDirectory      $backendDir
nssm set $backendSvc DisplayName       "MTSecurity Backend (FastAPI)"
nssm set $backendSvc Description       "MTSecurity v2 AI-powered security platform — REST API and WebSocket hub"
nssm set $backendSvc Start             SERVICE_AUTO_START
nssm set $backendSvc AppStdout         (Join-Path $logsDir "backend_stdout.log")
nssm set $backendSvc AppStderr         (Join-Path $logsDir "backend_stderr.log")
nssm set $backendSvc AppRotateFiles    1
nssm set $backendSvc AppRotateBytes    10485760    # 10 MB
nssm set $backendSvc AppRotateOnline   1
nssm set $backendSvc AppRestartDelay   3000        # 3 s before restart on crash
nssm set $backendSvc AppThrottle       10000       # cap restart rate

Write-Host "  Backend service installed." -ForegroundColor Green

# ── 2. Frontend Service (static file server via 'serve') ─────────────────────
# Alternatively, use nginx — see nginx.conf in the repo root.

$frontendDist = Join-Path $frontendDir "dist"

if (-not (Test-Path $frontendDist)) {
    Write-Warning "Frontend dist/ not found at $frontendDist"
    Write-Warning "Build first:  cd frontend && npm run build"
    Write-Warning "Skipping frontend service installation."
} else {
    $serveExe = (Get-Command serve -ErrorAction SilentlyContinue)?.Source
    $npxExe   = (Get-Command npx  -ErrorAction SilentlyContinue)?.Source

    if (-not $serveExe -and -not $npxExe) {
        Write-Warning "'serve' and 'npx' not found — install Node.js or use nginx for the frontend."
        Write-Warning "Skipping frontend service installation."
    } else {
        $frontendSvc = "MTSecurityFrontend"
        Remove-ServiceIfExists $frontendSvc

        $serveCmd  = if ($serveExe) { $serveExe } else { $npxExe }
        $serveArgs = if ($serveExe) { "-s `"$frontendDist`" -l $FrontendPort" } `
                     else           { "serve -s `"$frontendDist`" -l $FrontendPort" }

        Write-Host "Installing frontend service: $frontendSvc" -ForegroundColor Green
        nssm install $frontendSvc $serveCmd $serveArgs
        nssm set $frontendSvc AppDirectory      $frontendDist
        nssm set $frontendSvc DisplayName       "MTSecurity Frontend (static)"
        nssm set $frontendSvc Description       "MTSecurity v2 — Vue SPA static file server"
        nssm set $frontendSvc Start             SERVICE_AUTO_START
        nssm set $frontendSvc AppStdout         (Join-Path $logsDir "frontend_stdout.log")
        nssm set $frontendSvc AppStderr         (Join-Path $logsDir "frontend_stderr.log")
        nssm set $frontendSvc AppRotateFiles    1
        nssm set $frontendSvc AppRotateBytes    5242880
        nssm set $frontendSvc AppRestartDelay   3000

        Write-Host "  Frontend service installed (port $FrontendPort)." -ForegroundColor Green
    }
}

# ── Done ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Installation complete!               " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Verify backend\.env is configured"
Write-Host "  2. Run startup check:  .\scripts\check-startup.ps1"
Write-Host "  3. Start services:"
Write-Host "       nssm start MTSecurityBackend"
Write-Host "       nssm start MTSecurityFrontend   (if installed)"
Write-Host "  4. View logs: $logsDir"
Write-Host ""
Write-Host "Service management commands:"
Write-Host "  nssm status  MTSecurityBackend"
Write-Host "  nssm restart MTSecurityBackend"
Write-Host "  nssm stop    MTSecurityBackend"
Write-Host "  nssm edit    MTSecurityBackend   (opens NSSM GUI)"
Write-Host ""
