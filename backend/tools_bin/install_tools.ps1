# NightHawk AI - Windows Tool Installer Script
# Automatically downloads and sets up standalone binaries for Windows host execution

$ToolsBin = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "==> NightHawk AI Tool Setup (Windows)" -ForegroundColor Cyan

# 1. Download Nuclei if missing
$NucleiPath = Join-Path $ToolsBin "nuclei.exe"
if (-not (Test-Path $NucleiPath)) {
    Write-Host "[+] Downloading ProjectDiscovery Nuclei..." -ForegroundColor Yellow
    $ZipPath = Join-Path $ToolsBin "nuclei.zip"
    $Url = "https://github.com/projectdiscovery/nuclei/releases/download/v3.11.1/nuclei_3.11.1_windows_amd64.zip"
    Invoke-WebRequest -Uri $Url -OutFile $ZipPath
    Expand-Archive -Path $ZipPath -DestinationPath $ToolsBin -Force
    Remove-Item $ZipPath -Force
    Write-Host "[OK] Nuclei installed successfully." -ForegroundColor Green
} else {
    Write-Host "[OK] Nuclei already present." -ForegroundColor Green
}

# 2. Download OSV-Scanner if missing
$OsvPath = Join-Path $ToolsBin "osv-scanner.exe"
if (-not (Test-Path $OsvPath)) {
    Write-Host "[+] Downloading Google OSV-Scanner..." -ForegroundColor Yellow
    $Url = "https://github.com/google/osv-scanner/releases/download/v2.6.0/osv-scanner_windows_amd64.exe"
    Invoke-WebRequest -Uri $Url -OutFile $OsvPath
    Write-Host "[OK] OSV-Scanner installed successfully." -ForegroundColor Green
} else {
    Write-Host "[OK] OSV-Scanner already present." -ForegroundColor Green
}

Write-Host "All NightHawk security tools configured!" -ForegroundColor Green
