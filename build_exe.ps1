# Build ToolClick.exe (PyInstaller, thu muc dist\ToolClick\)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Chua co .venv - chay setup.ps1 truoc." -ForegroundColor Red
    exit 1
}

$py = ".\.venv\Scripts\python.exe"
& $py -m pip install -q -r requirements.txt "pyinstaller>=6.0"

Write-Host "Dang build (co the vai phut)..." -ForegroundColor Cyan
& $py -m PyInstaller --noconfirm --clean ToolClick.spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$out = Join-Path $PSScriptRoot "dist\ToolClick"
Copy-Item -Force "config.example.env" (Join-Path $out "config.example.env")

$readme = @"
ToolClick - Windows (cua so ung dung)

1. Can Google Chrome (BROWSER_CHANNEL=chrome).
2. Chay ToolClick.exe — mo cua so app, khong can trinh duyet / port 8501.
3. .env, output\, browser-profile\ nam canh file exe.
4. CLI: ToolClick.exe --toolclick-main -k "tu khoa" --headed
"@
Set-Content -Path (Join-Path $out "HUONG-DAN.txt") -Value $readme -Encoding UTF8

Write-Host ""
Write-Host "Xong: $out\ToolClick.exe" -ForegroundColor Green
Write-Host "Zip ca thu muc dist\ToolClick de phan phoi." -ForegroundColor Yellow
