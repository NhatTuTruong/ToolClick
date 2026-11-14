# Chạy nhanh (PowerShell). Sửa $Keywords bên dưới.
param(
    [string[]] $Keywords = @("hosting"),
    [switch] $Headed
)

Set-Location $PSScriptRoot
& .\.venv\Scripts\python main.py -k @Keywords @(
    if ($Headed) { "--headed" }
)
