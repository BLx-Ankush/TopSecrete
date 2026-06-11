# PLAN ALPHA: ALICE Capability Audit & Restoration Plan

## 1. Current State Summary
The recent "Fluidity Enhancement" upgrade successfully mitigated ALICE's high-latency issues by migrating her core intelligence from a sequential LiveKit pipeline (VAD -> API -> TTS) to the **Gemini Multimodal Live API via WebSocket (`gemini_streaming_client.py`)**. This achieved parallel processing and reduced conversational latency to <300ms.

**However, this architectural shift completely severed ALICE's connection to her OS environment.** She is currently operating strictly as a high-speed conversational voice bot. She cannot "do" anything.

---

## 2. What ALICE is Currently Unable to Do (The Deficits)

Because the new `gemini_streaming_client.py` does not interface with the LiveKit `FunctionContext` tool registry, ALICE has lost access to the following 16 built-in tools defined in `agent.py` and `alice_system_controller.py`:

### A. Operating System & File Management
- **Cannot Open Applications:** (`open_application`, `open_any_app`) She can no longer launch Chrome, Notepad, Spotify, or any local Windows executables.
- **Cannot Search Files:** (`search_files_system`) She cannot locate files on the local hard drive.
- **Cannot Manage Files:** (`create_file_and_open`) She cannot create, read, or edit documents.
- **Cannot Perform OS Commands:** (`advanced_system_operations`) She has lost the ability to control system states (e.g., volume, power, UI settings).

### B. Vision & UI Interaction
- **Blindness:** (`capture_screenshot`) She cannot take screenshots of the user's desktop to analyze visual context.
- **Cannot Click/Type:** The PyAutoGUI/PyWinAuto bindings in `alice_vision.py` are disconnected. If you ask her to click a button on the screen, the LLM will not trigger the automation script.

### C. Browser & Web Automation
- **Cannot Browse the Web:** (`open_browser`) The Playwright/Selenium bindings are inaccessible. She cannot perform live web searches to find updated information.

### D. Hardware & Peripheral Control
- **Lost Hardware Hooks:** (`control_servo_motor`, `get_ultrasonic_distance`) She cannot interact with connected physical peripherals.
- **Lost Display Control:** (`adjust_brightness`) She cannot change monitor brightness via WMI.

### E. Dynamic Extensions
- **Lost MCP Support:** Any Model Context Protocol (MCP) servers (e.g., file system servers) that were dynamically loaded into `mcp_tools` are ignored by the active session.

---

## 3. Technical Root Cause

In `agent.py`, ALICE is instantiated as an `Assistant` which receives `tools_list=all_tools`. 
However, the active streaming connection happens via `self.streaming_client.connect()`. 

Inside `gemini_streaming_client.py`:
1. **No Tool Registration:** The `__init__` method does not accept the `tools_list`. 
2. **No Setup Injection:** The `_send_config()` method sends a `setup` payload to the Gemini API containing `model` and `generation_config`, but completely omits the `tools` array (which should contain `function_declarations`).
3. **No Execution Handler:** The `_receive_loop` and `_handle_message` methods only parse `text` and `inlineData` (audio). They blindly ignore any `functionCall` events sent by the server.

---

## 4. What Needs to be Fixed (The Restoration Plan)

To restore ALICE's full capabilities without sacrificing the new low-latency streaming speeds, we must execute the following precise technical fixes:

### Step 1: Tool Pipeline Injection
- Modify the `GeminiStreamingClient.__init__` signature in `gemini_streaming_client.py` to accept an optional `tools` parameter.
- Update `agent.py` at line 740 to pass `tools=tools_list` into the `GeminiStreamingClient` instantiation.

### Step 2: Schema Translation
- Create a `_build_function_declarations()` helper method inside the client.
- This method must iterate over the provided Python tools, extract their names and docstrings, use `inspect.signature` to map Python types (str, int, bool) to JSON Schema types (STRING, INTEGER, BOOLEAN), and format them into the exact `FunctionDeclaration` schema required by the Gemini Live API.

### Step 3: API Handshake
- Modify `_send_config()` in the streaming client.
- Inject the parsed function declarations into the `config["setup"]` payload under the `"tools"` key before it is transmitted over the WebSocket.
- Update the `"system_instruction"` to explicitly remind the model to utilize the provided tools when fulfilling user requests.

### Step 4: Event Interception & Execution
- Update `_handle_message()` to scan `serverContent.modelTurn.parts` for `"functionCall"` keys.
- Create an asynchronous dispatcher `_execute_tool_and_respond(function_call)` that:
  1. Extracts the requested tool name and arguments.
  2. Matches the name against the local `tools_list`.
  3. Executes the underlying Python coroutine or synchronous function.
  4. Formats the return value (or error traceback) into a `functionResponse`.
  5. Packages it into a `clientContent` WebSocket message with `turnComplete: true` and transmits it back to the Gemini API to resume the conversation.

---
**Status:** ✅ IMPLEMENTED — All 4 fixes applied on 2026-06-06.

### Changes Applied:
| Fix | File | What was done |
|-----|------|---------------|
| #1 Tool Registration | `gemini_streaming_client.py` | Added `tools` param to `__init__`, built `_tool_dispatch` map |
| #2 Schema Translation | `gemini_streaming_client.py` | Added `_build_function_declarations()` — converts Python tools to Gemini JSON schema |
| #3 API Handshake | `gemini_streaming_client.py` | `_send_config()` now injects `tools` + `system_instruction` into WebSocket setup payload |
| #4 Event Handler | `gemini_streaming_client.py` | `_handle_message()` now catches `functionCall` parts and dispatches via `_execute_tool_and_respond()` |
| Wiring | `agent.py` | `GeminiStreamingClient` now receives `tools=tools_list` on instantiation |

### Restored Capabilities:
- ✅ Open any application (`open_application`, `open_any_app`)
- ✅ Search and manage files (`search_files_system`, `create_file_and_open`)
- ✅ OS commands & system control (`advanced_system_operations`, `adjust_brightness`)
- ✅ Screenshots & vision (`capture_screenshot` + `ALICE_VISION_TOOLS`)
- ✅ Browser automation (`open_browser` + Playwright tools)
- ✅ Hardware control (`control_servo_motor`, `get_ultrasonic_distance`)
- ✅ MCP tools (dynamically loaded `mcp_tools` now passed through)
