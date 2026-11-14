# Cài đặt một lần — chạy trong PowerShell:
#   Set-ExecutionPolicy -Scope Process Bypass; .\setup.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\python -m pip install -U pip
& .\.venv\Scripts\pip install -r requirements.txt
& .\.venv\Scripts\python -m playwright install chromium

if (-not (Test-Path ".env")) {
    Copy-Item "config.example.env" ".env"
}

Write-Host ""
Write-Host "Xong. Kich hoat venv:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Chay tool:" -ForegroundColor Green
Write-Host '  python main.py -k "tu khoa" --headed'
