#!/usr/bin/env python3
"""
Verification script for Task 5.2: Prompt Templates and Few-Shot Examples

This script verifies that:
1. SYSTEM_PROMPT is defined
2. FEW_SHOT_EXAMPLES has 5+ examples
3. PromptBuilder class is implemented
4. JSON schema definitions exist
"""

import sys
import json as json_module
from alice_browser_automation.qwen_client import (
    SYSTEM_PROMPT,
    FEW_SHOT_EXAMPLES,
    ACTION_RESPONSE_SCHEMA,
    TARGET_SELECTOR_SCHEMA,
    PromptBuilder
)


def verify_system_prompt():
    """Verify SYSTEM_PROMPT is defined and contains key elements."""
    print("=" * 70)
    print("1. Verifying SYSTEM_PROMPT")
    print("=" * 70)
    
    assert SYSTEM_PROMPT is not None, "SYSTEM_PROMPT is not defined"
    assert len(SYSTEM_PROMPT) > 100, "SYSTEM_PROMPT is too short"
    assert "browser automation assistant" in SYSTEM_PROMPT.lower(), "Missing role definition"
    assert "JSON" in SYSTEM_PROMPT, "Missing JSON format requirement"
    assert "action_type" in SYSTEM_PROMPT, "Missing action_type field"
    
    print("✅ SYSTEM_PROMPT is properly defined")
    print(f"   Length: {len(SYSTEM_PROMPT)} characters")
    print(f"   Contains: role definition, JSON schema, rules")
    print()


def verify_few_shot_examples():
    """Verify FEW_SHOT_EXAMPLES has 5+ examples covering key actions."""
    print("=" * 70)
    print("2. Verifying FEW_SHOT_EXAMPLES")
    print("=" * 70)
    
    assert FEW_SHOT_EXAMPLES is not None, "FEW_SHOT_EXAMPLES is not defined"
    assert isinstance(FEW_SHOT_EXAMPLES, list), "FEW_SHOT_EXAMPLES must be a list"
    assert len(FEW_SHOT_EXAMPLES) >= 5, f"Need at least 5 examples, got {len(FEW_SHOT_EXAMPLES)}"
    
    # Check structure of examples
    action_types = set()
    for i, example in enumerate(FEW_SHOT_EXAMPLES):
        assert "user" in example, f"Example {i} missing 'user' key"
        assert "assistant" in example, f"Example {i} missing 'assistant' key"
        
        # Parse assistant response to check structure
        try:
            response = json_module.loads(example["assistant"])
            assert "action_type" in response, f"Example {i} missing action_type"
            action_types.add(response["action_type"])
        except json_module.JSONDecodeError:
            raise AssertionError(f"Example {i} has invalid JSON in assistant response")
    
    print(f"✅ FEW_SHOT_EXAMPLES has {len(FEW_SHOT_EXAMPLES)} examples")
    print(f"   Action types covered: {', '.join(sorted(action_types))}")
    
    # Display examples
    for i, example in enumerate(FEW_SHOT_EXAMPLES, 1):
        response = json_module.loads(example["assistant"])
        print(f"   {i}. {response['action_type']}: {example['user'][:50]}...")
    print()


def verify_json_schemas():
    """Verify JSON schema definitions exist and are valid."""
    print("=" * 70)
    print("3. Verifying JSON Schema Definitions")
    print("=" * 70)
    
    # Check ACTION_RESPONSE_SCHEMA
    assert ACTION_RESPONSE_SCHEMA is not None, "ACTION_RESPONSE_SCHEMA is not defined"
    assert isinstance(ACTION_RESPONSE_SCHEMA, dict), "ACTION_RESPONSE_SCHEMA must be a dict"
    assert "type" in ACTION_RESPONSE_SCHEMA, "Schema missing 'type' field"
    assert "properties" in ACTION_RESPONSE_SCHEMA, "Schema missing 'properties' field"
    assert "required" in ACTION_RESPONSE_SCHEMA, "Schema missing 'required' field"
    
    # Check required fields
    required_fields = ACTION_RESPONSE_SCHEMA["required"]
    assert "action_type" in required_fields, "action_type not in required fields"
    assert "expected_result" in required_fields, "expected_result not in required fields"
    
    # Check properties
    properties = ACTION_RESPONSE_SCHEMA["properties"]
    assert "action_type" in properties, "action_type not in properties"
    assert "target_selector" in properties, "target_selector not in properties"
    assert "parameters" in properties, "parameters not in properties"
    assert "expected_result" in properties, "expected_result not in properties"
    
    print("✅ ACTION_RESPONSE_SCHEMA is properly defined")
    print(f"   Required fields: {', '.join(required_fields)}")
    print(f"   Properties: {', '.join(properties.keys())}")
    
    # Check TARGET_SELECTOR_SCHEMA
    assert TARGET_SELECTOR_SCHEMA is not None, "TARGET_SELECTOR_SCHEMA is not defined"
    assert isinstance(TARGET_SELECTOR_SCHEMA, dict), "TARGET_SELECTOR_SCHEMA must be a dict"
    
    print("✅ TARGET_SELECTOR_SCHEMA is properly defined")
    print(f"   Properties: {', '.join(TARGET_SELECTOR_SCHEMA['properties'].keys())}")
    print()


def verify_prompt_builder():
    """Verify PromptBuilder class is implemented with required methods."""
    print("=" * 70)
    print("4. Verifying PromptBuilder Class")
    print("=" * 70)
    
    # Check class exists
    assert PromptBuilder is not None, "PromptBuilder class is not defined"
    
    # Check methods exist
    required_methods = [
        '__init__',
        'build_messages',
        'build_action_prompt',
        'build_correction_prompt',
        'add_example',
        'clear_examples',
        'get_example_count'
    ]
    
    for method in required_methods:
        assert hasattr(PromptBuilder, method), f"PromptBuilder missing method: {method}"
    
    print("✅ PromptBuilder class is properly defined")
    print(f"   Methods: {', '.join(required_methods)}")
    
    # Test instantiation
    builder = PromptBuilder()
    assert builder is not None, "Failed to instantiate PromptBuilder"
    assert builder.system_prompt == SYSTEM_PROMPT, "System prompt not set correctly"
    assert len(builder.few_shot_examples) >= 5, "Few-shot examples not set correctly"
    
    print("✅ PromptBuilder can be instantiated")
    print(f"   Example count: {builder.get_example_count()}")
    print()


def test_prompt_builder_functionality():
    """Test PromptBuilder methods work correctly."""
    print("=" * 70)
    print("5. Testing PromptBuilder Functionality")
    print("=" * 70)
    
    builder = PromptBuilder()
    
    # Test build_messages
    messages = builder.build_messages("Click the button")
    assert isinstance(messages, list), "build_messages should return a list"
    assert len(messages) > 0, "build_messages should return non-empty list"
    assert messages[0]["role"] == "system", "First message should be system prompt"
    assert messages[-1]["role"] == "user", "Last message should be user prompt"
    
    print("✅ build_messages() works correctly")
    print(f"   Generated {len(messages)} messages")
    
    # Test build_action_prompt
    action_prompt = builder.build_action_prompt(
        task_description="Login to website",
        dom_snippet="<button>Login</button>",
        previous_actions=["navigate to page"]
    )
    assert isinstance(action_prompt, str), "build_action_prompt should return string"
    assert "Login to website" in action_prompt, "Task description not in prompt"
    assert "<button>Login</button>" in action_prompt, "DOM snippet not in prompt"
    assert "navigate to page" in action_prompt, "Previous actions not in prompt"
    
    print("✅ build_action_prompt() works correctly")
    print(f"   Prompt length: {len(action_prompt)} characters")
    
    # Test build_correction_prompt
    correction_prompt = builder.build_correction_prompt(
        original_prompt="Click button",
        invalid_response='{"action": "click"}',
        error_message="Missing required fields"
    )
    assert isinstance(correction_prompt, str), "build_correction_prompt should return string"
    assert "invalid" in correction_prompt.lower(), "Should mention invalid response"
    assert "Missing required fields" in correction_prompt, "Error message not in prompt"
    
    print("✅ build_correction_prompt() works correctly")
    print(f"   Prompt length: {len(correction_prompt)} characters")
    
    # Test add_example
    initial_count = builder.get_example_count()
    builder.add_example("Test user message", "Test assistant message")
    assert builder.get_example_count() == initial_count + 1, "add_example didn't increase count"
    
    print("✅ add_example() works correctly")
    print(f"   Example count increased from {initial_count} to {builder.get_example_count()}")
    
    # Test clear_examples
    builder.clear_examples()
    assert builder.get_example_count() == 0, "clear_examples didn't clear all examples"
    
    print("✅ clear_examples() works correctly")
    print(f"   Example count: {builder.get_example_count()}")
    print()


def main():
    """Run all verification tests."""
    print("\n" + "=" * 70)
    print("TASK 5.2 VERIFICATION: Prompt Templates and Few-Shot Examples")
    print("=" * 70)
    print()
    
    try:
        verify_system_prompt()
        verify_few_shot_examples()
        verify_json_schemas()
        verify_prompt_builder()
        test_prompt_builder_functionality()
        
        print("=" * 70)
        print("✅ ALL VERIFICATIONS PASSED")
        print("=" * 70)
        print()
        print("Task 5.2 is complete and all components are working correctly:")
        print("  ✅ SYSTEM_PROMPT defined")
        print("  ✅ FEW_SHOT_EXAMPLES with 6 examples")
        print("  ✅ PromptBuilder class implemented")
        print("  ✅ JSON schema definitions added")
        print()
        return 0
        
    except AssertionError as e:
        print()
        print("=" * 70)
        print("❌ VERIFICATION FAILED")
        print("=" * 70)
        print(f"Error: {e}")
        print()
        return 1
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ UNEXPECTED ERROR")
        print("=" * 70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
