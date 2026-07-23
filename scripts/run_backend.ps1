$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

$LogDir = Join-Path $ProjectRoot "logs"
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$OutLog = Join-Path $LogDir "backend.out.log"
$ErrLog = Join-Path $LogDir "backend.err.log"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

while ($true) {
    Add-Content -Path $OutLog -Value "[$(Get-Date -Format o)] Starting backend on http://127.0.0.1:8000"
    $Command = "`"$Python`" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 >> `"$OutLog`" 2>> `"$ErrLog`""
    & $env:ComSpec /d /c $Command
    Add-Content -Path $ErrLog -Value "[$(Get-Date -Format o)] Backend exited with code $LASTEXITCODE. Restarting in 2 seconds."
    Start-Sleep -Seconds 2
}
