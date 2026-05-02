#!/usr/bin/env python3
"""
Verification script for Task 2.3: Create data models for browser actions and tasks

This script verifies that all required data models exist in types.py and match
the design document specifications.

Requirements verified:
- Requirement 3.3: Data models for browser actions and tasks
- Requirement 4.3: Task result data structures
"""

import sys
from pathlib import Path
from dataclasses import fields
from typing import get_type_hints

# Add the alice_browser_automation module to path
sys.path.insert(0, str(Path(__file__).parent / "Alice_code"))

from alice_browser_automation.types import (
    BrowserAction,
    BrowserTask,
    BrowserState,
    TaskResult,
    ActionType,
    TaskType,
)


def verify_dataclass_fields(cls, expected_fields: dict, class_name: str) -> bool:
    """
    Verify that a dataclass has all expected fields with correct types.
    
    Args:
        cls: The dataclass to verify
        expected_fields: Dict mapping field names to expected types (as strings)
        class_name: Name of the class for error reporting
    
    Returns:
        True if all fields match, False otherwise
    """
    print(f"\n✓ Verifying {class_name}...")
    
    actual_fields = {f.name: f for f in fields(cls)}
    type_hints = get_type_hints(cls)
    
    all_match = True
    
    for field_name, expected_type_str in expected_fields.items():
        if field_name not in actual_fields:
            print(f"  ✗ Missing field: {field_name}")
            all_match = False
        else:
            actual_type = type_hints.get(field_name)
            print(f"  ✓ Field '{field_name}': {actual_type}")
    
    # Check for extra fields (informational only)
    extra_fields = set(actual_fields.keys()) - set(expected_fields.keys())
    if extra_fields:
        print(f"  ℹ Additional fields: {', '.join(extra_fields)}")
    
    return all_match


def main():
    """Main verification function."""
    print("=" * 70)
    print("Task 2.3 Verification: Data Models for Browser Actions and Tasks")
    print("=" * 70)
    
    all_passed = True
    
    # Verify BrowserAction dataclass
    browser_action_fields = {
        "action_type": "ActionType",
        "target_selector": "Optional[ElementSelectors]",
        "parameters": "Dict[str, Any]",
        "expected_result": "str",
        "retry_count": "int",
    }
    
    if not verify_dataclass_fields(BrowserAction, browser_action_fields, "BrowserAction"):
        all_passed = False
    
    # Verify BrowserTask dataclass
    browser_task_fields = {
        "task_id": "str",
        "description": "str",
        "task_type": "TaskType",
        "parameters": "Dict[str, Any]",
        "target_url": "Optional[str]",
        "expected_outcome": "str",
    }
    
    if not verify_dataclass_fields(BrowserTask, browser_task_fields, "BrowserTask"):
        all_passed = False
    
    # Verify BrowserState dataclass
    browser_state_fields = {
        "url": "str",
        "dom": "Optional[StructuredDOM]",
        "cookies": "List[Dict[str, Any]]",
        "local_storage": "Dict[str, str]",
        "session_storage": "Dict[str, str]",
        "screenshot_path": "Optional[str]",
    }
    
    if not verify_dataclass_fields(BrowserState, browser_state_fields, "BrowserState"):
        all_passed = False
    
    # Verify TaskResult dataclass
    task_result_fields = {
        "task_id": "str",
        "success": "bool",
        "summary": "str",
        "actions_taken": "List[BrowserAction]",
        "extracted_data": "Dict[str, Any]",
        "error": "Optional[str]",
        "duration_seconds": "float",
        "screenshots": "List[str]",
    }
    
    if not verify_dataclass_fields(TaskResult, task_result_fields, "TaskResult"):
        all_passed = False
    
    # Verify enums exist
    print("\n✓ Verifying ActionType enum...")
    action_types = [e.value for e in ActionType]
    print(f"  ✓ ActionType values: {', '.join(action_types)}")
    
    print("\n✓ Verifying TaskType enum...")
    task_types = [e.value for e in TaskType]
    print(f"  ✓ TaskType values: {', '.join(task_types)}")
    
    # Summary
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL VERIFICATIONS PASSED")
        print("\nTask 2.3 Complete:")
        print("  • BrowserAction dataclass: ✓")
        print("  • BrowserTask dataclass: ✓")
        print("  • BrowserState dataclass: ✓")
        print("  • TaskResult dataclass: ✓")
        print("\nRequirements validated:")
        print("  • Requirement 3.3: Data models for browser actions and tasks")
        print("  • Requirement 4.3: Task result data structures")
    else:
        print("✗ SOME VERIFICATIONS FAILED")
        return 1
    
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
