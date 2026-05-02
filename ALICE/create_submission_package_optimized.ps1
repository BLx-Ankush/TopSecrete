# ALICE Project Submission Package Creator - OPTIMIZED for 35MB limit
# Creates a clean zip file for submission (under 35 MB)

$projectRoot = "d:\ALICE(NEW)\Alice-main07"
$outputZip = "d:\ALICE(NEW)\ALICE_Project_Submission_Optimized.zip"
$tempFolder = "d:\ALICE(NEW)\ALICE_Temp_Package_Opt"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ALICE Optimized Submission Package" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Remove existing temp folder and zip if they exist
if (Test-Path $tempFolder) {
    Remove-Item $tempFolder -Recurse -Force
}
if (Test-Path $outputZip) {
    Remove-Item $outputZip -Force
}

# Create temp folder
New-Item -ItemType Directory -Path $tempFolder | Out-Null

# Create project structure
$aliceCodeDest = Join-Path $tempFolder "Alice_code"
$reactDest = Join-Path $tempFolder "agent-starter-react"

New-Item -ItemType Directory -Path $aliceCodeDest | Out-Null
New-Item -ItemType Directory -Path $reactDest | Out-Null

Write-Host "Copying essential Python files..." -ForegroundColor Green

# Copy only essential Alice_code files
$essentialFiles = @(
    'agent.py',
    'alice_personal_safe.py',
    'alice_vision_tools.py',
    'alice_vision.py',
    'alice_whatsapp_automation.py',
    'Alice_prompts.py',
    'memory_loop.py',
    'memory_store.py',
    'alice_system_controller.py',
    'Alice_duckduckgo_search.py',
    'alice_get_weather.py',
    'Alice_google_search.py',
    'alice_browser_automation.py',
    'alice_app_automation.py',
    'Alice_file_opener.py',
    'keyboard_mouse_CTRL.py',
    'Alice_window_CTRL.py',
    'alice_parameters_analysis.py',
    'alice_reasoning.py',
    'free_vlm_providers.py',
    'comprehensive_app_mapper.py',
    'requirements.txt',
    'alice_app_database.json',
    'apps_database.json',
    'pytest.ini',
    'performance_config.py',
    'ALICE_VISION_README.md',
    'Alice_Description.txt',
    'Alice_Summary.txt'
)

foreach ($file in $essentialFiles) {
    $filePath = Join-Path "$projectRoot\Alice_code" $file
    if (Test-Path $filePath) {
        Copy-Item $filePath -Destination $aliceCodeDest
    }
}

Write-Host "  Copied $($essentialFiles.Count) essential files" -ForegroundColor Gray

# Copy mcp_client folder (small)
if (Test-Path "$projectRoot\Alice_code\mcp_client") {
    Copy-Item "$projectRoot\Alice_code\mcp_client" -Destination $aliceCodeDest -Recurse -Exclude '__pycache__'
}

Write-Host "Copying React essentials (config only)..." -ForegroundColor Green

# Copy only React config files (no src folders to save space)
$reactConfigFiles = @(
    'package.json',
    'next.config.ts',
    'tsconfig.json',
    'tailwind.config.ts',
    'postcss.config.mjs',
    'components.json',
    'eslint.config.mjs',
    'README.md',
    'LICENSE'
)

foreach ($file in $reactConfigFiles) {
    $filePath = Join-Path "$projectRoot\agent-starter-react" $file
    if (Test-Path $filePath) {
        Copy-Item $filePath -Destination $reactDest
    }
}

# Copy app, components, lib folders from React (these are essential)
$reactFolders = @('app', 'components', 'lib', 'hooks', 'public')
foreach ($folder in $reactFolders) {
    $folderPath = Join-Path "$projectRoot\agent-starter-react" $folder
    if (Test-Path $folderPath) {
        Copy-Item $folderPath -Destination $reactDest -Recurse
    }
}

Write-Host "Copying root files..." -ForegroundColor Green

# Copy root level files
$rootFiles = @(
    'alice_trigger.py',
    'start_alice.bat',
    'README.md'
)

foreach ($file in $rootFiles) {
    $filePath = Join-Path $projectRoot $file
    if (Test-Path $filePath) {
        Copy-Item $filePath -Destination $tempFolder
    }
}

# Create comprehensive README
Write-Host "Creating documentation..." -ForegroundColor Green

$readmeContent = @"
# ALICE AI Assistant - Submission Package

## 🤖 About ALICE
ALICE is an advanced voice-based AI assistant built by Ankush, featuring:
- 👁️ Vision & OCR capabilities (11 tools)
- 🖥️ Windows system automation (14 functions)  
- 💬 WhatsApp automation
- 🧠 Persistent memory system
- 🎤 Real-time voice conversation (Hinglish)

## 📁 Package Contents

### /Alice_code/
**Core Python Backend** - All essential Python modules:
- agent.py - Main orchestration
- alice_personal_safe.py - System automation
- alice_vision_tools.py - 11 vision/OCR tools
- alice_whatsapp_automation.py - WhatsApp control
- memory_loop.py, memory_store.py - Memory management
- requirements.txt - All dependencies

### /agent-starter-react/
**Next.js Frontend** - Web interface configuration & source

### Root Files
- alice_trigger.py - Security launcher
- start_alice.bat - Windows launcher
- README.md - Main documentation

## 🚀 Quick Installation

### 1. Install Python Dependencies
\`\`\`bash
cd Alice_code
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
\`\`\`

### 2. Install Frontend Dependencies
\`\`\`bash
cd agent-starter-react
npm install
\`\`\`

### 3. Configure Environment
Create \`.env\` in Alice_code/:
\`\`\`
GOOGLE_API_KEY=your_gemini_key
MEM0_API_KEY=your_mem0_key
LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret
\`\`\`

### 4. Launch ALICE
\`\`\`bash
python alice_trigger.py
\`\`\`
Default code: **0007**

## ✨ Features Overview

### Voice AI
- Real-time conversation
- Google TTS/STT
- Hinglish personality

### Vision System (11 Tools)
- Screen reading & analysis
- OCR text extraction
- UI element detection
- Screenshot capture
- Click & type automation

### System Automation (14 Functions)
- App launching (Chrome, VS Code, etc.)
- File creation & management
- Browser control
- Multi-app workflows
- Screenshot & brightness control

### WhatsApp Automation
- Send messages to contacts
- Open specific chats
- Automated WhatsApp Desktop control

### Memory System
- Conversation memory
- Context retention
- Mem0 persistent storage

## 🛠️ Technology Stack

**Backend:** Python 3.11, LiveKit Agents, Google Gemini, EasyOCR, LangChain, pywinauto
**Frontend:** Next.js, React, TypeScript, Tailwind CSS
**AI/ML:** Google Cloud AI, OpenCV, ONNX Runtime
**Platform:** Windows OS (for full automation)

## 📊 Statistics
- **30+ AI Tools** available
- **100+ Dependencies**
- **Multi-modal**: Voice + Vision + Automation
- **Bilingual**: Hinglish (Hindi + English)

## 🔧 System Requirements
- Windows 10/11
- Python 3.11+
- Node.js 18+
- 4GB RAM minimum
- Internet connection

## 📝 Notes for Reviewers
**Excluded from package to meet 35MB limit:**
- Virtual environments (venv/) - Install via requirements.txt
- node_modules/ - Install via npm
- Cache files (__pycache__, .next/)
- Test scripts (9 files) - Available in full repository
- Documentation folder - Key docs included in README

**All core functionality is intact!**

## 🔐 Security
- 4-digit authentication system
- Safe personal mode controls
- Environment variable protection

## 👤 Developer
**Name:** Ankush
**Project:** ALICE AI Assistant
**Date:** March 2026

## 📧 Support
For installation issues or questions about the code, refer to inline documentation and comments within source files.

---

**Ready to experience ALICE? Follow the installation guide above!** 🚀
"@

Set-Content -Path (Join-Path $tempFolder "README.md") -Value $readmeContent

# Create quick start guide
$quickStart = @"
# ALICE Quick Start Guide

## Installation (5 minutes)

### Step 1: Python Setup
\`\`\`bash
cd Alice_code
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
\`\`\`

### Step 2: Frontend Setup  
\`\`\`bash
cd agent-starter-react
npm install
\`\`\`

### Step 3: Environment Variables
Create \`.env\` file in Alice_code/:
\`\`\`
GOOGLE_API_KEY=your_api_key
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
\`\`\`

### Step 4: Run
\`\`\`bash
python alice_trigger.py
\`\`\`

## Features to Try

### 1. Voice Commands
- "Hello Alice"
- "Alice, open Chrome"
- "Alice, what's on my screen?"

### 2. Vision Commands
- "Alice, read the text on screen"
- "Alice, take a screenshot"
- "Alice, click on the submit button"

### 3. Automation
- "Alice, enable personal mode"
- "Alice, open VS Code"
- "Alice, create a file called notes.txt"

### 4. WhatsApp (requires WhatsApp Desktop)
- "Alice, send message to [contact]"
- "Alice, open WhatsApp chat with [contact]"

## Troubleshooting

**Issue:** Module not found
**Fix:** Ensure venv is activated and all requirements installed

**Issue:** Frontend won't start
**Fix:** Check Node.js version (18+) and npm install completed

**Issue:** Vision not working
**Fix:** Ensure GOOGLE_API_KEY is set in .env

**Issue:** App won't open
**Fix:** Enable personal mode first

## Security Code
Default: **0007** (change in alice_trigger.py line 13)

Enjoy ALICE!
"@

Set-Content -Path (Join-Path $tempFolder "QUICKSTART.md") -Value $quickStart

Write-Host ""
Write-Host "Creating optimized zip archive..." -ForegroundColor Green

# Create the zip file
Compress-Archive -Path "$tempFolder\*" -DestinationPath $outputZip -CompressionLevel Optimal

# Get file size
$zipSize = (Get-Item $outputZip).Length / 1MB
$zipSizeMB = [math]::Round($zipSize, 2)

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ OPTIMIZED PACKAGE CREATED!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Location: $outputZip" -ForegroundColor Cyan
Write-Host "Size: $zipSizeMB MB (Limit: 35 MB)" -ForegroundColor Cyan

if ($zipSizeMB -gt 35) {
    Write-Host ""
    Write-Host "⚠️  WARNING: Still exceeds 35 MB!" -ForegroundColor Red
    Write-Host "Size difference: $([math]::Round($zipSizeMB - 35, 2)) MB over limit" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "✅ PERFECT! Size is within the 35 MB limit!" -ForegroundColor Green
    Write-Host "Available margin: $([math]::Round(35 - $zipSizeMB, 2)) MB" -ForegroundColor Green
}

Write-Host ""
Write-Host "Optimized Package Contents:" -ForegroundColor White
Write-Host "  ✅ All essential Python source code" -ForegroundColor Gray
Write-Host "  ✅ React frontend configuration & source" -ForegroundColor Gray
Write-Host "  ✅ Comprehensive README" -ForegroundColor Gray
Write-Host "  ✅ Quick start guide" -ForegroundColor Gray
Write-Host "  ✅ Installation instructions" -ForegroundColor Gray

Write-Host ""
Write-Host "Smart Exclusions:" -ForegroundColor White
Write-Host "  • Heavy documentation folder (kept essentials in README)" -ForegroundColor Gray
Write-Host "  • Sample/test data files" -ForegroundColor Gray
Write-Host "  • Debug logs and screenshots" -ForegroundColor Gray
Write-Host "  • Test scripts (kept in original repository)" -ForegroundColor Gray

Write-Host ""
Write-Host "Cleaning up..." -ForegroundColor Yellow
Remove-Item $tempFolder -Recurse -Force

Write-Host "✅ Ready for submission!" -ForegroundColor Green
Write-Host ""
