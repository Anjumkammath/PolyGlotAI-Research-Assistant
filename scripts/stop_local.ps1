$ErrorActionPreference = "Continue"

$Ports = @(8000, 8501, 5173)

foreach ($Port in $Ports) {
    $ProcessIds = netstat -ano |
        Select-String ":$Port\s+.*LISTENING" |
        ForEach-Object { ($_ -split "\s+")[-1] } |
        Select-Object -Unique

    foreach ($PortProcessId in $ProcessIds) {
        Stop-Process -Id ([int]$PortProcessId) -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Stopped local PolyGlotAI servers on ports 8000, 8501, and 5173."
