# Kill any stray node/python processes that might be holding old ports
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq "" } | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "Starting backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000"

Start-Sleep -Seconds 3

Write-Host "Starting frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"

Write-Host "Both servers starting in new windows. Backend: http://localhost:8000 | Frontend: http://localhost:5173" -ForegroundColor Green