# ✅ Alice Final Setup Checklist

## 🎯 Current Status

### ✅ Completed (Already Done!)
- [x] Created fresh virtual environment at `Alice_code\venv\`
- [x] Installed 200+ Python packages
- [x] Fixed vision system parsing bug
- [x] Updated package.json to use new venv
- [x] Created `.env` files with your LiveKit credentials
- [x] Fixed alice_trigger.py startup script

### ⚠️ Needs Your Action

#### 1. 🔑 Add OpenAI API Key (CRITICAL!)

**File:** `Alice_code\.env`

**Find this line:**
```env
OPENAI_API_KEY=your_openai_api_key_here
```

**Replace with your actual key:**
```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Get your key here:** https://platform.openai.com/api-keys

---

#### 2. 📦 Install Node.js & pnpm

**Check if already installed:**
```bash
node --version
pnpm --version
```

**If not installed:**
1. Download Node.js from: https://nodejs.org/ (LTS version)
2. Install Node.js
3. Open a NEW terminal and run:
   ```bash
   npm install -g pnpm
   ```

---

#### 3. 🌐 Install Web Interface Dependencies

```bash
cd "d:\ALICE(NEW)\Alice Upgraded\Alice (Alpha)\ALICE\agent-starter-react"
pnpm install
```

This will take 2-3 minutes.

---

## 🚀 Starting Alice

### Option 1: Full System (Recommended)
```bash
cd "d:\ALICE(NEW)\Alice Upgraded\Alice (Alpha)\ALICE"
python alice_trigger.py
```
- Enter security code: `0007`
- Opens web interface automatically at http://localhost:3000

### Option 2: Backend Only
```bash
cd "d:\ALICE(NEW)\Alice Upgraded\Alice (Alpha)\ALICE\Alice_code"
venv\Scripts\python.exe agent.py dev
```

---

## 🔍 Verification Commands

### Check Python Environment
```bash
cd "d:\ALICE(NEW)\Alice Upgraded\Alice (Alpha)\ALICE\Alice_code"
venv\Scripts\python.exe --version
```
Should show: Python 3.11.x

### Check Installed Packages
```bash
venv\Scripts\pip.exe list | findstr livekit
```
Should show multiple livekit packages

### Check Environment Variables
```bash
type .env
```
Verify all keys are present (OpenAI should NOT be empty!)

---

## 📊 File Structure Overview

```
ALICE/
├── alice_trigger.py          ✅ Fixed (uses new venv)
├── STARTUP_GUIDE.md          ✅ Created
├── QUICK_FIX.md              ✅ Created  
├── ENV_SETUP_GUIDE.md        ✅ Created
├── FINAL_SETUP_CHECKLIST.md  ✅ This file
│
├── Alice_code/
│   ├── .env                  ⚠️ Add OpenAI key here!
│   ├── agent.py              ✅ Ready
│   ├── requirements.txt      ✅ Fixed
│   ├── venv/                 ✅ New venv created!
│   │   └── Scripts/
│   │       └── python.exe
│   └── alice_vision_tools.py ✅ Ready
│
└── agent-starter-react/
    ├── .env                  ✅ Created
    ├── package.json          ✅ Fixed (uses new venv)
    ├── node_modules/         ⚠️ Run 'pnpm install'
    └── app/                  ✅ Ready
```

---

## 🎬 Step-by-Step First Launch

### Step 1: Add OpenAI Key (2 minutes)
1. Open `Alice_code\.env` in Notepad
2. Find `OPENAI_API_KEY=your_openai_api_key_here`
3. Replace with your real key
4. Save and close

### Step 2: Install Node Dependencies (3-5 minutes)
```bash
cd "d:\ALICE(NEW)\Alice Upgraded\Alice (Alpha)\ALICE\agent-starter-react"
pnpm install
```

### Step 3: Start Alice (30 seconds)
```bash
cd "d:\ALICE(NEW)\Alice Upgraded\Alice (Alpha)\ALICE"
python alice_trigger.py
```

### Step 4: Enter Security Code
```
Enter 4-digit security code: 0007
```

### Step 5: Wait for Startup (1-2 minutes)
You'll see:
```
✅ Vision System: 11 tools ready
🐍 Using Python: ...\Alice_code\venv\Scripts\python.exe
🚀 Starting Alice...
✅ Found package manager: pnpm
🎉 ALICE IS READY!
🌐 Web Interface: http://localhost:3000
```

### Step 6: Open Browser
Navigate to: http://localhost:3000

---

## 🐛 Troubleshooting Quick Reference

| Error | Solution |
|-------|----------|
| "OPENAI_API_KEY not found" | Add key to `Alice_code\.env` |
| "pnpm not found" | Install: `npm install -g pnpm` |
| "Vision System error" | Ignore - it's just a warning |
| "Port 3000 in use" | Close other apps or change port |
| "ModuleNotFoundError" | Reinstall: `venv\Scripts\pip.exe install -r requirements.txt` |
| "LiveKit connection failed" | Check `.env` has correct LIVEKIT_URL format |

---

## 📚 Documentation Files

All guides are in the ALICE folder:

1. **STARTUP_GUIDE.md** - Complete setup instructions
2. **QUICK_FIX.md** - Common problems and solutions
3. **ENV_SETUP_GUIDE.md** - Detailed .env configuration
4. **FINAL_SETUP_CHECKLIST.md** - This file (quick reference)

---

## 🎉 Success Indicators

When Alice is running correctly, you'll see:

### Console Output:
```
✅ Code validated successfully
✅ Vision System: 11 tools ready
🐍 Using Python: ...\venv\Scripts\python.exe
🎉 ALICE IS READY!
🌐 Web Interface: http://localhost:3000
```

### Browser (localhost:3000):
- Alice interface loads
- LiveKit connection indicator shows "Connected"
- Microphone/camera permissions requested

### Test Voice:
- Click microphone button
- Say "Hello Alice"
- She should respond!

---

## 💡 Pro Tips

1. **Keep terminal open** - Don't close it while Alice is running
2. **Check logs** - Console output shows what Alice is doing
3. **First response is slow** - Subsequent ones are faster
4. **Voice quality** - Use a good microphone for best results
5. **API costs** - Monitor your OpenAI usage dashboard

---

## 🆘 Still Stuck?

### Quick Diagnostics:
```bash
# Check Python
cd Alice_code
venv\Scripts\python.exe --version

# Check packages
venv\Scripts\pip.exe list | findstr "livekit openai"

# Check .env
type .env | findstr "OPENAI_API_KEY"

# Check Node/pnpm
node --version
pnpm --version
```

### Most Common Issue:
**90% of startup failures are due to missing OpenAI API key!**

Make sure `Alice_code\.env` has:
```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxx
```
(Your actual key, not the placeholder!)

---

## 🎯 Next Steps After Successful Start

1. Test voice interaction
2. Try vision/OCR features ("Alice, read this text")
3. Explore the web interface settings
4. Check memory system (Mem0 integration)
5. Review API usage in dashboards

---

**Ready to go?** Just add your OpenAI key and run `python alice_trigger.py`!

🚀 **Good luck with Alice!**
