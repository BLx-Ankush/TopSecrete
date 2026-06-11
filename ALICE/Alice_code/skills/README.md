# Skills System

This module provides self-improving procedural memory that creates and refines skills from experience.

## Features

- **Auto-Creation**: Automatically create skills from complex task completions
- **Voice Activation**: Invoke skills via voice commands or slash commands
- **Skill Management**: List, view, create, edit, and delete skills
- **Skills Hub**: Share and discover community skills
- **Configuration**: Skills can prompt for configuration values

## Structure

```
skills/
├── __init__.py
├── manager.py              # Skills discovery and management
├── skill.py                # Skill class and metadata
└── voice_invoker.py        # Voice-activated skill invocation
```

## Skill Format

Skills are stored as markdown files with YAML frontmatter:

```markdown
---
name: skill-name
description: What this skill does
version: 1.0.0
platforms: [windows, linux, macos]
tags: [automation, system]
category: system
---

# Skill Instructions

Step-by-step instructions for the skill...
```

## Usage

```python
from skills.manager import SkillsManager

manager = SkillsManager(config)
messages = manager.invoke("skill-name", context)
```

## Storage

Skills are stored in `data/skills/` directory.
