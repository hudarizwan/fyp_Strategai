# StrategAI Frontend Setup Script
# This script helps you set up the development environment

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "StrategAI Frontend Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Node.js is installed
Write-Host "Checking for Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    $npmVersion = npm --version 2>&1
    Write-Host "✓ Node.js found: $nodeVersion" -ForegroundColor Green
    Write-Host "✓ npm found: $npmVersion" -ForegroundColor Green
    Write-Host ""
    
    # Install dependencies
    Write-Host "Installing project dependencies..." -ForegroundColor Yellow
    npm install
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ Dependencies installed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "Setup Complete!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "To start the development server, run:" -ForegroundColor Yellow
        Write-Host "  npm run dev" -ForegroundColor White
        Write-Host ""
        Write-Host "The app will be available at: http://localhost:5173" -ForegroundColor Cyan
    } else {
        Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "✗ Node.js is not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Node.js first:" -ForegroundColor Yellow
    Write-Host "  1. Visit: https://nodejs.org/" -ForegroundColor White
    Write-Host "  2. Download the LTS version" -ForegroundColor White
    Write-Host "  3. Run the installer" -ForegroundColor White
    Write-Host "  4. Restart your terminal" -ForegroundColor White
    Write-Host "  5. Run this script again" -ForegroundColor White
    Write-Host ""
    Write-Host "Or use winget (as Administrator):" -ForegroundColor Yellow
    Write-Host "  winget install OpenJS.NodeJS.LTS" -ForegroundColor White
    exit 1
}

