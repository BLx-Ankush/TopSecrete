# ALICE Project Submission Package Creator
# Creates a clean zip file for submission (under 35 MB)

$projectRoot = "d:\ALICE(NEW)\Alice-main07"
$outputZip = "d:\ALICE(NEW)\ALICE_Project_Submission.zip"
$tempFolder = "d:\ALICE(NEW)\ALICE_Temp_Package"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ALICE Project Submission Package Creator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Remove existing temp folder and zip if they exist
if (Test-Path $tempFolder) {
    Write-Host "Cleaning up old temp folder..." -ForegroundColor Yellow
    Remove-Item $tempFolder -Recurse -Force
}
if (Test-Path $outputZip) {
    Write-Host "Removing old submission zip..." -ForegroundColor Yellow
    Remove-Item $outputZip -Force
}

# Create temp folder
Write-Host "Creating temporary package folder..." -ForegroundColor Green
New-Item -ItemType Directory -Path $tempFolder | Out-Null

# Create project structure
$aliceCodeDest = Join-Path $tempFolder "Alice_code"
$reactDest = Join-Path $tempFolder "agent-starter-react"
$docsDest = Join-Path $tempFolder "docs"

New-Item -ItemType Directory -Path $aliceCodeDest | Out-Null
New-Item -ItemType Directory -Path $reactDest | Out-Null
New-Item -ItemType Directory -Path $docsDest | Out-Null

Write-Host "Copying Python source files..." -ForegroundColor Green

# Copy Alice_code files (excluding venv, pycache, test files, logs)
$aliceFiles = Get-ChildItem "$projectRoot\Alice_code" -File | Where-Object {
    $_.Extension -in @('.py', '.txt', '.json', '.md', '.ini') -and
    $_.Name -notmatch '^test_' -and
    $_.Name -ne 'debug.log' -and
    $_.Name -ne 'control_log.txt' -and
    $_.Name -ne 'alice_automation_test.txt' -and
    $_.Name -notmatch 'Solar_System|India_AI|black_holes'
}

foreach ($file in $aliceFiles) {
    Copy-Item $file.FullName -Destination $aliceCodeDest
}

Write-Host "  Copied $($aliceFiles.Count) Python/config files" -ForegroundColor Gray

# Copy specific folders from Alice_code
Write-Host "Copying mcp_client, KMS folders..." -ForegroundColor Green
if (Test-Path "$projectRoot\Alice_code\mcp_client") {
    Copy-Item "$projectRoot\Alice_code\mcp_client" -Destination $aliceCodeDest -Recurse -Exclude '__pycache__'
}
if (Test-Path "$projectRoot\Alice_code\KMS") {
    Copy-Item "$projectRoot\Alice_code\KMS" -Destination $aliceCodeDest -Recurse -Exclude '__pycache__'
}

# Copy tests folder structure (without __pycache__)
if (Test-Path "$projectRoot\Alice_code\tests") {
    Write-Host "Copying tests folder..." -ForegroundColor Green
    Copy-Item "$projectRoot\Alice_code\tests" -Destination $aliceCodeDest -Recurse -Exclude '__pycache__'
}

Write-Host "Copying React frontend files..." -ForegroundColor Green

# Copy React app files (excluding node_modules)
$reactItems = Get-ChildItem "$projectRoot\agent-starter-react" -Exclude 'node_modules', '.next', 'build', 'dist'
foreach ($item in $reactItems) {
    if ($item.PSIsContainer) {
        Copy-Item $item.FullName -Destination $reactDest -Recurse -Exclude 'node_modules', '.next'
    } else {
        Copy-Item $item.FullName -Destination $reactDest
    }
}

Write-Host "Copying documentation..." -ForegroundColor Green

# Copy docs folder
if (Test-Path "$projectRoot\docs") {
    Copy-Item "$projectRoot\docs\*" -Destination $docsDest -Recurse
}

Write-Host "Copying root files..." -ForegroundColor Green

# Copy root level files
$rootFiles = @(
    'alice_trigger.py',
    'start_alice.bat',
    'optimize-alice.bat',
    'README.md',
    'test.py'
)

foreach ($file in $rootFiles) {
    $filePath = Join-Path $projectRoot $file
    if (Test-Path $filePath) {
        Copy-Item $filePath -Destination $tempFolder
    }
}

# Create a comprehensive README for submission
Write-Host "Creating submission README..." -ForegroundColor Green

$readmeContent = @"
# ALICE AI Assistant - Submission Package

## 🤖 Project Overview
ALICE is an advanced, voice-based AI assistant with vision, OCR, and system automation capabilities.

## 📁 Project Structure

### Alice_code/
Core Python backend containing:
- **agent.py** - Main AI agent orchestration
- **alice_personal_safe.py** - System automation (14 functions)
- **alice_vision_tools.py** - Vision & OCR capabilities (11 tools)
- **alice_whatsapp_automation.py** - WhatsApp integration
- **Alice_prompts.py** - System prompts & personality
- **memory_loop.py / memory_store.py** - Memory management
- **mcp_client/** - Model Context Protocol integration
- **requirements.txt** - Python dependencies

### agent-starter-react/
Next.js web interface for ALICE:
- TypeScript + React frontend
- Runs on http://localhost:3000
- Real-time LiveKit integration

### docs/
Complete documentation and guides

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- Windows OS (for full automation features)

### Backend Setup
```bash
cd Alice_code
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup
```bash
cd agent-starter-react
npm install
# or
pnpm install
```

### Environment Variables
Create `.env` file in Alice_code/:
```
GOOGLE_API_KEY=your_gemini_api_key
MEM0_API_KEY=your_mem0_api_key
LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_livekit_key
LIVEKIT_API_SECRET=your_livekit_secret
```

### Run ALICE
```bash
# Using the security launcher (requires 4-digit code)
python alice_trigger.py

# Or use the batch file
start_alice.bat
```

## ✨ Key Features

### 1. Voice AI Assistant
- Real-time voice conversation
- Hinglish (Hindi + English) personality
- Google TTS/STT integration

### 2. Vision & OCR (11 Tools)
- Screen reading and analysis
- Text extraction from images
- UI element detection and interaction
- Screenshot capture

### 3. System Automation (14 Functions)
- Application launching
- File management
- Browser control
- Brightness adjustment
- Multi-app workflows

### 4. WhatsApp Automation
- Send messages
- Open chats
- Automated WhatsApp Desktop control

### 5. Memory System
- Conversation memory
- Persistent storage (Mem0)
- Context retention across sessions

## 🛠️ Built With

### Core Technologies
- **Python 3.11** - Backend logic
- **TypeScript/Next.js** - Frontend
- **LiveKit Agents** - Voice AI framework
- **Google Gemini** - Vision & language model
- **EasyOCR** - Text recognition
- **pywinauto** - Windows automation

### AI/ML
- LangChain - LLM orchestration
- Google Cloud AI - Speech/TTS/Vision
- OpenCV - Computer vision

### Frontend
- React, Tailwind CSS, TypeScript

## 📊 Project Statistics
- **Total Tools**: 30+ AI tools
- **Languages**: Python, TypeScript, Batch
- **Dependencies**: 100+ packages
- **Features**: Voice, Vision, Automation, Memory

## 🔐 Security
- 4-digit authentication launcher
- Safe personal mode controls
- Environment variable protection

## 👤 Author
Developed by Ankush

## 📄 License
See LICENSE file for details

---

**Note**: This package excludes:
- Virtual environments (venv, venv_new) - Install via requirements.txt
- node_modules - Install via npm/pnpm
- Cache files (__pycache__)
- Environment files (.env) - Create your own
- Large logs and temporary files
"@

Set-Content -Path (Join-Path $tempFolder "SUBMISSION_README.md") -Value $readmeContent

# Create installation guide
Write-Host "Creating installation guide..." -ForegroundColor Green

$installGuide = @"
# ALICE Installation Guide

## Step 1: Extract Files
Extract the entire submission package to your desired location.

## Step 2: Install Python Dependencies
```bash
cd Alice_code
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Step 3: Install Frontend Dependencies
```bash
cd agent-starter-react
npm install
```

## Step 4: Configure Environment
Create `.env` file in Alice_code/ with:
- GOOGLE_API_KEY
- MEM0_API_KEY  
- LIVEKIT credentials

## Step 5: Run ALICE
```bash
python alice_trigger.py
```

Default security code: **0007** (change in alice_trigger.py)

## Troubleshooting
- Ensure Windows OS for full automation
- Install WhatsApp Desktop for WhatsApp features
- Check firewall allows localhost:3000

For detailed documentation, see docs/ folder.
"@

Set-Content -Path (Join-Path $tempFolder "INSTALLATION_GUIDE.md") -Value $installGuide

Write-Host ""
Write-Host "Creating zip archive..." -ForegroundColor Green
Write-Host "This may take a moment..." -ForegroundColor Yellow

# Create the zip file
Compress-Archive -Path "$tempFolder\*" -DestinationPath $outputZip -CompressionLevel Optimal

# Get file size
$zipSize = (Get-Item $outputZip).Length / 1MB
$zipSizeMB = [math]::Round($zipSize, 2)

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ SUBMISSION PACKAGE CREATED!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Location: $outputZip" -ForegroundColor Cyan
Write-Host "Size: $zipSizeMB MB (Limit: 35 MB)" -ForegroundColor Cyan

if ($zipSizeMB -gt 35) {
    Write-Host ""
    Write-Host "⚠️  WARNING: File size exceeds 35 MB limit!" -ForegroundColor Red
    Write-Host "Consider removing additional files or splitting the submission." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "✅ Size is within the 35 MB limit!" -ForegroundColor Green
}

Write-Host ""
Write-Host "Package Contents:" -ForegroundColor White
Write-Host "  • Python source code (Alice_code/)" -ForegroundColor Gray
Write-Host "  • React frontend (agent-starter-react/)" -ForegroundColor Gray
Write-Host "  • Documentation (docs/)" -ForegroundColor Gray
Write-Host "  • Installation guides" -ForegroundColor Gray
Write-Host "  • Configuration files" -ForegroundColor Gray

Write-Host ""
Write-Host "Excluded (too large):" -ForegroundColor White
Write-Host "  • Virtual environments (install via requirements.txt)" -ForegroundColor Gray
Write-Host "  • node_modules (install via npm)" -ForegroundColor Gray
Write-Host "  • Cache files" -ForegroundColor Gray
Write-Host "  • Test files and logs" -ForegroundColor Gray

Write-Host ""
Write-Host "Cleaning up temporary files..." -ForegroundColor Yellow
Remove-Item $tempFolder -Recurse -Force

Write-Host "Done! Ready for submission." -ForegroundColor Green
Write-Host ""
