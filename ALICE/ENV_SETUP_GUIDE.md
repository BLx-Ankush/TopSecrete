# 🔐 Alice Environment Variables Setup Guide

## 📋 Overview

Alice requires TWO separate `.env` files:
1. **Backend `.env`** - Located in `Alice_code/` folder
2. **Frontend `.env`** - Located in `agent-starter-react/` folder

Both files have been created for you with your LiveKit credentials!

---

## ⚠️ IMPORTANT: Missing API Keys

### ✅ What You Already Have:
- ✅ LiveKit API Key
- ✅ LiveKit API Secret  
- ✅ LiveKit URL (wss://alice-ojqmlipd.livekit.cloud)
- ✅ Google Gemini API Key
- ✅ Mem0 API Key (for memory)
- ✅ Deepgram API Key (for speech-to-text)
- ✅ AssemblyAI API Key (alternative STT)

### ❌ What You Need to Add:

#### 🔑 OpenAI API Key (REQUIRED!)

Alice needs an OpenAI API key for the voice agent functionality.

**How to get it:**
1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)
5. Add it to your `.env` file

**Edit this file:** `Alice_code\.env`

Find this line:
```env
OPENAI_API_KEY=your_openai_api_key_here
```

Replace `your_openai_api_key_here` with your actual key:
```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 📁 File Locations

### 1. Backend Environment File
**Location:** `d:\ALICE(NEW)\Alice Upgraded\Alice (Alpha)\ALICE\Alice_code\.env`

**Purpose:** Used by the Python backend (agent.py)

**Contains:**
- LiveKit credentials (Server connection)
- OpenAI API key (Voice & AI)
- Google Gemini key (Alternative LLM)
- Mem0 key (Memory system)
- Deepgram/AssemblyAI keys (Speech-to-Text)
- VAD configuration
- STT settings

### 2. Frontend Environment File
**Location:** `d:\ALICE(NEW)\Alice Upgraded\Alice (Alpha)\ALICE\agent-starter-react\.env`

**Purpose:** Used by the Next.js web interface

**Contains:**
- LiveKit credentials (Client connection)
- App configuration endpoints

---

## 🔧 LiveKit URL Formats

Your LiveKit URL can be in either format:

### WebSocket Format (Current - Recommended)
```env
LIVEKIT_URL=wss://alice-ojqmlipd.livekit.cloud
```

### HTTPS Format (Alternative)
```env
LIVEKIT_URL=https://alice-ojqmlipd.livekit.cloud
```

**If you get LiveKit connection errors, try switching between these two formats.**

---

## ✅ Verification Steps

### 1. Check Backend .env
```bash
cd "d:\ALICE(NEW)\Alice Upgraded\Alice (Alpha)\ALICE\Alice_code"
type .env
```

You should see:
- ✅ LIVEKIT_API_KEY
- ✅ LIVEKIT_API_SECRET
- ✅ LIVEKIT_URL
- ❗ OPENAI_API_KEY (needs your real key!)

### 2. Check Frontend .env
```bash
cd "d:\ALICE(NEW)\Alice Upgraded\Alice (Alpha)\ALICE\agent-starter-react"
type .env
```

You should see:
- ✅ LIVEKIT_API_KEY
- ✅ LIVEKIT_API_SECRET
- ✅ LIVEKIT_URL

---

## 🚨 Common Issues & Solutions

### Issue 1: "OPENAI_API_KEY not found"
**Solution:** Add your OpenAI API key to `Alice_code\.env`

### Issue 2: "LiveKit connection failed"
**Possible causes:**
1. Wrong URL format (try switching wss:// to https://)
2. Invalid API credentials
3. LiveKit server is down
4. Firewall blocking WebSocket connections

**Solutions:**
1. Verify your LiveKit dashboard shows these credentials
2. Try the alternative URL format
3. Check LiveKit status: https://status.livekit.io/
4. Temporarily disable firewall to test

### Issue 3: "Environment variables not loading"
**Solutions:**
1. Make sure the `.env` file is named exactly `.env` (not `.env.txt`)
2. Restart your terminal/command prompt
3. Restart the Alice application

### Issue 4: "Google API quota exceeded"
**Solution:** 
- This is optional, OpenAI will be used as primary
- Get a new key from: https://makersuite.google.com/app/apikey

---

## 🔒 Security Best Practices

1. **Never commit `.env` files to Git**
   - Already in `.gitignore`
   
2. **Rotate keys periodically**
   - Change your API keys every few months
   
3. **Use different keys for development and production**
   - Get separate keys for testing

4. **Monitor API usage**
   - Check your OpenAI dashboard regularly
   - Set usage limits to avoid unexpected charges

---

## 📊 API Cost Estimates

### OpenAI API (Pay as you go)
- **GPT-4 Turbo**: ~$0.01 per conversation
- **Whisper (STT)**: ~$0.006 per minute
- **TTS**: ~$0.015 per 1000 characters

### LiveKit (Your current plan)
- Check your plan at: https://cloud.livekit.io/

### Deepgram (STT)
- Free tier: 45 minutes/month
- Paid: $0.0043 per minute

---

## 🎯 Quick Start Checklist

After adding your OpenAI API key:

- [ ] Backend `.env` has OPENAI_API_KEY filled in
- [ ] Backend `.env` has valid LiveKit credentials
- [ ] Frontend `.env` exists with LiveKit credentials
- [ ] Saved both files
- [ ] Restarted terminal (if Alice was already running)

Now run:
```bash
python alice_trigger.py
```

---

## 📞 Need Help?

If you continue to have issues:

1. **Check the exact error message** - It will tell you which key is missing
2. **Verify key format** - OpenAI keys start with `sk-`
3. **Test LiveKit credentials** - Log into https://cloud.livekit.io/
4. **Check API quotas** - Make sure you haven't exceeded limits

---

**Last Updated:** 2026-06-09
**Status:** ✅ .env files created, ❗ OpenAI key needed
