# LLM Provider System

This module provides multi-provider LLM support for ALICE with automatic fallback and credential rotation.

## Features

- **Multi-Provider Support**: OpenRouter, Anthropic, OpenAI, Google Gemini, and custom endpoints
- **Automatic Fallback**: Seamlessly switch to backup providers on failure
- **Credential Rotation**: Distribute requests across multiple API keys
- **Voice Integration**: Preserves Gemini Realtime Model for voice sessions
- **Context Management**: Automatic compression and caching support

## Structure

```
llm/
├── __init__.py
├── providers/
│   ├── base.py              # Abstract base class
│   ├── openrouter.py        # OpenRouter provider
│   ├── anthropic.py         # Anthropic Claude provider
│   ├── gemini.py            # Google Gemini (text mode)
│   └── gemini_realtime.py   # Gemini Realtime (voice mode)
├── credential_pool.py       # API key rotation
└── provider_manager.py      # Provider orchestration
```

## Usage

```python
from llm.provider_manager import LLMProviderManager

manager = LLMProviderManager(config)
response = await manager.generate(messages, tools)
```

## Configuration

See `data/config.yaml` for LLM configuration options.
