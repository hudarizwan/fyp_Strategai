@echo off
echo ========================================
echo Starting StrategAI System
echo ========================================
echo.

echo [1/4] Starting Ollama server (llama3.1:8b)...
echo       (If first run, model will auto-load on first request)
start "StrategAI Ollama" cmd /k "ollama serve"

timeout /t 3 /nobreak >nul

echo [2/4] Starting Landing Page...
start "StrategAI Landing Page" cmd /k "cd /d %~dp0frontend\landing-page && npm run dev -- --port 5175"

timeout /t 2 /nobreak >nul

echo [3/4] Starting Frontend Dashboard...
start "StrategAI Dashboard" cmd /k "cd /d %~dp0frontend\salik-frontend && npm run dev"

timeout /t 2 /nobreak >nul

echo [4/4] Starting Backend...
start "StrategAI Backend" cmd /k "cd /d %~dp0backend && .\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"

echo.
echo ========================================
echo System Started!
echo ========================================
echo.
echo Ollama:       http://localhost:11434  (model: llama3.1:8b)
echo Landing Page: http://localhost:5175
echo Dashboard:    http://localhost:5173
echo Backend:      http://localhost:8001
echo API Docs:     http://localhost:8001/docs
echo.
echo NOTE: First-time setup? Run this once in a terminal:
echo       ollama pull llama3.1:8b
echo.
echo Press any key to open Landing Page...
pause >nul

start http://localhost:5175

echo.
echo To stop: Close the terminal windows
echo.
