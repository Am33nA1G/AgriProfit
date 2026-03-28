# Start Backend Server Script
# This script ensures the backend starts from the correct directory

Set-Location -Path $PSScriptRoot
Write-Host "Starting backend server from: $PSScriptRoot" -ForegroundColor Green
Write-Host "Backend will be available at: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
