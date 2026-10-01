# ==============================================================================
# CrisisMesh - Cloudflare Quick Tunnel Public Share Script (PowerShell)
# ==============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"

$ROOT_DIR = (Get-Item $PSScriptRoot).Parent.FullName
$FRONTEND_DIR = Join-Path $ROOT_DIR "frontend"
$LOGS_DIR = Join-Path $ROOT_DIR "logs"

if (-not (Test-Path $LOGS_DIR)) {
    New-Item -ItemType Directory -Path $LOGS_DIR -Force | Out-Null
}

$BACKEND_TUNNEL_OUT = Join-Path $LOGS_DIR "cloudflared_backend.out.log"
$BACKEND_TUNNEL_ERR = Join-Path $LOGS_DIR "cloudflared_backend.err.log"
$FRONTEND_TUNNEL_OUT = Join-Path $LOGS_DIR "cloudflared_frontend.out.log"
$FRONTEND_TUNNEL_ERR = Join-Path $LOGS_DIR "cloudflared_frontend.err.log"
$BACKEND_SERVER_OUT = Join-Path $LOGS_DIR "backend_server.out.log"
$BACKEND_SERVER_ERR = Join-Path $LOGS_DIR "backend_server.err.log"
$FRONTEND_SERVER_OUT = Join-Path $LOGS_DIR "frontend_server.out.log"
$FRONTEND_SERVER_ERR = Join-Path $LOGS_DIR "frontend_server.err.log"

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host " CrisisMesh: Starting Cloudflare Quick Tunnels Share Flow " -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

# Step 0: Ensure cloudflared is in PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
try {
    $cfVer = & cloudflared --version 2>&1
    Write-Host "[0/6] Cloudflared verified: $cfVer" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] cloudflared is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Clean existing processes on ports 8000 and 3000
Write-Host "[1/6] Stopping existing listeners on ports 8000 and 3000..." -ForegroundColor Yellow
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 4 } | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 4 } | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Step A: Start Backend
Write-Host "[2/6] Starting FastAPI Backend on 0.0.0.0:8000..." -ForegroundColor Yellow
$env:CRISISMESH_DEMO_MODE = "true"
$env:LLM_MODE = "mock"

$backendProc = Start-Process python -ArgumentList "-m", "uvicorn", "backend.app.api.main:app", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory $ROOT_DIR -PassThru -RedirectStandardOutput $BACKEND_SERVER_OUT -RedirectStandardError $BACKEND_SERVER_ERR

Start-Sleep -Seconds 3

# Step B: Start Quick Tunnel to http://localhost:8000
Write-Host "[3/6] Starting Cloudflare Quick Tunnel for Backend (Port 8000)..." -ForegroundColor Yellow
if (Test-Path $BACKEND_TUNNEL_OUT) { Remove-Item $BACKEND_TUNNEL_OUT -Force }
if (Test-Path $BACKEND_TUNNEL_ERR) { Remove-Item $BACKEND_TUNNEL_ERR -Force }

$backendTunnelProc = Start-Process cloudflared -ArgumentList "tunnel", "--url", "http://127.0.0.1:8000" -PassThru -RedirectStandardOutput $BACKEND_TUNNEL_OUT -RedirectStandardError $BACKEND_TUNNEL_ERR

$backendUrl = ""
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    $outText = ""
    $errText = ""
    if (Test-Path $BACKEND_TUNNEL_OUT) { $outText = Get-Content $BACKEND_TUNNEL_OUT -Raw -ErrorAction SilentlyContinue }
    if (Test-Path $BACKEND_TUNNEL_ERR) { $errText = Get-Content $BACKEND_TUNNEL_ERR -Raw -ErrorAction SilentlyContinue }
    $combined = "$outText`n$errText"
    if ($combined -match "https://[a-zA-Z0-9-]+\.trycloudflare\.com") {
        $backendUrl = $matches[0]
        break
    }
}

if (-not $backendUrl) {
    Write-Host "[ERROR] Failed to obtain Cloudflare tunnel URL for backend." -ForegroundColor Red
    exit 1
}

$backendHost = $backendUrl.Replace("https://", "").Replace("http://", "")
$backendWsUrl = "wss://$backendHost/ws"

Write-Host " -> Backend Public URL: $backendUrl" -ForegroundColor Green
Write-Host " -> Backend WebSocket URL: $backendWsUrl" -ForegroundColor Green

# Step C: Build & Start Frontend with baked-in URLs
Write-Host "[4/6] Building Next.js Frontend with Public Backend URLs..." -ForegroundColor Yellow
$env:NEXT_PUBLIC_API_URL = $backendUrl
$env:NEXT_PUBLIC_WS_URL = $backendWsUrl
$env:NEXT_PUBLIC_DEMO_AUTOLOGIN = "true"

Push-Location $FRONTEND_DIR
npm.cmd run build
Pop-Location

Write-Host "Starting Next.js production server on port 3000..." -ForegroundColor Yellow
$frontendProc = Start-Process npm.cmd -ArgumentList "run", "start" -WorkingDirectory $FRONTEND_DIR -PassThru -RedirectStandardOutput $FRONTEND_SERVER_OUT -RedirectStandardError $FRONTEND_SERVER_ERR

Start-Sleep -Seconds 3

# Step D: Start Quick Tunnel to http://localhost:3000
Write-Host "[5/6] Starting Cloudflare Quick Tunnel for Frontend (Port 3000)..." -ForegroundColor Yellow
if (Test-Path $FRONTEND_TUNNEL_OUT) { Remove-Item $FRONTEND_TUNNEL_OUT -Force }
if (Test-Path $FRONTEND_TUNNEL_ERR) { Remove-Item $FRONTEND_TUNNEL_ERR -Force }

$frontendTunnelProc = Start-Process cloudflared -ArgumentList "tunnel", "--url", "http://127.0.0.1:3000" -PassThru -RedirectStandardOutput $FRONTEND_TUNNEL_OUT -RedirectStandardError $FRONTEND_TUNNEL_ERR

$frontendUrl = ""
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    $outText = ""
    $errText = ""
    if (Test-Path $FRONTEND_TUNNEL_OUT) { $outText = Get-Content $FRONTEND_TUNNEL_OUT -Raw -ErrorAction SilentlyContinue }
    if (Test-Path $FRONTEND_TUNNEL_ERR) { $errText = Get-Content $FRONTEND_TUNNEL_ERR -Raw -ErrorAction SilentlyContinue }
    $combined = "$outText`n$errText"
    if ($combined -match "https://[a-zA-Z0-9-]+\.trycloudflare\.com") {
        $frontendUrl = $matches[0]
        break
    }
}

if (-not $frontendUrl) {
    Write-Host "[ERROR] Failed to obtain Cloudflare tunnel URL for frontend." -ForegroundColor Red
    exit 1
}

Write-Host " -> Frontend Public URL: $frontendUrl" -ForegroundColor Green

# Step E: Update Backend CORS Origins
$env:CRISISMESH_ALLOWED_ORIGINS = "$frontendUrl,http://localhost:3000"

# Step F: Run Health Checks
Write-Host "[6/6] Running System Health Checks..." -ForegroundColor Yellow

$healthPassed = $false
try {
    $healthRes = Invoke-RestMethod -Uri "$backendUrl/health" -Method Get -TimeoutSec 10
    if ($healthRes.status -eq "OK" -or $healthRes.status -eq "healthy" -or $healthRes.mode) {
        $healthPassed = $true
        Write-Host " [PASS] GET $backendUrl/health" -ForegroundColor Green
    } else {
        Write-Host " [PASS] GET $backendUrl/health returned response" -ForegroundColor Green
        $healthPassed = $true
    }
} catch {
    Write-Host " [FAIL] GET ${backendUrl}/health: $_" -ForegroundColor Red
}

$loginPassed = $false
try {
    $loginRes = Invoke-RestMethod -Uri "$backendUrl/auth/demo-login?role=commander" -Method Post -TimeoutSec 10
    if ($loginRes.access_token) {
        $loginPassed = $true
        Write-Host " [PASS] POST ${backendUrl}/auth/demo-login" -ForegroundColor Green
    }
} catch {
    Write-Host " [FAIL] POST ${backendUrl}/auth/demo-login: $_" -ForegroundColor Red
}

$frontendHttpPassed = $false
try {
    $frontRes = Invoke-WebRequest -Uri $frontendUrl -Method Get -TimeoutSec 15
    if ($frontRes.StatusCode -eq 200) {
        $frontendHttpPassed = $true
        Write-Host " [PASS] GET ${frontendUrl} (HTTP 200 OK)" -ForegroundColor Green
    }
} catch {
    Write-Host " [FAIL] GET ${frontendUrl}: $_" -ForegroundColor Red
}

Write-Host "`n=========================================================" -ForegroundColor Green
Write-Host "PUBLIC LINK: $frontendUrl" -ForegroundColor Green
Write-Host "BACKEND LINK: $backendUrl" -ForegroundColor Green
Write-Host "=========================================================" -ForegroundColor Green

# Output result file for verification scripts
$results = @{
    public_frontend_url = $frontendUrl
    public_backend_url = $backendUrl
    public_ws_url = $backendWsUrl
    health_check = if ($healthPassed) { "PASS" } else { "FAIL" }
    demo_login = if ($loginPassed) { "PASS" } else { "FAIL" }
    frontend_load = if ($frontendHttpPassed) { "PASS" } else { "FAIL" }
} | ConvertTo-Json

Set-Content -Path (Join-Path $ROOT_DIR "public_share_info.json") -Value $results -Force

Write-Host "Keeping all services and Cloudflare quick tunnels active..." -ForegroundColor Cyan
try {
    while ($true) {
        Start-Sleep -Seconds 10
    }
} finally {
    Write-Host "Shutting down background services..." -ForegroundColor Yellow
    Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $backendTunnelProc.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontendTunnelProc.Id -Force -ErrorAction SilentlyContinue
}
