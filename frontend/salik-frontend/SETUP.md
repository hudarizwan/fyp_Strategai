# StrategAI Frontend - Setup Guide

## Step 1: Install Node.js

You need to install Node.js (which includes npm) first. Choose one of the following methods:

### Option A: Direct Download (Recommended)
1. Visit: https://nodejs.org/
2. Download the **LTS (Long Term Support)** version
3. Run the installer (.msi file)
4. Follow the installation wizard (accept defaults)
5. **Restart your terminal/PowerShell** after installation

### Option B: Using winget (Windows Package Manager)
Open PowerShell as Administrator and run:
```powershell
winget install OpenJS.NodeJS.LTS
```

### Option C: Using Chocolatey
If you have Chocolatey installed:
```powershell
choco install nodejs-lts
```

## Step 2: Verify Installation

After installing Node.js, open a new terminal and verify:
```bash
node --version
npm --version
```

You should see version numbers (e.g., v20.x.x and 10.x.x)

## Step 3: Install Project Dependencies

Navigate to the project directory and run:
```bash
npm install
```

This will install all required packages listed in `package.json`.

## Step 4: Start Development Server

```bash
npm run dev
```

The application will start at: **http://localhost:5173**

## Troubleshooting

### If npm/node commands are not recognized:
1. Close and reopen your terminal/PowerShell
2. Restart your computer if needed
3. Check that Node.js was added to PATH during installation

### If you get permission errors:
- Run PowerShell as Administrator
- Or use a different terminal (Git Bash, Command Prompt)

## Quick Start Script

After Node.js is installed, you can run:
```bash
npm install && npm run dev
```

This will install dependencies and start the server in one command.

