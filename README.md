# ALICE — Voice‑First Agentic Assistant (Problem Statement 1)

Sapthagiri NPS University Hackathon project targeting:

**Problem Statement 1: “Voice agents that actually complete tasks (not just talk)”**

ALICE is a Windows‑first, voice‑driven AI assistant that can understand intent across multiple steps and **take real actions** on your device and the web—while staying robust to interruptions, corrections, and flaky networks.

## Why today’s voice assistants fall short

Most mainstream assistants (e.g., Alexa/Google Assistant) are great at single‑turn Q&A, but struggle with:

- **Multi‑step task completion** (booking flows, forms, resolving issues end‑to‑end)
- **Tool execution** beyond simple APIs (desktop apps, UI workflows, browser flows)
- **Context + corrections** (“No, open the other file”, “Wait—send to Mom, not Dad”)
- **Reliability** in the real world (timeouts, UI changes, noisy environments)

In short: they “talk”, but they often don’t “do”.

## Introducing ALICE

ALICE behaves like a voice‑first operating layer on top of a Windows machine:

- Understands a request, asks only what’s needed
- Breaks it into steps and uses tools to execute
- Verifies outcomes using vision/OCR when applicable
- Recovers gracefully from failures (timeouts, retries, fallbacks)

ALICE is built around a realtime voice pipeline (LiveKit) and a tool‑calling agent runtime that can invoke:

- desktop automation (open apps, control windows, system actions)
- web browsing automation
- vision + OCR (read screen/text, reason about UI)
- utilities like search and weather

## What ALICE can do (high level)

- **Voice‑first conversation** with realtime audio sessions
- **Agentic task completion** using callable tools (APIs + workflows)
- **Desktop automation (Windows)**: app launching, window control, keyboard/mouse actions
- **Vision + OCR**: analyze screenshots/screen text and use that to guide actions
- **Browser automation** (Playwright‑based) for multi‑step web tasks
- **Memory (optional)**: persist useful user context across sessions (when configured)
- **Safety gate**: a 4‑digit code launcher before starting the full system

## How it maps to Problem Statement 1

ALICE is designed to satisfy the three key requirements:

1) **Understands intent across multiple steps**
- Maintains conversational context while planning the next actionable step.

2) **Takes actions (APIs, workflows)**
- Executes tasks through tools: desktop automation, web automation, information tools.

3) **Handles corrections and interruptions naturally**
- The agent loop supports iterative execution: user can interrupt, correct, and ALICE continues from the new intent.

## Tech stack overview

**Backend / Agent runtime (Python)**

- Python (agent + tools)
- LiveKit Agents (realtime session orchestration)
- LiveKit plugins (voice pipeline pieces; provider depends on configured keys)
- Tool wrappers (LangChain tools + LiveKit tool decorators)
- Requests/HTTP + retry/backoff for network resilience

**Vision & Automation (Windows)**

- OCR + image pipeline (EasyOCR / OpenCV / Pillow)
- UI automation helpers (pywinauto, pyautogui, window utilities)
- System utilities (psutil, app mapping)

**Browser automation**

- Playwright (robust scripted browser control)
- Error handling + retries for step execution

**Frontend (Web UI)**

- Next.js + React + TypeScript
- Tailwind CSS
- LiveKit client components to interact with the agent session

## Repo layout (important bits)

- [ALICE/alice_trigger.py](ALICE/alice_trigger.py): secure launcher (4‑digit code) + startup
- [ALICE/Alice_code/agent.py](ALICE/Alice_code/agent.py): main agent runtime
- [ALICE/Alice_code/alice_vision.py](ALICE/Alice_code/alice_vision.py): screen/window scanning + OCR pipeline
- [ALICE/Alice_code/alice_vision_tools.py](ALICE/Alice_code/alice_vision_tools.py): vision actions exposed as tools
- [ALICE/Alice_code/alice_browser_automation_integration.py](ALICE/Alice_code/alice_browser_automation_integration.py): browser automation bridge
- [ALICE/agent-starter-react](ALICE/agent-starter-react): Next.js web interface

## Running ALICE (local)

Prereqs:

- Windows
- Python installed
- Node.js 18+ (for the web UI)

Start (secure launcher):

```powershell
python ALICE/alice_trigger.py
```

Notes:

- The launcher starts the web UI (default: `http://localhost:3000`) when Node tooling is available.
- Some features require environment keys (model/voice providers, optional memory). See `ALICE/Alice_code/.env.example` for guidance.

## Conclusion

Problem Statement 1 asks for voice agents that *complete tasks*—not just respond. ALICE is built as an agentic, voice‑first system that can plan, execute, verify, and recover using real tools (desktop + browser + vision). The result is a practical assistant that moves beyond “talking” into reliable, multi‑step task completion.