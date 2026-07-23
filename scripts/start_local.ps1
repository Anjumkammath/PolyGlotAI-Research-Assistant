$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendScript = Join-Path $ProjectRoot "scripts\run_backend.ps1"
$StreamlitScript = Join-Path $ProjectRoot "scripts\run_streamlit.ps1"
$ReactScript = Join-Path $ProjectRoot "scripts\run_react.ps1"
$ReactNodeModules = Join-Path $ProjectRoot "frontend-react\node_modules"

if (!(Test-Path (Join-Path $ProjectRoot ".venv\Scripts\python.exe"))) {
    Write-Host "Virtual environment not found. Create it first with: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

& $env:ComSpec /d /c start "PolyGlotAI Backend" /min powershell.exe -NoExit -NoProfile -ExecutionPolicy Bypass -File "`"$BackendScript`""
& $env:ComSpec /d /c start "PolyGlotAI Streamlit" /min powershell.exe -NoExit -NoProfile -ExecutionPolicy Bypass -File "`"$StreamlitScript`""

if (Test-Path $ReactNodeModules) {
    & $env:ComSpec /d /c start "PolyGlotAI React" /min powershell.exe -NoExit -NoProfile -ExecutionPolicy Bypass -File "`"$ReactScript`""
} else {
    Write-Host "React dependencies not found. Run this once: cd frontend-react; npm.cmd install" -ForegroundColor Yellow
}

Write-Host "PolyGlotAI local servers are starting..." -ForegroundColor Green
Write-Host "Backend:   http://127.0.0.1:8000"
Write-Host "Streamlit: http://127.0.0.1:8501"
if (Test-Path $ReactNodeModules) {
    Write-Host "React:     http://127.0.0.1:5173"
}
Write-Host "Keep the minimized PowerShell windows open while using the app."
