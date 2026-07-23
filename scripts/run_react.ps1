$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ReactRoot = Join-Path $ProjectRoot "frontend-react"
Set-Location -LiteralPath $ReactRoot

$LogDir = Join-Path $ProjectRoot "logs"
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$OutLog = Join-Path $LogDir "react.out.log"
$ErrLog = Join-Path $LogDir "react.err.log"

while ($true) {
    Add-Content -Path $OutLog -Value "[$(Get-Date -Format o)] Starting React frontend on http://127.0.0.1:5173"
    $Command = "npm.cmd run dev >> `"$OutLog`" 2>> `"$ErrLog`""
    & $env:ComSpec /d /c $Command
    Add-Content -Path $ErrLog -Value "[$(Get-Date -Format o)] React frontend exited with code $LASTEXITCODE. Restarting in 2 seconds."
    Start-Sleep -Seconds 2
}
