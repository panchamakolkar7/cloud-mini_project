# QuotaCloud PowerShell Launcher
Set-Location -Path $PSScriptRoot

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "          QuotaCloud - Multi-User Cloud Storage SaaS            " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$python = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

Write-Host "Starting Flask server on http://127.0.0.1:5000/ ..." -ForegroundColor Green
Write-Host "Admin Login:  admin / Admin@123" -ForegroundColor Yellow
Write-Host "User Login:   user1 / User@123" -ForegroundColor Yellow
Write-Host ""

Start-Process "http://127.0.0.1:5000/"
& $python run.py
