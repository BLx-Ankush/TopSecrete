# 🤖 ALICE - Advanced Language Interactive Conversational Entity

Alice is an AI-powered voice assistant with vision capabilities, OCR, and multi-modal interactions built on LiveKit and OpenAI.

## ✨ Features

- 🎤 **Voice Interaction**: Natural conversation with voice input/output
- 👁️ **Vision & OCR**: Can see and read text from images and screen
- 🧠 **Persistent Memory**: Remembers context using Mem0
- 🌐 **Web Interface**: Beautiful Next.js frontend for interaction
- 🔒 **Security**: 4-digit code authentication system
- 🎯 **Multi-Provider**: Supports OpenAI, Google Gemini, Deepgram, AssemblyAI

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Node.js 18+ and pnpm
- OpenAI API key
- LiveKit account and credentials

### 1. Clone the Repository

```bash
git clone https://github.com/Project-ALICE-X/TopSecrete.git
cd TopSecrete/ALICE
```

### 2. Set Up Python Environment

```bash
cd Alice_code
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit .env and add your API keys
```

Required keys:
- `OPENAI_API_KEY` - From https://platform.openai.com/api-keys
- `LIVEKIT_API_KEY` - From https://cloud.livekit.io/
- `LIVEKIT_API_SECRET` - From https://cloud.livekit.io/
- `LIVEKIT_URL` - Your LiveKit server URL

### 4. Set Up Web Interface

```bash
cd ../agent-starter-react
cp .env.example .env
# Edit .env with same LiveKit credentials
pnpm install
```

### 5. Start Alice

```bash
cd ..
python alice_trigger.py
```

Default security code: `0007`

The web interface will open at: http://localhost:3000

## 📁 Project Structure

```
ALICE/
├── alice_trigger.py          # Security launcher
├── Alice_code/               # Backend Python agent
│   ├── agent.py             # Main agent logic
│   ├── alice_vision_tools.py # Vision/OCR capabilities
│   ├── requirements.txt     # Python dependencies
│   ├── .env.example         # Environment template
│   └── venv/               # Virtual environment (not in git)
│
├── agent-starter-react/     # Frontend web interface
│   ├── app/                # Next.js app
│   ├── components/         # React components
│   ├── package.json        # Node dependencies
│   ├── .env.example        # Frontend env template
│   └── node_modules/       # Dependencies (not in git)
│
└── docs/                   # Documentation
    ├── STARTUP_GUIDE.md
    ├── QUICK_FIX.md
    └── ENV_SETUP_GUIDE.md
```

## 🛠️ Configuration

### Environment Variables

#### Backend (.env in Alice_code/)

```env
# Required
OPENAI_API_KEY=sk-...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
LIVEKIT_URL=wss://...

# Optional
GOOGLE_API_KEY=...
MEM0_API_KEY=...
DEEPGRAM_API_KEY=...
ASSEMBLYAI_API_KEY=...
```

#### Frontend (.env in agent-starter-react/)

```env
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
LIVEKIT_URL=wss://...
```

## 🎯 Usage

### Starting Alice

#### Method 1: Security Trigger (Recommended)
```bash
python alice_trigger.py
# Enter code: 0007
```

#### Method 2: Manual Backend
```bash
cd Alice_code
venv\Scripts\python.exe agent.py dev
```

#### Method 3: Full System
```bash
cd agent-starter-react
pnpm run dev
```

### Voice Commands

- "Hello Alice" - Greet Alice
- "Alice, read the text on my screen" - OCR capture
- "What can you see?" - Vision analysis
- "Remember that..." - Store in memory
- "What did I tell you about..." - Recall memory

## 🐛 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "OPENAI_API_KEY not found" | Add key to `Alice_code/.env` |
| "pnpm not found" | Install: `npm install -g pnpm` |
| "Vision System error" | This is a warning, Alice will still work |
| "Port 3000 in use" | Close other apps or change port |
| "LiveKit connection failed" | Check credentials in `.env` |

See [QUICK_FIX.md](QUICK_FIX.md) for detailed solutions.

## 📚 Documentation

- [STARTUP_GUIDE.md](STARTUP_GUIDE.md) - Complete setup guide
- [QUICK_FIX.md](QUICK_FIX.md) - Common problems and solutions
- [ENV_SETUP_GUIDE.md](ENV_SETUP_GUIDE.md) - Environment variables guide
- [FINAL_SETUP_CHECKLIST.md](FINAL_SETUP_CHECKLIST.md) - Setup checklist

## 🔐 Security

- Never commit `.env` files
- Never share API keys publicly
- Change the default security code in `alice_trigger.py`
- Rotate API keys periodically
- Monitor API usage dashboards

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📜 License

[Your License Here]

## 🙏 Acknowledgments

Built with:
- [LiveKit](https://livekit.io/) - Real-time voice infrastructure
- [OpenAI](https://openai.com/) - AI models
- [Next.js](https://nextjs.org/) - Web framework
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) - OCR capabilities
- [Mem0](https://mem0.ai/) - Memory system

## 📞 Support

- 📧 Email: [your-email]
- 🐛 Issues: [GitHub Issues](https://github.com/Project-ALICE-X/TopSecrete/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/Project-ALICE-X/TopSecrete/discussions)

---

**Made with ❤️ by the Project ALICE Team**
