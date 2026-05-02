# Alice Browser Automation - Installation Guide

This guide walks you through installing and setting up Alice Browser Automation.

## Prerequisites

- **Python 3.10 or higher**
- **8GB RAM minimum** (recommended for Qwen 3B model)
- **10GB free disk space** (for Playwright browsers and Qwen model)
- **Operating System**: Windows, macOS, or Linux

## Quick Start

Run the master setup script to install everything automatically:

```bash
cd ALICE/Alice_code/alice_browser_automation
python setup.py
```

This will:
1. Install all Python dependencies
2. Install Playwright Chromium browser
3. Check Ollama installation and provide instructions if needed
4. Download Qwen 2.5 Coder 3B model
5. Create configuration files
6. Set up directory structure
7. Verify the installation

## Manual Installation

If you prefer to install components individually:

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Install Playwright Browsers

```bash
python -m playwright install chromium
```

On Linux, you may also need system dependencies:

```bash
python -m playwright install-deps chromium
```

### Step 3: Install Ollama

#### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

#### macOS

Download from [ollama.com/download](https://ollama.com/download) or use Homebrew:

```bash
brew install ollama
```

#### Windows

Download the installer from [ollama.com/download](https://ollama.com/download)

### Step 4: Start Ollama Service

```bash
ollama serve
```

Keep this running in a separate terminal.

### Step 5: Download Qwen Model

```bash
ollama pull qwen2.5-coder:3b
```

This will download approximately 2GB of data.

### Step 6: Set Up Configuration

```bash
python setup_config.py
```

This creates:
- `alice_browser_automation_config.yaml` - Main configuration file
- `.env.example` - Environment variables template
- Browser profile directory structure

### Step 7: Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and configure as needed. The defaults should work for most setups.

### Step 8: Verify Installation

```bash
python verify_installation.py
```

This runs comprehensive checks to ensure everything is working correctly.

## Individual Scripts

### install.py

Installs all dependencies and downloads required components.

```bash
python install.py
```

**What it does:**
- Checks Python version (3.10+ required)
- Verifies system resources (8GB RAM, 10GB disk)
- Installs Python packages from requirements.txt
- Installs Playwright Chromium browser
- Checks Ollama installation
- Downloads Qwen 2.5 Coder 3B model
- Creates directory structure

### setup_config.py

Creates and configures all configuration files.

```bash
python setup_config.py
```

**What it does:**
- Generates `alice_browser_automation_config.yaml` with defaults
- Creates/updates `.env.example`
- Creates browser profile directory structure
- Validates configuration

### verify_installation.py

Verifies that all components are properly installed.

```bash
python verify_installation.py
```

**What it does:**
- Checks Python packages are installed
- Verifies Playwright installation
- Tests Ollama service connectivity
- Verifies Qwen model availability
- Tests Qwen model response
- Validates configuration files
- Tests browser session creation
- Runs integration test

## Configuration

### alice_browser_automation_config.yaml

Main configuration file with settings for:
- Browser behavior (headless mode, session limits, timeouts)
- Qwen model connection (host, model name, timeouts)
- DOM parser settings
- Performance targets
- Security settings
- Logging configuration

### .env

Environment variables for runtime configuration:
- `OLLAMA_HOST` - Ollama API endpoint (default: http://localhost:11434)
- `QWEN_MODEL` - Model name (default: qwen2.5-coder:3b)
- `BROWSER_PROFILES_DIR` - Browser profiles location
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- Feature flags for enabling/disabling capabilities

## Directory Structure

After installation, the following directories are created:

```
~/.alice/
├── browser_profiles/
│   ├── default/
│   │   ├── local_storage/
│   │   ├── session_storage/
│   │   └── extensions/
│   └── README.md
└── logs/
    └── browser_automation.log
```

## Troubleshooting

### Python Version Error

**Error:** "Python 3.10+ required"

**Solution:** Install Python 3.10 or higher from [python.org](https://www.python.org/downloads/)

### Playwright Installation Failed

**Error:** "Failed to install Playwright browsers"

**Solution:**
```bash
python -m playwright install chromium
python -m playwright install-deps chromium  # Linux only
```

### Ollama Not Found

**Error:** "Ollama is not installed"

**Solution:** Follow the Ollama installation instructions for your platform (see Step 3 above)

### Ollama Service Not Running

**Error:** "Ollama service is not accessible"

**Solution:**
```bash
ollama serve
```

Keep this running in a separate terminal.

### Qwen Model Not Found

**Error:** "Qwen 2.5 Coder 3B model not found"

**Solution:**
```bash
ollama pull qwen2.5-coder:3b
```

### Low RAM Warning

**Warning:** "Low RAM detected: XXXMB (8GB recommended)"

**Impact:** The Qwen 3B model may run slowly or fail with insufficient RAM.

**Solution:** Close other applications or upgrade system RAM.

### Low Disk Space Warning

**Warning:** "Low disk space: XGB free (10GB recommended)"

**Impact:** Installation may fail or browser profiles may not save properly.

**Solution:** Free up disk space before continuing.

### Browser Session Test Failed

**Error:** "Browser session test failed"

**Solution:**
1. Ensure Playwright is installed: `python -m playwright install chromium`
2. Check system dependencies (Linux): `python -m playwright install-deps chromium`
3. Try running with headed mode to see errors: Edit config and set `headless_default: false`

### Integration Test Failed

**Error:** "Integration test failed"

**Solution:**
1. Verify all previous checks passed
2. Check logs at `~/.alice/logs/browser_automation.log`
3. Ensure Ollama service is running
4. Restart Ollama service: `killall ollama && ollama serve`

## Verification Checklist

After installation, verify these components:

- [ ] Python 3.10+ installed
- [ ] All Python packages installed
- [ ] Playwright Chromium browser installed
- [ ] Ollama service running
- [ ] Qwen 2.5 Coder 3B model downloaded
- [ ] Configuration files created
- [ ] Directory structure created
- [ ] Browser session test passes
- [ ] Integration test passes

Run `python verify_installation.py` to check all items automatically.

## Next Steps

Once installation is complete:

1. **Review Configuration**
   - Check `alice_browser_automation_config.yaml`
   - Adjust settings for your use case

2. **Configure Environment**
   - Copy `.env.example` to `.env`
   - Set any custom environment variables

3. **Test the System**
   - Run the test suite: `pytest`
   - Try a simple browser automation task

4. **Integrate with Alice**
   - Ensure Alice agent is configured
   - Test voice commands with browser automation

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review logs at `~/.alice/logs/browser_automation.log`
3. Run verification script: `python verify_installation.py`
4. Check the main README.md for usage examples

## Uninstallation

To remove Alice Browser Automation:

1. Remove Python packages:
   ```bash
   pip uninstall -r requirements.txt
   ```

2. Remove Playwright browsers:
   ```bash
   python -m playwright uninstall chromium
   ```

3. Remove Qwen model (optional):
   ```bash
   ollama rm qwen2.5-coder:3b
   ```

4. Remove data directories:
   ```bash
   rm -rf ~/.alice/browser_profiles
   rm -rf ~/.alice/logs
   ```

5. Remove configuration files:
   ```bash
   rm alice_browser_automation_config.yaml
   rm .env
   ```
