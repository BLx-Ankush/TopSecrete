# ALICE-X

ALICE-X is a multimodal desktop AI assistant by Ankush, built to combine real-time voice conversation, on-screen understanding, app automation, and a web control interface in one system.

It is designed for practical daily use on Windows: talk to Alice, ask it to analyze your screen, open apps, automate workflows, and manage information with memory-aware responses.

## Creator Credentials and Acknowledgment

This project is independently conceptualized, architected, and developed by Ankush.

- Creator: Ankush Kumar
- Project: ALICE-X (Advanced Multimodal AI Assistant)
- Role: AI Engineer, System Architect, Full-Stack Developer
- Focus Areas: Voice AI, Vision AI, Desktop Automation, Realtime Agent Systems

Suggested acknowledgment text for portfolio/profile use:

"I built ALICE-X as an end-to-end multimodal AI assistant platform integrating realtime voice interaction, Gemini-powered intelligence, vision analysis, memory, and desktop automation with a production-style web interface."

If you want to publish this project publicly, keep this acknowledgment block in the README to preserve authorship and project provenance.

## Core Idea

The core idea behind ALICE is to behave like an always-available, voice-first personal operating layer on top of your computer.

Instead of only answering text prompts, ALICE is designed to:
- listen and speak in real time,
- see and analyze screen and image content,
- execute desktop actions safely,
- automate repetitive tasks (including WhatsApp flows),
- remember useful user context across sessions.

## Key Features

- Real-time voice assistant pipeline using LiveKit.
- Gemini-powered conversational model (audio-native realtime model in the active agent).
- Enhanced vision system with screenshot analysis, UI understanding, OCR, and click/type helpers.
- Gemini VLM image analysis with automatic fallback to free VLM providers.
- Desktop automation for app launching, file operations, browser actions, and system controls.
- WhatsApp desktop automation (open chat, search contact, send message).
- Persistent memory via Mem0 cloud storage (optional, API key based).
- Security launcher with 4-digit code gate.
- React + Next.js web interface for running and interacting with the agent.

## Architecture Overview

```text
ALICE-X
|- alice_trigger.py                 # Security entry launcher
|- Alice_code/
|  |- agent.py                      # Main LiveKit agent runtime
|  |- Alice_prompts.py              # Assistant behavior and reply prompt templates
|  |- alice_vision.py               # Window/UI scanning, OCR pipeline
|  |- alice_vision_tools.py         # LiveKit tool wrappers for vision actions
|  |- alice_personal_safe.py        # Safe app/system automation layer
|  |- alice_whatsapp_automation.py  # WhatsApp automation workflow
|  |- memory_store.py               # Mem0 memory client wrapper
|  |- memory_loop.py                # Background conversation memory extraction
|  |- free_vlm_providers.py         # Ollama/HuggingFace/Together fallbacks
|  |- mcp_client/                   # MCP client helpers
|- agent-starter-react/             # Next.js + LiveKit frontend
|- docs/                            # Extended setup and integration docs
```

## Technologies Used

### Backend and Agent

- Python 3.11+
- LiveKit Agents (`livekit`, `livekit-agents`, `livekit-api`)
- LiveKit plugins (`livekit-plugins-google`, `livekit-plugins-openai`, `livekit-plugins-silero`, `livekit-plugins-deepgram`, noise cancellation)
- Google GenAI libraries (`google-genai`, `google.generativeai` usage in vision tools)
- Mem0 (`mem0ai`) for long-term memory
- LangChain packages for tooling support

### Vision and Automation

- EasyOCR
- OpenCV (`opencv-python`)
- Pillow
- pyautogui
- pywinauto
- PyGetWindow
- psutil

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- LiveKit React components and LiveKit client SDK
- Three.js and react-three-fiber stack for 3D/avatar features

## Integrations

## 1) Google Gemini Integration

Active in the current runtime.

- Main realtime model in `Alice_code/agent.py` uses:
  - `google.beta.realtime.RealtimeModel`
  - model: `gemini-2.5-flash-native-audio-preview-12-2025`
- Vision analysis in `Alice_code/alice_vision_tools.py` uses:
  - `gemini-2.0-flash`
  - screen/image analysis helpers (`analyze_screen_with_gemini`, `analyze_image_with_gemini`)
- Requires Google API credentials (typically `GOOGLE_API_KEY` or equivalent Gemini key setup).

## 2) Google Cloud Integration

Partially active / dependency-ready.

- Installed dependencies include:
  - `google-cloud-speech`
  - `google-cloud-texttospeech`
  - `google-api-core`, `google-auth`
- LiveKit Google plugin is installed and used in agent runtime.
- In this codebase, Gemini integration is actively wired; Google Cloud Speech/TTS libraries are present for extension and can be enabled in voice pipelines as needed.

## 3) LiveKit Integration

Active and central to ALICE.

- Realtime session orchestration via LiveKit Agents.
- Agent startup and room session lifecycle in `Alice_code/agent.py`.
- Frontend communicates via LiveKit in `agent-starter-react`.
- Noise cancellation plugin enabled in session input options.

## 4) Vision Integration (Gemini + OCR + UI Automation)

Active.

- `alice_vision.py` handles window discovery, active UI scanning, OCR extraction, screenshot capture, input simulation.
- `alice_vision_tools.py` exposes vision actions as callable tools for the agent.
- Hybrid strategy:
  - Gemini VLM for high-level understanding,
  - EasyOCR/OpenCV for text extraction and fallback,
  - cache, preprocessing, and failure-handling for stability.

## 5) Free VLM Fallback Integrations

Active when configured.

`free_vlm_providers.py` supports:
- Ollama vision models (local)
- Hugging Face inference API
- Together AI vision API

If Gemini is unavailable, ALICE can fall back to these providers (depending on keys/local setup).

## 6) Mem0 Memory Integration

Optional but implemented.

- `memory_store.py` uses Mem0 cloud client for storing and retrieving user conversation memory.
- `memory_loop.py` continuously captures new session messages and saves them.
- Enable with `MEM0_API_KEY`.

## 7) WhatsApp Desktop Integration

Active.

- `alice_whatsapp_automation.py` automates:
  - opening WhatsApp,
  - searching/selecting contact,
  - focusing message input,
  - sending message safely.
- Uses pyautogui and vision-assisted verification to reduce misclick risks.

## 8) System and App Automation Integration

Active.

- `alice_personal_safe.py` provides app discovery and execution methods.
- Supports opening common apps, browser actions, screenshot utilities, file/system operations.
- Includes Windows registry and Start Menu app mapping logic.

## 9) Search and Information Integration

Active.

- `Alice_duckduckgo_search.py` uses DuckDuckGo search for web lookup without requiring a paid search API.

## 10) MCP Integration

Code present, currently disabled in active runtime.

- `Alice_code/mcp_client/` exists with MCP client utilities.
- In `Alice_code/agent.py`, MCP dynamic server/tool loading is currently commented out due to dependency conflict.
- Can be re-enabled once dependency compatibility is resolved.

## Setup

## Prerequisites

- Windows (primary target environment)
- Python 3.11+
- Node.js 18+
- pnpm or npm

## 1) Python setup

```powershell
cd Alice_code
python -m venv venv_new
venv_new\Scripts\activate
pip install -r requirements.txt
```

## 2) Frontend setup

```powershell
cd agent-starter-react
pnpm install
```

## 3) Environment variables

Create and configure `Alice_code/.env` with required keys.

Recommended keys:
- `GOOGLE_API_KEY` (Gemini and vision)
- `MEM0_API_KEY` (memory)
- `HUGGINGFACE_API_KEY` (optional free VLM fallback)
- `TOGETHER_API_KEY` (optional free VLM fallback)
- LiveKit-related env values depending on your deployment

## Running ALICE

## Quick launcher

```powershell
python alice_trigger.py
```

or

```powershell
start_alice.bat
```

## Full web + backend dev

```powershell
cd agent-starter-react
pnpm dev
```

This runs:
- Next.js frontend
- Python agent backend (via `Alice_code/agent.py`)

## Useful Documents

- `docs/API_SETUP.md`
- `docs/ENHANCED_VISION_README.md`
- `docs/FREE_VLM_SETUP_GUIDE.md`
- `docs/ENABLING_MCP_MEM0_GUIDE.md`
- `docs/ALICE_WHATSAPP_AUTOMATION_COMPLETE.md`
- `docs/ALICE_AVATAR_GUIDE.md`

## Current Integration Status Summary

- Gemini Realtime (core agent): Active
- Gemini Vision tools: Active
- LiveKit backend/frontend pipeline: Active
- EasyOCR/OpenCV vision fallback: Active
- WhatsApp automation: Active
- Mem0 memory: Implemented (requires key)
- Free VLM providers: Implemented (requires provider setup)
- MCP dynamic server tools: Present but currently disabled
- Google Cloud Speech/TTS packages: Installed and ready for pipeline extension

## Notes

- This project includes powerful desktop automation. Run with care on production machines.
- Some features rely on the target app window being visible and focused.
- For safety, validate automation commands on a test environment first.
