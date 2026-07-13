# StrategAI Startup Script (PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting StrategAI System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Frontend Dashboard
Write-Host "[1/2] Starting Frontend Dashboard..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend\salik-frontend'; Write-Host 'Dashboard Running on http://localhost:5173' -ForegroundColor Green; npm run dev"

Start-Sleep -Seconds 2

# 2. Backend
Write-Host "[2/2] Starting Backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; Write-Host 'Backend Running on http://localhost:8001' -ForegroundColor Green; .\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "System Started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Dashboard:    http://localhost:5173" -ForegroundColor Cyan
Write-Host "Backend:      http://localhost:8001" -ForegroundColor Cyan
Write-Host "API Docs:     http://localhost:8001/docs" -ForegroundColor Cyan
Write-Host "Ollama:       https://q7fn9rrgympjqn-11434.proxy.runpod.net" -ForegroundColor Cyan
Write-Host ""
Write-Host "Opening Dashboard in 3 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "To stop: Close the PowerShell windows" -ForegroundColor Red
Write-Host ""
