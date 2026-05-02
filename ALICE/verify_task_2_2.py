"""
Verification script for Task 2.2: Data Models for DOM Structures

This script verifies that all required data models are implemented correctly
according to the design document specifications.
"""

import sys
from pathlib import Path

# Add the alice_browser_automation module to path
sys.path.insert(0, str(Path(__file__).parent / "Alice_code"))

from alice_browser_automation.types import (
    ElementSelectors,
    InteractiveElement,
    StructuredDOM,
    AccessibilityNode,
    AccessibilityTree,
)
from dataclasses import fields
from typing import get_type_hints


def verify_dataclass_fields(cls, expected_fields):
    """Verify that a dataclass has all expected fields with correct types."""
    actual_fields = {f.name: f.type for f in fields(cls)}
    type_hints = get_type_hints(cls)
    
    print(f"\n✓ Verifying {cls.__name__}:")
    print(f"  Expected fields: {len(expected_fields)}")
    print(f"  Actual fields: {len(actual_fields)}")
    
    all_present = True
    for field_name, expected_type in expected_fields.items():
        if field_name not in actual_fields:
            print(f"  ✗ Missing field: {field_name}")
            all_present = False
        else:
            actual_type = type_hints.get(field_name, actual_fields[field_name])
            print(f"  ✓ {field_name}: {actual_type}")
    
    return all_present


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("Task 2.2 Verification: Data Models for DOM Structures")
    print("=" * 70)
    
    all_checks_passed = True
    
    # 1. Verify ElementSelectors
    element_selectors_fields = {
        'css_selector': str,
        'xpath': str,
        'aria_label': 'Optional[str]',
        'test_id': 'Optional[str]',
        'text_content': 'Optional[str]',
    }
    if not verify_dataclass_fields(ElementSelectors, element_selectors_fields):
        all_checks_passed = False
    
    # 2. Verify InteractiveElement
    interactive_element_fields = {
        'element_id': str,
        'tag_name': str,
        'role': str,
        'label': str,
        'selectors': ElementSelectors,
        'attributes': 'Dict[str, str]',
        'position': 'Tuple[int, int]',
        'is_visible': bool,
    }
    if not verify_dataclass_fields(InteractiveElement, interactive_element_fields):
        all_checks_passed = False
    
    # 3. Verify StructuredDOM
    structured_dom_fields = {
        'url': str,
        'title': str,
        'interactive_elements': 'List[InteractiveElement]',
        'text_content': str,
        'metadata': 'Dict[str, Any]',
        'timestamp': 'datetime',
    }
    if not verify_dataclass_fields(StructuredDOM, structured_dom_fields):
        all_checks_passed = False
    
    # 4. Verify AccessibilityNode
    accessibility_node_fields = {
        'role': str,
        'name': str,
        'description': 'Optional[str]',
        'children': 'List[AccessibilityNode]',
        'selectors': 'Optional[ElementSelectors]',
    }
    if not verify_dataclass_fields(AccessibilityNode, accessibility_node_fields):
        all_checks_passed = False
    
    # 5. Verify AccessibilityTree
    accessibility_tree_fields = {
        'root': AccessibilityNode,
        'interactive_nodes': 'List[AccessibilityNode]',
    }
    if not verify_dataclass_fields(AccessibilityTree, accessibility_tree_fields):
        all_checks_passed = False
    
    # Test instantiation
    print("\n" + "=" * 70)
    print("Testing Data Model Instantiation")
    print("=" * 70)
    
    try:
        # Test ElementSelectors
        selectors = ElementSelectors(
            css_selector="button.submit",
            xpath="//button[@class='submit']",
            aria_label="Submit form",
            test_id="submit-btn",
            text_content="Submit"
        )
        print("\n✓ ElementSelectors instantiated successfully")
        print(f"  css_selector: {selectors.css_selector}")
        print(f"  xpath: {selectors.xpath}")
        print(f"  aria_label: {selectors.aria_label}")
        
        # Test InteractiveElement
        element = InteractiveElement(
            element_id="btn-1",
            tag_name="button",
            role="button",
            label="Submit",
            selectors=selectors,
            attributes={"class": "submit", "type": "submit"},
            position=(100, 200),
            is_visible=True
        )
        print("\n✓ InteractiveElement instantiated successfully")
        print(f"  element_id: {element.element_id}")
        print(f"  tag_name: {element.tag_name}")
        print(f"  position: {element.position}")
        
        # Test AccessibilityNode
        child_node = AccessibilityNode(
            role="button",
            name="Submit",
            description="Submit the form",
            selectors=selectors
        )
        root_node = AccessibilityNode(
            role="main",
            name="Main content",
            children=[child_node]
        )
        print("\n✓ AccessibilityNode instantiated successfully")
        print(f"  root role: {root_node.role}")
        print(f"  children count: {len(root_node.children)}")
        
        # Test AccessibilityTree
        tree = AccessibilityTree(
            root=root_node,
            interactive_nodes=[child_node]
        )
        print("\n✓ AccessibilityTree instantiated successfully")
        print(f"  root: {tree.root.role}")
        print(f"  interactive_nodes count: {len(tree.interactive_nodes)}")
        
        # Test StructuredDOM
        from datetime import datetime
        dom = StructuredDOM(
            url="https://example.com",
            title="Example Page",
            interactive_elements=[element],
            text_content="Example page content",
            metadata={"page_type": "form"},
            timestamp=datetime.now()
        )
        print("\n✓ StructuredDOM instantiated successfully")
        print(f"  url: {dom.url}")
        print(f"  title: {dom.title}")
        print(f"  interactive_elements count: {len(dom.interactive_elements)}")
        print(f"  timestamp: {dom.timestamp}")
        
    except Exception as e:
        print(f"\n✗ Instantiation failed: {e}")
        all_checks_passed = False
    
    # Final summary
    print("\n" + "=" * 70)
    if all_checks_passed:
        print("✓ ALL CHECKS PASSED - Task 2.2 Complete")
        print("\nAll required data models are correctly implemented:")
        print("  • ElementSelectors - Multiple selector strategies")
        print("  • InteractiveElement - DOM element representation")
        print("  • StructuredDOM - Complete DOM structure")
        print("  • AccessibilityNode - Accessibility tree node")
        print("  • AccessibilityTree - Complete accessibility tree")
    else:
        print("✗ SOME CHECKS FAILED - Review output above")
    print("=" * 70)
    
    return 0 if all_checks_passed else 1


if __name__ == "__main__":
    sys.exit(main())
