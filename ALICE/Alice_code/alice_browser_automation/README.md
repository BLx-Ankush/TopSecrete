# Alice Browser Automation

Browser automation for Alice voice agent powered by Qwen Coder 2.5 3B via Ollama.

## Overview

Alice Browser Automation extends Alice's capabilities by integrating browser automation powered by a local Qwen Coder 2.5 3B model via Ollama. This feature enables Alice to handle complex web-based tasks through voice commands, including web bookings, desktop problem-solving, and application access.

### Key Features

- **DOM-First Architecture**: Uses structured DOM data instead of screenshots for 100% accuracy
- **Local Processing**: Qwen 3B model via Ollama for privacy and low latency
- **Voice-Driven**: Seamless integration with LiveKit voice agent
- **Persistent Sessions**: Maintains browser profiles for authenticated sessions
- **Robust Error Handling**: Graceful degradation with fallback strategies

### Action Suites

1. **Web Bookings**: Travel, food delivery, and event ticket bookings
2. **Problem Solving**: Web research and desktop problem resolution
3. **Application Access**: Access web applications with persistent login

## Installation

### System Requirements

- Python 3.10+
- Node.js 18+ (for Playwright)
- Ollama
- 8GB RAM minimum
- 10GB disk space

### Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Install Ollama (if not already installed)
# Visit: https://ollama.com/download

# Pull Qwen model
ollama pull qwen2.5-coder:3b
```

## Configuration

Copy the configuration template and customize:

```bash
cp alice_browser_automation_config.yaml ~/.alice/alice_browser_automation_config.yaml
```

Edit the configuration file to adjust settings:

```yaml
browser:
  headless_default: true
  max_concurrent_sessions: 3
  
qwen:
  host: "http://localhost:11434"
  model: "qwen2.5-coder:3b"
  
security:
  require_payment_confirmation: true
  validate_ssl: true
```

## Usage

### With Alice Voice Agent

```python
from alice_browser_automation import browser_automation

# Book a flight
result = await browser_automation(
    "Book a flight to Paris on December 25th",
    "web_booking",
    {"origin": "SFO", "destination": "CDG"}
)

# Solve a problem
result = await browser_automation(
    "Find solution for Python import error",
    "problem_solving",
    {"error": "ModuleNotFoundError"}
)

# Access application
result = await browser_automation(
    "Check my Gmail inbox",
    "app_access",
    {"app": "gmail", "action": "check_inbox"}
)
```

### Programmatic Usage

```python
from alice_browser_automation import BrowserAutomationEngine, TaskType

# Initialize engine
engine = BrowserAutomationEngine()
await engine.initialize()

# Execute task
result = await engine.execute_task(
    task_description="Book a flight to Paris",
    task_type=TaskType.WEB_BOOKING,
    parameters={"origin": "SFO", "destination": "CDG"},
    callback=lambda msg: print(f"Progress: {msg}")
)

# Cleanup
await engine.shutdown()
```

## Architecture

```
Alice Voice Agent (LiveKit)
    ↓
LiveKit-Qwen Bridge
    ↓
Browser Automation Engine
    ↓
browser-use + Playwright
    ↓
Chrome Browser
```

### Key Components

- **BrowserAutomationEngine**: Core orchestrator
- **DOMParser**: Extracts structured DOM data
- **QwenModelClient**: Interfaces with Ollama
- **SessionManager**: Manages browser sessions
- **OTPHandler**: Handles OTP verification
- **ChromeProfileManager**: Manages persistent profiles

## Security

- Credentials encrypted with system keychain
- SSL certificate validation
- No sensitive data in logs
- Payment confirmation required
- Local AI processing (no external API calls)

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest -m unit

# Run integration tests
pytest -m integration

# Run with coverage
pytest --cov=alice_browser_automation
```

### Code Quality

```bash
# Format code
black alice_browser_automation/

# Type checking
mypy alice_browser_automation/

# Linting
flake8 alice_browser_automation/
```

## Troubleshooting

### Ollama Not Available

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama service
ollama serve
```

### Playwright Issues

```bash
# Reinstall browsers
playwright install --force chromium
```

### Profile Issues

```bash
# Clear browser profiles
rm -rf ~/.alice/browser_profiles/*
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[User Guide](docs/USER_GUIDE.md)**: Voice commands, troubleshooting, and security best practices
- **[API Reference](docs/API_REFERENCE.md)**: Complete API documentation for all classes and methods
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)**: Architecture, extension points, and contributing guidelines

### Quick Links

- [Installation Guide](docs/USER_GUIDE.md#installation)
- [Voice Command Examples](docs/USER_GUIDE.md#voice-command-examples)
- [Troubleshooting](docs/USER_GUIDE.md#troubleshooting)
- [Adding New Action Suites](docs/DEVELOPER_GUIDE.md#adding-new-action-suites)
- [API Examples](docs/API_REFERENCE.md#complete-example)

## Support

For issues and questions:
- GitHub Issues: https://github.com/alice/alice-browser-automation/issues
- Documentation: [docs/](docs/)
- Email: support@alice-automation.com
