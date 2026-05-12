# MTSecurity v2 — Pre-flight startup check
# Run before starting services to verify the environment is ready.
# Usage:  .\scripts\check-startup.ps1
#         .\scripts\check-startup.ps1 -BackendDir "D:\MyApp\backend"

param(
    [string]$BackendDir = (Join-Path (Split-Path -Parent $PSScriptRoot) "backend"),
    [string]$VenvDir    = "D:\dev\MTSecurity\my_env"
)

$ok    = $true
$warns = 0

function Pass([string]$msg)  { Write-Host "  [OK]   $msg" -ForegroundColor Green }
function Fail([string]$msg)  { Write-Host "  [FAIL] $msg" -ForegroundColor Red;    $script:ok = $false }
function Warn([string]$msg)  { Write-Host "  [WARN] $msg" -ForegroundColor Yellow; $script:warns++ }
function Section([string]$t) { Write-Host "`n── $t " -ForegroundColor Cyan }

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   MTSecurity v2 — Pre-flight Check       ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan

# ── 1. Python venv ────────────────────────────────────────────────────────────
Section "Python Environment"
$pythonExe = Join-Path $VenvDir "Scripts\python.exe"
if (Test-Path $pythonExe) {
    $ver = & $pythonExe --version 2>&1
    Pass "virtualenv found — $ver ($VenvDir)"
} else {
    Fail "virtualenv not found at $VenvDir"
    Write-Host "       Fix: python -m venv D:\dev\MTSecurity\my_env"
    Write-Host "            my_env\Scripts\pip install -r my_workspace\backend\requirements.txt"
}

# ── 2. .env file ──────────────────────────────────────────────────────────────
Section "Environment Configuration"
$envFile = Join-Path $BackendDir ".env"
if (-not (Test-Path $envFile)) {
    Fail ".env not found at $envFile"
    Write-Host "       Fix: copy backend\.env.example backend\.env and fill in required values"
} else {
    Pass ".env file present"

    $envContent = Get-Content $envFile -Raw

    # Required keys
    $required = @(
        "JWT_SECRET_KEY",
        "ENCRYPTION_KEY",
        "BASE_URL"
    )
    foreach ($key in $required) {
        if ($envContent -match "(?m)^$key\s*=\s*(.+)$") {
            $val = $Matches[1].Trim()
            if ($val -like "CHANGE_ME*" -or $val -eq "") {
                Fail "$key is not configured (still placeholder)"
            } elseif ($key -eq "JWT_SECRET_KEY" -and $val.Length -lt 32) {
                Fail "JWT_SECRET_KEY must be at least 32 characters (current: $($val.Length))"
            } else {
                Pass "$key is set"
            }
        } else {
            Fail "$key missing from .env"
        }
    }

    # Optional but warn if missing
    $optional = @("LINE_CHANNEL_ACCESS_TOKEN", "DISCORD_WEBHOOK_URL", "SLACK_WEBHOOK_URL", "SMTP_HOST")
    $anyNotif = $false
    foreach ($key in $optional) {
        if ($envContent -match "(?m)^$key\s*=\s*(.+)$") {
            $anyNotif = $true
        }
    }
    if (-not $anyNotif) {
        Warn "No notification channel configured (LINE / Discord / Slack / SMTP). Alerts will be logged only."
    }
}

# ── 3. AI Model ───────────────────────────────────────────────────────────────
Section "AI Model"
# Read MODEL_PATH from .env, fall back to default
$modelPath = $null
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match "(?m)^MODEL_PATH\s*=\s*(.+)$") {
        $modelPath = $Matches[1].Trim()
    }
}
if (-not $modelPath) {
    $modelPath = Join-Path $BackendDir "data\models\yolov11n.xml"
} elseif (-not [System.IO.Path]::IsPathRooted($modelPath)) {
    $modelPath = Join-Path $BackendDir $modelPath
}

if (Test-Path $modelPath) {
    $size = (Get-Item $modelPath).Length / 1MB
    Pass "Model found: $modelPath ($([math]::Round($size,1)) MB)"
} else {
    Warn "Model file not found: $modelPath"
    Write-Host "       AI inference will be disabled until model is placed at this path."
}

# ── 4. Data directories ───────────────────────────────────────────────────────
Section "Data Directories"
$dirs = @(
    (Join-Path $BackendDir "data"),
    (Join-Path $BackendDir "data\snapshots"),
    (Join-Path $BackendDir "data\clips"),
    (Join-Path $BackendDir "data\models")
)
foreach ($d in $dirs) {
    if (Test-Path $d) {
        Pass "Directory exists: $d"
    } else {
        try {
            New-Item -ItemType Directory -Path $d -Force | Out-Null
            Pass "Created directory: $d"
        } catch {
            Fail "Cannot create directory: $d — $_"
        }
    }
}

# ── 5. Disk space ─────────────────────────────────────────────────────────────
Section "Disk Space"
$drive = Split-Path -Qualifier $BackendDir
$disk  = Get-PSDrive -Name ($drive.TrimEnd(':')) -ErrorAction SilentlyContinue
if ($disk) {
    $freeGB = [math]::Round($disk.Free / 1GB, 1)
    if ($freeGB -lt 5) {
        Fail "Low disk space: ${freeGB} GB free on $drive (minimum 5 GB recommended)"
    } elseif ($freeGB -lt 20) {
        Warn "Disk space: ${freeGB} GB free on $drive (20 GB recommended for recordings)"
    } else {
        Pass "Disk space: ${freeGB} GB free on $drive"
    }
}

# ── 6. Port availability ──────────────────────────────────────────────────────
Section "Port Availability"
$ports = @(8000)
foreach ($port in $ports) {
    $listener = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties()
    $active   = $listener.GetActiveTcpListeners() | Where-Object { $_.Port -eq $port }
    if ($active) {
        Warn "Port $port is already in use — backend may fail to start"
    } else {
        Pass "Port $port is available"
    }
}

# ── 7. Dependencies ───────────────────────────────────────────────────────────
Section "Python Dependencies"
if (Test-Path $pythonExe) {
    $reqFile = Join-Path $BackendDir "requirements.txt"
    if (Test-Path $reqFile) {
        try {
            $check = & $pythonExe -m pip check 2>&1
            if ($LASTEXITCODE -eq 0) {
                Pass "All pip dependencies satisfied"
            } else {
                Warn "Dependency issue detected — run: my_env\Scripts\pip install -r my_workspace\backend\requirements.txt"
            }
        } catch {
            Warn "Could not run pip check: $_"
        }
    } else {
        Warn "requirements.txt not found at $reqFile"
    }
}

# ── 8. Frontend build ─────────────────────────────────────────────────────────
Section "Frontend"
$frontendDist = Join-Path (Split-Path -Parent $BackendDir) "frontend\dist"
if (Test-Path $frontendDist) {
    $indexHtml = Join-Path $frontendDist "index.html"
    if (Test-Path $indexHtml) {
        Pass "Frontend dist/ found with index.html"
    } else {
        Warn "Frontend dist/ exists but index.html missing — rebuild: cd frontend && npm run build"
    }
} else {
    Warn "Frontend not built. Run: cd frontend && npm run build"
    Write-Host "       (Not required if using a separate web server)"
}

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "══════════════════════════════════════════" -ForegroundColor Cyan
if ($ok -and $warns -eq 0) {
    Write-Host "  ALL CHECKS PASSED — ready to start    " -ForegroundColor Green
} elseif ($ok) {
    Write-Host "  PASSED with $warns warning(s)          " -ForegroundColor Yellow
    Write-Host "  Review warnings above before going live" -ForegroundColor Yellow
} else {
    Write-Host "  FAILED — fix errors before starting   " -ForegroundColor Red
}
Write-Host "══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if ($ok) {
    Write-Host "Start services:"
    Write-Host "  nssm start MTSecurityBackend"
    Write-Host "  nssm start MTSecurityFrontend"
    Write-Host ""
    Write-Host "Or run directly (dev):"
    Write-Host "  cd backend && ..\.venv\Scripts\python main.py"
    Write-Host "  cd frontend && npm run dev"
}
Write-Host ""

exit ([int](-not $ok))
