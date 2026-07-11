# StrategAI Startup Script (PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting StrategAI System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Landing Page
Write-Host "[1/3] Starting Landing Page..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend\landing-page'; Write-Host 'Landing Page Running on http://localhost:5175' -ForegroundColor Green; npm run dev -- --port 5175"

Start-Sleep -Seconds 2

# 2. Frontend Dashboard
Write-Host "[2/3] Starting Frontend Dashboard..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend\salik-frontend'; Write-Host 'Dashboard Running on http://localhost:5173' -ForegroundColor Green; npm run dev"

Start-Sleep -Seconds 2

# 3. Backend
Write-Host "[3/3] Starting Backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; Write-Host 'Backend Running on http://localhost:8001' -ForegroundColor Green; .\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "System Started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Landing Page: http://localhost:5175" -ForegroundColor Cyan
Write-Host "Dashboard:    http://localhost:5173" -ForegroundColor Cyan
Write-Host "Backend:      http://localhost:8001" -ForegroundColor Cyan
Write-Host "API Docs:     http://localhost:8001/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Opening Landing Page in 3 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Start-Process "http://localhost:5175"

Write-Host ""
Write-Host "To stop: Close the PowerShell windows" -ForegroundColor Red
Write-Host ""
