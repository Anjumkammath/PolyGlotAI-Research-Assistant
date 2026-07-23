$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

$LogDir = Join-Path $ProjectRoot "logs"
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$OutLog = Join-Path $LogDir "streamlit.out.log"
$ErrLog = Join-Path $LogDir "streamlit.err.log"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$App = Join-Path $ProjectRoot "frontend\streamlit_app.py"

while ($true) {
    Add-Content -Path $OutLog -Value "[$(Get-Date -Format o)] Starting Streamlit on http://127.0.0.1:8501"
    $Command = "`"$Python`" -m streamlit run `"$App`" --server.address 127.0.0.1 --server.port 8501 --server.headless true --server.fileWatcherType none >> `"$OutLog`" 2>> `"$ErrLog`""
    & $env:ComSpec /d /c $Command
    Add-Content -Path $ErrLog -Value "[$(Get-Date -Format o)] Streamlit exited with code $LASTEXITCODE. Restarting in 2 seconds."
    Start-Sleep -Seconds 2
}
