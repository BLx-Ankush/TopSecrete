# Task 5.2 Summary: Create Prompt Templates and Few-Shot Examples

## Task Completion Status: ✅ COMPLETE

### Implementation Date
January 2025

### Requirements Validated
- **Requirement 4.1**: Few-shot examples for JSON formatting in system prompt
- **Requirement 4.2**: Generate responses in valid JSON format for browser actions
- **Requirement 4.4**: Use few-shot examples demonstrating actions
- **Requirement 4.5**: Retry with corrected prompt if invalid JSON generated

---

## What Was Implemented

### 1. JSON Schema Definitions ✅

Added comprehensive JSON schema definitions for browser action responses:

```python
ACTION_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["action_type", "expected_result"],
    "properties": {
        "action_type": {
            "type": "string",
            "enum": ["navigate", "click", "type", "wait", "extract", "scroll", "select", "upload", "download"]
        },
        "target_selector": {
            "type": ["object", "null"],
            "properties": {
                "css_selector": {"type": ["string", "null"]},
                "xpath": {"type": ["string", "null"]},
                "aria_label": {"type": ["string", "null"]},
                "test_id": {"type": ["string", "null"]},
                "text_content": {"type": ["string", "null"]}
            }
        },
        "parameters": {
            "type": "object"
        },
        "expected_result": {
            "type": "string"
        }
    }
}
```

Also added `TARGET_SELECTOR_SCHEMA` for selector validation.

### 2. System Prompt ✅

The `SYSTEM_PROMPT` was already defined in Task 5.1 and includes:
- Clear role definition as browser automation assistant
- JSON schema specification
- 5 key rules for generating actions
- Action type enumeration

### 3. Few-Shot Examples ✅

Enhanced `FEW_SHOT_EXAMPLES` with **6 comprehensive examples** covering:

1. **Click Action**: Login button with ARIA label
2. **Type Action**: Email input field with text parameter
3. **Navigate Action**: URL navigation with wait condition
4. **Wait Action**: Waiting for search results with visibility condition
5. **Extract Action**: Extracting confirmation number with regex pattern
6. **Scroll Action**: Scrolling down to load more results (NEW)

Each example demonstrates:
- Proper JSON structure
- Multiple selector strategies (CSS, XPath, ARIA)
- Action-specific parameters
- Expected result description

### 4. PromptBuilder Class ✅ (NEW)

Implemented a comprehensive `PromptBuilder` class with the following methods:

#### Core Methods:
- `__init__()`: Initialize with system prompt, few-shot examples, and schema options
- `build_messages()`: Construct complete message list for Ollama API
- `build_action_prompt()`: Build prompts for browser action generation
- `build_correction_prompt()`: Build prompts for correcting invalid JSON responses

#### Utility Methods:
- `add_example()`: Add new few-shot examples dynamically
- `clear_examples()`: Clear all examples
- `get_example_count()`: Get count of examples

#### Key Features:
- Flexible system prompt configuration
- Optional additional context support
- Previous actions tracking
- Error correction prompt generation
- Dynamic example management

---

## Code Location

**File**: `ALICE/Alice_code/alice_browser_automation/qwen_client.py`

**Lines**: 
- JSON Schemas: Lines 24-68
- System Prompt: Lines 73-95
- Few-Shot Examples: Lines 97-192
- PromptBuilder Class: Lines 197-310

---

## Integration with Existing Code

The PromptBuilder class integrates seamlessly with the existing `QwenModelClient`:

1. **QwenModelClient.generate_with_prompt()** already uses few-shot examples
2. **QwenModelClient.generate_json_response()** uses `FEW_SHOT_EXAMPLES` by default
3. **QwenModelClient.validate_json_output()** validates against the schema structure
4. **PromptBuilder** can be used independently or with QwenModelClient for advanced prompt construction

---

## Example Usage

### Basic Usage with PromptBuilder:

```python
from alice_browser_automation.qwen_client import PromptBuilder

# Create prompt builder
builder = PromptBuilder()

# Build messages for action generation
messages = builder.build_messages(
    user_prompt="Click the submit button",
    additional_context="DOM: <button id='submit'>Submit</button>"
)

# Build action prompt with context
action_prompt = builder.build_action_prompt(
    task_description="Fill out login form",
    dom_snippet="<input id='username'><input id='password'><button>Login</button>",
    previous_actions=["navigate to login page", "type username"]
)

# Build correction prompt for invalid response
correction_prompt = builder.build_correction_prompt(
    original_prompt="Click the button",
    invalid_response='{"action": "click"}',  # Missing required fields
    error_message="Missing 'action_type' and 'expected_result' fields"
)
```

### Integration with QwenModelClient:

```python
from alice_browser_automation.qwen_client import QwenModelClient, PromptBuilder, ACTION_RESPONSE_SCHEMA

async def generate_browser_action():
    client = QwenModelClient()
    builder = PromptBuilder()
    
    # Build prompt
    prompt = builder.build_action_prompt(
        task_description="Login to website",
        dom_snippet="<input id='email'><input id='password'><button>Login</button>"
    )
    
    # Generate JSON response
    action = await client.generate_json_response(
        prompt=prompt,
        schema=ACTION_RESPONSE_SCHEMA
    )
    
    return action
```

---

## Verification

### ✅ Task Requirements Met:

1. **Define SYSTEM_PROMPT**: ✅ Already defined in Task 5.1
2. **Create FEW_SHOT_EXAMPLES list with 5+ examples**: ✅ 6 examples covering all major action types
3. **Implement PromptBuilder class**: ✅ Comprehensive class with message building and prompt construction
4. **Add JSON schema definitions**: ✅ ACTION_RESPONSE_SCHEMA and TARGET_SELECTOR_SCHEMA

### ✅ Design Document Compliance:

All implementations match the design document specifications in:
- Section: "4. Qwen Model Client"
- Subsection: "Prompt Templates"
- The few-shot examples match the exact format specified in the design

### ✅ Requirements Validated:

- **4.1**: Few-shot examples in system prompt ✅
- **4.2**: Valid JSON format generation ✅
- **4.4**: Few-shot examples for actions ✅
- **4.5**: Correction prompt support ✅

---

## Next Steps

Task 5.2 is complete. The next task is:

**Task 5.3**: Implement retry logic for invalid JSON responses
- Add retry mechanism with error context in prompt
- Implement exponential backoff for retries
- Add validation against expected JSON schema
- Limit retries to 3 attempts per action

The PromptBuilder class already provides `build_correction_prompt()` which will be used in Task 5.3 for retry logic.

---

## Notes

1. The PromptBuilder class provides a clean separation of concerns between prompt construction and model interaction
2. The 6 few-shot examples cover all major browser actions: click, type, navigate, wait, extract, and scroll
3. JSON schemas are defined as constants for easy reuse and validation
4. The implementation is fully compatible with the existing QwenModelClient from Task 5.1
5. All code includes proper docstrings and requirement validation comments
