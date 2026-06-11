# ALICE Data Directory

This directory contains all persistent data for ALICE with Hermes integration.

## Structure

```
data/
├── config.yaml              # Main configuration file
├── .env                     # API keys and secrets (not in git)
├── MEMORY.md                # Built-in memory (always active)
├── USER.md                  # User profile and preferences
├── SOUL.md                  # Personality definition
├── config/                  # Additional config files
├── skills/                  # Active skills (markdown files)
├── sessions/                # Conversation history (SQLite)
├── memory/                  # Memory provider data
├── cron/                    # Scheduled tasks and logs
└── logs/                    # Application logs
```

## Files

### config.yaml
Main configuration file for ALICE. Contains settings for:
- LLM providers and models
- Voice configuration (LiveKit + Gemini Realtime)
- Memory providers
- Skills system
- Tools and toolsets
- Gateway platforms
- Cron scheduler
- Security settings
- Personality configuration

### .env
Environment variables and API keys. **Never commit this file to git.**

Required variables:
- `LIVEKIT_URL` - LiveKit server URL
- `LIVEKIT_API_KEY` - LiveKit API key
- `LIVEKIT_API_SECRET` - LiveKit API secret
- `GEMINI_API_KEY` - Google Gemini API key

Optional variables:
- `OPENROUTER_API_KEY` - OpenRouter API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `MEM0_API_KEY` - Mem0 API key
- `HONCHO_API_KEY` - Honcho API key

### MEMORY.md
Built-in memory file that stores persistent memories and insights from conversations. This file is automatically updated by ALICE's memory system.

### USER.md
User profile and preferences. Can be manually edited or updated by ALICE during conversations.

### SOUL.md
Personality definition for ALICE. Defines:
- Core identity and traits
- Communication style
- Language preferences (Hinglish)
- Values and behavioral guidelines
- Special capabilities

## Directories

### config/
Additional configuration files for specific components.

### skills/
Active skills stored as markdown files with YAML frontmatter. Skills are automatically created from complex task completions or manually added.

### sessions/
SQLite database with conversation history and FTS5 full-text search.

### memory/
Data for external memory providers (Honcho, Mem0, etc.).

### cron/
Scheduled tasks configuration (`jobs.yaml`) and execution logs.

### logs/
Application logs:
- `agent.log` - Main agent logs
- `errors.log` - Error logs
- `gateway.log` - Gateway/platform logs

## Security

- `.env` file should have 0600 permissions (owner read/write only)
- Never commit `.env` to version control
- Use `.env.example` as a template
- Store sensitive data only in `.env`, not in `config.yaml`

## Backup

Important files to backup:
- `config.yaml` - Configuration
- `MEMORY.md` - Memories
- `USER.md` - User profile
- `skills/` - Custom skills
- `sessions/` - Conversation history
- `memory/` - Memory provider data

## Migration

When upgrading from basic ALICE to Hermes integration:
1. Existing `.env` is preserved
2. `config.yaml` is generated from existing settings
3. Tools are converted to plugins
4. Memory data is preserved
5. Session history is migrated to SQLite

See migration documentation for details.
