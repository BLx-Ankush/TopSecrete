# 🚀 Alice AI Assistant - Startup Guide

## ✅ Setup Complete!

A fresh virtual environment has been created specifically for Alice at:
`Alice_code\venv\`

## 📋 Prerequisites

Before starting Alice, make sure you have:

### 1. Node.js and pnpm (Required for Web Interface)
- **Node.js**: Download from [nodejs.org](https://nodejs.org/) (LTS version recommended)
- **pnpm**: After installing Node.js, run: `npm install -g pnpm`

### 2. Environment Variables
Create a `.env` file in `Alice_code\` directory with your API keys:

```env
# OpenAI API Key (Required)
OPENAI_API_KEY=your_openai_api_key_here

# LiveKit Server Configuration (Required)
LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret

# Optional: Google API Keys for Speech/TTS
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
```

### 3. Install Web Interface Dependencies
Navigate to the React app folder and install dependencies:

```bash
cd "agent-starter-react"
pnpm install
```

## 🎬 Starting Alice

### Method 1: Using the Security Trigger (Recommended)
```bash
python alice_trigger.py
```
- Enter your 4-digit security code (default: `0007`)
- Alice will start both backend and web interface automatically

### Method 2: Manual Start (Backend Only)
```bash
cd Alice_code
venv\Scripts\python.exe agent.py dev
```

### Method 3: Full System (Backend + Web)
From the `agent-starter-react` folder:
```bash
pnpm run dev
```

## 🔧 What Was Fixed

1. ✅ Created new virtual environment at `Alice_code\venv\`
2. ✅ Installed all Python dependencies (200+ packages)
3. ✅ Fixed vision system check to handle multi-line output
4. ✅ Updated `package.json` to use the new venv path
5. ✅ Fixed `alice_trigger.py` to prioritize the new venv

## 🐛 Troubleshooting

### "npm/pnpm not found"
- Install Node.js from [nodejs.org](https://nodejs.org/)
- Install pnpm: `npm install -g pnpm`

### "Vision System Error"
- This is a minor issue with output parsing
- Alice will still start and function normally
- Vision tools will be available even if the check shows a warning

### "Invalid security code"
- Default code is `0007`
- Change it in `alice_trigger.py` by editing the `SECURITY_CODE` variable

### Python Package Issues
If you encounter missing package errors:
```bash
cd Alice_code
venv\Scripts\pip.exe install -r requirements.txt
```

## 📝 Important Notes

- **First Start**: The first startup may take longer as the system initializes
- **Port 3000**: The web interface runs on `http://localhost:3000`
- **LiveKit**: Make sure your LiveKit server is running and accessible
- **API Keys**: Alice requires valid OpenAI and LiveKit credentials to function

## 🎯 Next Steps

1. Install Node.js and pnpm if you haven't already
2. Create your `.env` file with API keys
3. Run `pnpm install` in the `agent-starter-react` folder
4. Start Alice using `python alice_trigger.py`
5. Open `http://localhost:3000` in your browser

## 📚 Additional Resources

- **Alice Documentation**: Check the main `README.md` file
- **LiveKit Docs**: https://docs.livekit.io/
- **OpenAI API**: https://platform.openai.com/docs

---

🎉 **You're all set!** Alice is ready to assist you with vision, OCR, and conversational AI capabilities.
