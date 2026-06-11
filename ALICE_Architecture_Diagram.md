# ALICE Architecture - Presentation Version

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERACTION LAYER                    │
├─────────────────────┬───────────────────────────────────────┤
│   Voice (Primary)   │         Text Platforms                │
│  ┌──────────────┐   │   ┌────────────────────────────┐     │
│  │   LiveKit    │   │   │  Multi-Platform Gateway    │     │
│  │   + Gemini   │   │   │  • Telegram  • Discord     │     │
│  │   Realtime   │   │   │  • WhatsApp  • Slack       │     │
│  └──────────────┘   │   └────────────────────────────┘     │
└─────────────────────┴───────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      AGENT CORE                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │         Agent Orchestrator                         │     │
│  │  • Turn Management    • Context Assembly           │     │
│  │  • Tool Execution     • Response Generation        │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │   LLM    │ │  Memory  │ │  Skills  │ │  Tools   │      │
│  │ Provider │ │ Provider │ │  System  │ │ Registry │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Session  │ │  Config  │ │   Cron   │ │ Approval │      │
│  │ Manager  │ │ Manager  │ │Scheduler │ │  System  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   EXECUTION LAYER                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  Local   │ │  Docker  │ │   SSH    │ │  Modal   │      │
│  │ Terminal │ │Container │ │  Remote  │ │Serverless│      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  SQLite  │ │   YAML   │ │   .env   │ │   Files  │      │
│  │ Sessions │ │  Config  │ │ Secrets  │ │Skills/Mem│      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. **Interaction Layer**
- **Voice**: LiveKit + Gemini Realtime (Primary)
- **Text**: Multi-platform gateway (Telegram, Discord, WhatsApp, Slack)

### 2. **Agent Core**
- Turn management and context assembly
- Tool execution orchestration
- Response generation

### 3. **Service Layer**
- **LLM Provider**: Multi-provider with fallback (OpenRouter, Anthropic, Gemini)
- **Memory Provider**: Pluggable backends (Honcho, Mem0, Built-in)
- **Skills System**: Self-improving procedural memory
- **Tool Registry**: Centralized tool management
- **Session Manager**: SQLite with FTS5 search
- **Config Manager**: YAML + .env with profiles
- **Cron Scheduler**: Natural language task scheduling
- **Approval System**: Security for dangerous operations

### 4. **Execution Layer**
- Local terminal, Docker containers, SSH remote, Modal serverless

### 5. **Storage Layer**
- SQLite for sessions, YAML for config, .env for secrets, Files for skills/memory

## Key Features

| Feature | Description |
|---------|-------------|
| **Voice-First** | LiveKit + Gemini Realtime for native audio processing |
| **Multi-Platform** | Telegram, Discord, WhatsApp, Slack integration |
| **Self-Improving** | Skills system learns from experience |
| **Multi-Provider LLM** | 200+ models with automatic fallback |
| **Pluggable Memory** | Multiple memory backends (Honcho, Mem0, etc.) |
| **Windows Automation** | Native Windows control and automation |
| **Hardware Control** | Raspberry Pi integration (servo, sensors) |
| **Browser Automation** | Advanced web interaction with anti-detection |
| **Cron Scheduling** | Natural language task scheduling |
| **Profile Isolation** | Multi-persona support with separate configs |

## Data Flow

```
User Input (Voice/Text)
    ↓
Agent Orchestrator
    ↓
Memory Prefetch → Context Assembly
    ↓
LLM Generation (with Tools)
    ↓
Tool Execution
    ↓
Memory Sync → Session Storage
    ↓
Response to User
```

## Technology Stack

- **Voice**: LiveKit Agents, Gemini Realtime Model
- **LLM**: OpenRouter, Anthropic, OpenAI, Gemini
- **Memory**: Honcho, Mem0, Supermemory, Built-in
- **Storage**: SQLite (FTS5), YAML, .env
- **Execution**: Python, Docker, SSH, Modal
- **Platforms**: Telegram, Discord, WhatsApp, Slack
- **Automation**: Windows API, Raspberry Pi GPIO
- **Browser**: Playwright, Camofox (anti-detection)
