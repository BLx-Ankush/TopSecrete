# Alice Agent Startup Errors - Fixed

## Issues Fixed

### 1. AttributeError: 'AgentSession' object has no attribute 'wait_for_completion'

**Problem**: The code was calling `await session.wait_for_completion()` on line 221, but the `AgentSession` class doesn't have this method in the current version of the LiveKit agents SDK.

**Solution**: Removed the `wait_for_completion()` call. The session will run until the room is closed or an error occurs, which is the expected behavior for LiveKit agent sessions.

**Location**: `ALICE/Alice_code/agent.py`, line 221

### 2. UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'

**Problem**: Windows console (using cp1252 encoding) cannot display Unicode characters like checkmarks (✓) that the logging system was trying to print. This caused repeated logging errors throughout the application.

**Solution**: Added UTF-8 encoding configuration at the start of the script:
- Reconfigured stdout and stderr to use UTF-8 encoding
- Set `PYTHONIOENCODING` environment variable to 'utf-8'
- Applied only on Windows platform (`sys.platform == "win32"`)

**Location**: `ALICE/Alice_code/agent.py`, lines 8-16

### 3. UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f

**Problem**: Subprocess calls throughout the codebase were not specifying encoding, causing Windows to use the default cp1252 encoding which cannot decode certain bytes from command output.

**Solution**: Added `encoding='utf-8'` and `errors='ignore'` parameters to all subprocess calls that capture output:
- `subprocess.run()` calls with `capture_output=True` or `text=True`
- `subprocess.Popen()` calls with `stdout=subprocess.PIPE`

**Locations Fixed**:
- `ALICE/Alice_code/alice_personal_safe.py` - PowerShell WhatsApp check
- `ALICE/Alice_code/alice_browser_automation/install.py` - Multiple subprocess calls:
  - System memory detection (wmic, sysctl)
  - pip install commands
  - playwright install commands
  - ollama pull command
- `ALICE/Alice_code/alice_browser_automation/setup.py` - Script execution

## Changes Made

```python
# At the top of agent.py (after imports)
if sys.platform == "win32":
    # Set UTF-8 encoding for stdout/stderr to handle Unicode characters
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    # Set environment variable for Python to use UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
```

```python
# In entrypoint function (around line 221)
# Removed: await session.wait_for_completion()
# Added comment explaining the behavior
# The session will run until the room is closed or an error occurs
```

```python
# For all subprocess calls with text output
subprocess.run(
    [...],
    capture_output=True,
    text=True,
    encoding='utf-8',  # Added
    errors='ignore'    # Added
)

subprocess.Popen(
    [...],
    stdout=subprocess.PIPE,
    text=True,
    encoding='utf-8',  # Added
    errors='ignore'    # Added
)
```

## Testing

After these fixes:
1. The agent should start without the AttributeError
2. Unicode characters in logs should display correctly on Windows
3. The session will run normally and respond to room events
4. Subprocess calls will handle non-UTF-8 output gracefully without crashing

## Notes

- The `wait_for_completion()` method may have been from an older version of the LiveKit SDK or was incorrectly assumed to exist
- The Unicode encoding fixes are Windows-specific but won't affect Linux/Mac systems
- The session lifecycle is now properly managed by the LiveKit framework
- The `errors='ignore'` parameter ensures that any non-decodable bytes are skipped rather than causing crashes
