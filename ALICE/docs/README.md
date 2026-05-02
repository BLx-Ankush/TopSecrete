# 🤖 ALICE-X - Advanced AI Assistant

<div align="center">

![ALICE Logo](./agent-starter-react/public/Alice.gif)

**ALICE-X** is a comprehensive AI assistant system with multimodal capabilities including voice interaction, computer vision, automation, and real-time web interface.

[![GitHub Stars](https://img.shields.io/github/stars/BLx-Ankush/ALICE-X?style=social)](https://github.com/BLx-Ankush/ALICE-X/stargazers)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://reactjs.org)

</div>

## 🌟 Overview

ALICE-X is a next-generation AI assistant created by **Ankush** that combines the power of modern AI with comprehensive system automation. It features voice interaction, computer vision, intelligent automation, and a beautiful real-time web interface built with React and LiveKit.

### 🎯 Key Features

- **🎙️ Voice Interaction**: Advanced speech recognition and synthesis
- **👁️ Computer Vision**: OCR, image analysis, and screen understanding
- **🤖 Smart Automation**: WhatsApp automation, app control, and system management
- **💻 Real-time Web Interface**: Modern React-based UI with LiveKit integration
- **🧠 Multiple AI Providers**: Support for various LLM providers including free options
- **💾 Memory System**: Persistent conversation memory and context retention
- **🔧 System Control**: Window management, keyboard/mouse automation
- **📱 Mobile Integration**: WhatsApp and messaging automation

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Node.js 18+ (for React frontend)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/BLx-Ankush/ALICE-X.git
   cd ALICE-X
   ```

2. **Set up Python environment**
   ```bash
   cd Alice_code
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

3. **Set up React frontend**
   ```bash
   cd agent-starter-react
   npm install
   ```

4. **Configure API keys**
   ```bash
   # Copy environment template
   cp Alice_code/.env.example Alice_code/.env
   # Edit .env file with your API keys
   ```

### 🏃‍♂️ Running ALICE

#### Option 1: Quick Start (Windows)
```bash
# Run Alice with optimizations
./optimize-alice.bat

# Or start Alice normally
./start_alice.bat
```

#### Option 2: Manual Start

**Backend (Alice Core)**
```bash
cd Alice_code
python alice_trigger.py
```

**Frontend (Web Interface)**
```bash
cd agent-starter-react
npm run dev
```

Then visit `http://localhost:3000` to access the web interface.

## 🏗️ Architecture

ALICE-X is built with a modular architecture:

```
ALICE-X/
├── 🧠 Alice_code/          # Core AI system
│   ├── 🎯 agent.py         # Main agent logic
│   ├── 👁️ alice_vision.py  # Computer vision
│   ├── 🎙️ alice_personal_mode.py # Voice interaction
│   ├── 📱 alice_whatsapp_automation.py # WhatsApp automation
│   ├── 🎮 alice_system_controller.py # System control
│   └── 💾 memory_store.py  # Memory management
├── 🌐 agent-starter-react/ # React web interface
├── 📚 docs/               # Documentation
└── 🛠️ Configuration files
```

### Core Components

- **🤖 Agent Core**: Main intelligence powered by multiple LLM providers
- **👁️ Vision System**: Advanced OCR and image understanding using Tesseract and AI models
- **🎙️ Voice Interface**: Speech-to-text and text-to-speech capabilities
- **📱 Automation Engine**: Smart automation for apps and system control
- **💾 Memory System**: Persistent storage and context management
- **🌐 Web Interface**: Real-time React frontend with LiveKit for video/audio

## 🔧 Features in Detail

### 🎙️ Voice Interaction
- **Speech Recognition**: Real-time voice commands
- **Text-to-Speech**: Natural voice responses
- **Conversation Flow**: Context-aware dialogue management

### 👁️ Computer Vision
- **OCR Capabilities**: Extract text from images and screenshots
- **Screen Analysis**: Understand and interact with desktop applications
- **Image Processing**: Advanced image analysis and manipulation

### 🤖 AI Integration
- **Multiple Providers**: OpenAI, Anthropic, local models, and free alternatives
- **Smart Routing**: Automatic provider selection based on task type
- **Cost Optimization**: Intelligent model selection for cost efficiency

### 📱 Automation
- **WhatsApp Integration**: Send messages, automate conversations
- **App Control**: Launch and control desktop applications
- **System Management**: File operations, window management
- **Keyboard/Mouse Control**: Programmatic input automation

### 💻 Web Interface
- **Real-time Communication**: Built with LiveKit for seamless interaction
- **Modern UI**: Beautiful React interface with dark/light themes
- **Live Chat**: Real-time conversation with Alice
- **Media Support**: Voice and video communication

## 📖 Usage Examples

### Basic Conversation
```python
# Start Alice and ask questions
"Hey Alice, what's the weather like today?"
"Alice, can you help me organize my desktop?"
"Show me the latest news about AI"
```

### Automation Tasks
```python
# WhatsApp automation
"Alice, send a message to John saying I'll be late"
"Check my WhatsApp messages"

# System control
"Alice, open my favorite music app"
"Take a screenshot and analyze what's on screen"
"Organize my Downloads folder"
```

### Vision Tasks
```python
# OCR and image analysis
"Alice, read the text from this image"
"What do you see in this screenshot?"
"Extract the important information from this document"
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the `Alice_code` directory:

```env
# AI Provider API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Voice & Audio
SPEECH_RECOGNITION_ENGINE=whisper
TTS_ENGINE=pyttsx3

# System Settings
DEBUG_MODE=false
ENABLE_VISION=true
ENABLE_AUTOMATION=true
```

### Customization
- **Personality**: Edit `Alice_prompts.py` to customize Alice's personality
- **Voice Settings**: Configure voice parameters in `alice_personal_mode.py`
- **Automation Rules**: Modify automation scripts in respective modules
- **UI Themes**: Customize the React interface in `agent-starter-react/`

## 📚 Documentation

For detailed documentation, see:

- [📋 API Setup Guide](./docs/API_SETUP.md)
- [🚀 Agent Starter Guide](./docs/AGENT_STARTER_README.md)
- [👁️ Vision System Documentation](./docs/ENHANCED_VISION_README.md)
- [📱 WhatsApp Automation Guide](./docs/ALICE_WHATSAPP_AUTOMATION_COMPLETE.md)
- [🧠 Memory & MCP Guide](./docs/ENABLING_MCP_MEM0_GUIDE.md)
- [🆓 Free VLM Setup](./docs/FREE_VLM_SETUP_GUIDE.md)

## 🧪 Testing

ALICE-X includes comprehensive testing:

```bash
# Run core tests
cd Alice_code
python test_alice_vision.py
python test_agent_vision_integration.py

# Run automation tests
python test_trigger_integration.py
```

## 🤝 Contributing

We welcome contributions! Here's how to help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit your changes**: `git commit -m 'Add amazing feature'`
4. **Push to the branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Guidelines

- Follow Python PEP 8 style guidelines
- Add tests for new features
- Update documentation for API changes
- Ensure cross-platform compatibility

## 🐛 Troubleshooting

### Common Issues

1. **API Key Errors**
   - Ensure all required API keys are set in `.env`
   - Check API key validity and quotas

2. **Voice Issues**
   - Install proper audio drivers
   - Check microphone/speaker permissions

3. **Automation Problems**
   - Run as administrator on Windows
   - Check system security settings

4. **Frontend Issues**
   - Clear browser cache
   - Check Node.js version compatibility

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Credits & Acknowledgments

**ALICE-X** was created and developed by **Ankush** with passion and dedication to advancing AI accessibility.

### Special Thanks
- **Ankush** - Creator, lead developer, and visionary behind ALICE-X
- The AI community for inspiration and tools
- Contributors who helped improve and expand ALICE's capabilities

### Technologies Used
- **AI/ML**: OpenAI API, Anthropic Claude, Ollama, Whisper
- **Computer Vision**: Tesseract OCR, Pillow, OpenCV
- **Web Technologies**: React, Next.js, LiveKit, TypeScript
- **System Integration**: PyAutoGUI, pycaw, psutil
- **Voice Processing**: SpeechRecognition, pyttsx3, sounddevice

## 🌟 Star History

If you find ALICE-X useful, please consider giving it a star ⭐ on GitHub!

## 📞 Support & Contact

- **Issues**: [GitHub Issues](https://github.com/BLx-Ankush/ALICE-X/issues)
- **Discussions**: [GitHub Discussions](https://github.com/BLx-Ankush/ALICE-X/discussions)
- **Documentation**: [Project Wiki](https://github.com/BLx-Ankush/ALICE-X/wiki)
- **📷 Instagram**: [Connect with Ankush](https://www.instagram.com/07__alone?utm_source=ig_web_button_share_sheet&igsh=ZDNlZDc0MzIxNw==)

---

<div align="center">

**Made with ❤️ by [Ankush](https://github.com/BLx-Ankush)**

*Empowering the future of AI assistance*

</div>
