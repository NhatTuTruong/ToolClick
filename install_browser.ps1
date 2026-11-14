# Tải Chromium cho đúng bản Playwright trong .venv
Set-Location $PSScriptRoot
& .\.venv\Scripts\python -m playwright install chromium
Write-Host "Xong. Thu lai: python main.py -k `"hosting`" --headed" -ForegroundColor Green
