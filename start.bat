@echo off
echo ========================================
echo Starting StrategAI System
echo ========================================
echo.

echo [1/2] Using RunPod Ollama endpoint...
echo       https://q7fn9rrgympjqn-11434.proxy.runpod.net

timeout /t 2 /nobreak >nul

echo [2/2] Starting Frontend Dashboard...
start "StrategAI Dashboard" cmd /k "cd /d %~dp0frontend\salik-frontend && npm run dev"

timeout /t 2 /nobreak >nul

echo [3/3] Starting Backend...
start "StrategAI Backend" cmd /k "cd /d %~dp0backend && .\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"

echo.
echo ========================================
echo System Started!
echo ========================================
echo.
echo Ollama:       https://q7fn9rrgympjqn-11434.proxy.runpod.net  (model: llama3.1:8b)
echo Dashboard:    http://localhost:5173
echo Backend:      http://localhost:8001
echo API Docs:     http://localhost:8001/docs
echo.
echo NOTE: Ollama is hosted remotely on RunPod for this setup.
echo.
echo Press any key to open Dashboard...
pause >nul

start http://localhost:5173

echo.
echo To stop: Close the terminal windows
echo.
