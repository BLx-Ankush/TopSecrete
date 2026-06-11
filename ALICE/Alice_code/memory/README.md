# Memory System

This module provides pluggable memory providers for persistent context across sessions.

## Features

- **Built-in Memory**: MEMORY.md and USER.md files (always active)
- **External Providers**: Honcho, Mem0, Supermemory, and more
- **Session Continuity**: Maintain context across conversations
- **Automatic Insights**: Extract and store key information
- **Tool Integration**: Memory providers can expose tools

## Structure

```
memory/
├── __init__.py
├── base.py                  # Abstract MemoryProvider class
├── builtin.py              # Built-in memory (MEMORY.md/USER.md)
├── honcho.py               # Honcho dialectic memory
├── mem0.py                 # Mem0 integration
└── manager.py              # Memory provider orchestration
```

## Usage

```python
from memory.manager import MemoryManager

manager = MemoryManager(config)
await manager.initialize(session_id, user_id)
context = await manager.prefetch(session_id)
```

## Configuration

See `data/config.yaml` for memory provider configuration.
