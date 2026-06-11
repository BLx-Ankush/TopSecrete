# Multi-Platform Gateway

This module provides multi-platform messaging support for ALICE.

## Features

- **Multiple Platforms**: Telegram, Discord, Slack, WhatsApp, Signal, and more
- **Conversation Continuity**: Maintain context across platforms
- **Voice Memo Support**: Transcribe audio messages
- **Platform Hooks**: Customize behavior per platform
- **Secure Authentication**: DM pairing and user policies

## Structure

```
gateway/
├── __init__.py
├── base.py                 # Abstract PlatformAdapter class
├── telegram.py             # Telegram adapter
├── discord.py              # Discord adapter
├── slack.py                # Slack adapter
├── whatsapp.py             # WhatsApp adapter
└── manager.py              # Gateway orchestration
```

## Usage

```python
from gateway.manager import GatewayManager

manager = GatewayManager(config)
await manager.start()
```

## Configuration

See `data/config.yaml` for gateway configuration and platform credentials.

## Platform Setup

Each platform requires specific setup:
- **Telegram**: Bot token from @BotFather
- **Discord**: Bot token from Discord Developer Portal
- **Slack**: App credentials from Slack API
- **WhatsApp**: Business API credentials
