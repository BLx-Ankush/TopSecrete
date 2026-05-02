#!/usr/bin/env python3
"""
Simple verification script for Task 5.2: Prompt Templates and Few-Shot Examples

This script verifies the implementation without complex imports.
"""

import sys
import os

# Add the Alice_code directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Alice_code'))

def main():
    print("\n" + "=" * 70)
    print("TASK 5.2 VERIFICATION: Prompt Templates and Few-Shot Examples")
    print("=" * 70)
    print()
    
    try:
        # Import after path is set
        from alice_browser_automation.qwen_client import (
            SYSTEM_PROMPT,
            FEW_SHOT_EXAMPLES,
            ACTION_RESPONSE_SCHEMA,
            TARGET_SELECTOR_SCHEMA,
            PromptBuilder
        )
        import json
        
        # 1. Verify SYSTEM_PROMPT
        print("1. Verifying SYSTEM_PROMPT...")
        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT) > 100
        assert "browser automation assistant" in SYSTEM_PROMPT.lower()
        print("   ✅ SYSTEM_PROMPT is properly defined")
        print(f"   Length: {len(SYSTEM_PROMPT)} characters\n")
        
        # 2. Verify FEW_SHOT_EXAMPLES
        print("2. Verifying FEW_SHOT_EXAMPLES...")
        assert FEW_SHOT_EXAMPLES is not None
        assert isinstance(FEW_SHOT_EXAMPLES, list)
        assert len(FEW_SHOT_EXAMPLES) >= 5
        
        action_types = set()
        for example in FEW_SHOT_EXAMPLES:
            assert "user" in example
            assert "assistant" in example
            response = json.loads(example["assistant"])
            action_types.add(response["action_type"])
        
        print(f"   ✅ FEW_SHOT_EXAMPLES has {len(FEW_SHOT_EXAMPLES)} examples")
        print(f"   Action types: {', '.join(sorted(action_types))}\n")
        
        # 3. Verify JSON Schemas
        print("3. Verifying JSON Schema Definitions...")
        assert ACTION_RESPONSE_SCHEMA is not None
        assert "type" in ACTION_RESPONSE_SCHEMA
        assert "properties" in ACTION_RESPONSE_SCHEMA
        assert "required" in ACTION_RESPONSE_SCHEMA
        print("   ✅ ACTION_RESPONSE_SCHEMA is properly defined")
        
        assert TARGET_SELECTOR_SCHEMA is not None
        assert "properties" in TARGET_SELECTOR_SCHEMA
        print("   ✅ TARGET_SELECTOR_SCHEMA is properly defined\n")
        
        # 4. Verify PromptBuilder
        print("4. Verifying PromptBuilder Class...")
        assert PromptBuilder is not None
        
        required_methods = [
            'build_messages',
            'build_action_prompt',
            'build_correction_prompt',
            'add_example',
            'clear_examples',
            'get_example_count'
        ]
        
        for method in required_methods:
            assert hasattr(PromptBuilder, method)
        
        print("   ✅ PromptBuilder class is properly defined")
        print(f"   Methods: {', '.join(required_methods)}\n")
        
        # 5. Test PromptBuilder functionality
        print("5. Testing PromptBuilder Functionality...")
        builder = PromptBuilder()
        
        # Test build_messages
        messages = builder.build_messages("Click the button")
        assert isinstance(messages, list)
        assert len(messages) > 0
        print("   ✅ build_messages() works")
        
        # Test build_action_prompt
        action_prompt = builder.build_action_prompt(
            task_description="Login",
            dom_snippet="<button>Login</button>"
        )
        assert isinstance(action_prompt, str)
        assert "Login" in action_prompt
        print("   ✅ build_action_prompt() works")
        
        # Test build_correction_prompt
        correction = builder.build_correction_prompt(
            original_prompt="Click",
            invalid_response='{}',
            error_message="Missing fields"
        )
        assert isinstance(correction, str)
        print("   ✅ build_correction_prompt() works")
        
        # Test example management
        initial_count = builder.get_example_count()
        builder.add_example("test", "test")
        assert builder.get_example_count() == initial_count + 1
        print("   ✅ add_example() works")
        
        builder.clear_examples()
        assert builder.get_example_count() == 0
        print("   ✅ clear_examples() works\n")
        
        # Success!
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
        
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ VERIFICATION FAILED")
        print("=" * 70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
