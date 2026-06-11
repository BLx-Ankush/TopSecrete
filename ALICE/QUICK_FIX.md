# 🔧 Alice Quick Fix Guide

## Common Startup Issues & Solutions

### 1. ⚠️ Vision System Warning
**Error Message:**
```
⚠️ Vision System: invalid literal for int() with base 10: 'OCR capabilities enabled...'
```

**Fix:** Already fixed! The updated `alice_trigger.py` now handles multi-line output correctly.

**What was the issue?**
- The vision check was trying to convert multi-line output to an integer
- Now it takes only the last line (the actual count) for parsing

---

### 2. ❌ npm/pnpm Not Found
**Error Message:**
```
❌ npm/pnpm not found
```

**Fix:**
1. Download and install Node.js from https://nodejs.org/ (LTS version)
2. After installation, open a new terminal and run:
   ```bash
   npm install -g pnpm
   ```
3. Verify installation:
   ```bash
   pnpm --version
   ```

---

### 3. 🐍 Wrong Python Version
**Error Message:**
```
🐍 Using Python: D:\ProjectAlice\venv\Scripts\python.exe
```

**Fix:** Already fixed! The new venv is now prioritized.

**Verification:**
- Run `python alice_trigger.py`
- You should see: `🐍 Using Python: d:\ALICE(NEW)\...\Alice_code\venv\Scripts\python.exe`

---

### 4. 📦 Missing Python Packages
**Error Message:**
```
ModuleNotFoundError: No module named 'livekit'
```

**Fix:**
```bash
cd Alice_code
venv\Scripts\pip.exe install -r requirements.txt
```

---

### 5. 🔑 Missing API Keys
**Error Message:**
```
Error: OPENAI_API_KEY not found
```

**Fix:**
1. Create a `.env` file in the `Alice_code` folder:
   ```env
   OPENAI_API_KEY=sk-your-key-here
   LIVEKIT_URL=wss://your-livekit-url
   LIVEKIT_API_KEY=your-livekit-key
   LIVEKIT_API_SECRET=your-livekit-secret
   ```

---

### 6. 🌐 Web Interface Won't Start
**Symptoms:**
- Backend starts but no web interface
- Cannot access http://localhost:3000

**Fix:**
```bash
cd agent-starter-react
pnpm install
pnpm run dev
```

---

### 7. 🔒 Security Code Issues
**Problem:** Forgot your security code or want to change it

**Fix:**
1. Open `alice_trigger.py`
2. Find the line:
   ```python
   SECURITY_CODE = "0007"  # Change this to your preferred 4-digit code
   ```
3. Change `0007` to your desired code
4. Save the file

---

### 8. 🔧 Rebuild Virtual Environment
**When to use:** If you have persistent package issues

**Steps:**
1. Delete the old venv:
   ```bash
   rmdir /s /q Alice_code\venv
   ```

2. Create a new venv:
   ```bash
   cd Alice_code
   python -m venv venv
   ```

3. Install packages:
   ```bash
   venv\Scripts\pip.exe install --upgrade pip
   venv\Scripts\pip.exe install -r requirements.txt
   ```

---

## ✅ Verification Checklist

Before starting Alice, verify:

- [ ] Node.js installed (`node --version`)
- [ ] pnpm installed (`pnpm --version`)
- [ ] Virtual environment exists at `Alice_code\venv\`
- [ ] `.env` file created with API keys
- [ ] Web dependencies installed (`node_modules` folder exists in `agent-starter-react`)

---

## 🆘 Still Having Issues?

1. Check the full error message carefully
2. Verify all prerequisites are installed
3. Try restarting your terminal/command prompt
4. Check that no other process is using port 3000
5. Review the `STARTUP_GUIDE.md` for detailed setup instructions

---

## 📞 Getting Help

If you continue to experience issues:

1. Check the console output for specific error messages
2. Verify your Python version: `python --version` (should be 3.10+)
3. Verify your Node version: `node --version` (should be 18+)
4. Check if all services (LiveKit, etc.) are running

---

**Last Updated:** 2026-06-09
**Alice Version:** Alpha
