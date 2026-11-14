# Xóa profile lỗi (Chrome crash / TargetClosed). Đóng Chrome trước khi chạy.
Set-Location $PSScriptRoot
if (Test-Path "browser-profile") {
    Remove-Item -Recurse -Force "browser-profile"
    Write-Host "Da xoa browser-profile/" -ForegroundColor Green
} else {
    Write-Host "Khong co browser-profile/" -ForegroundColor Yellow
}
