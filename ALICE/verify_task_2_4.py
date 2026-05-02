#!/usr/bin/env python3
"""
Verification script for Task 2.4: Data Models for Sessions and Configurations

This script verifies that the data models in types.py match the design document
specifications for BrowserSession, RetryConfig, and AppConfig.

Requirements validated: 7.1, 7.2, 8.1, 8.2
"""

import sys
from pathlib import Path
from dataclasses import fields
from datetime import datetime

# Add the alice_browser_automation module to the path
sys.path.insert(0, str(Path(__file__).parent / "Alice_code"))

from alice_browser_automation.types import (
    BrowserSession,
    RetryConfig,
    AppConfig,
    SessionState,
    ElementSelectors
)


def verify_browser_session():
    """
    Verify BrowserSession dataclass matches design specifications.
    
    Requirements: 8.1, 8.2
    Design spec: session_id, profile_name, domain, playwright_context, 
                 playwright_page, created_at, last_activity, is_headless, state
    """
    print("=" * 70)
    print("Verifying BrowserSession dataclass")
    print("=" * 70)
    
    required_fields = {
        'session_id': str,
        'profile_name': str,
        'domain': str,
        'playwright_context': type(None),  # Any type
        'playwright_page': type(None),  # Any type
        'created_at': datetime,
        'last_activity': datetime,
        'is_headless': bool,
        'state': SessionState
    }
    
    actual_fields = {f.name: f.type for f in fields(BrowserSession)}
    
    print(f"\nRequired fields: {len(required_fields)}")
    print(f"Actual fields: {len(actual_fields)}")
    
    all_present = True
    for field_name, expected_type in required_fields.items():
        if field_name in actual_fields:
            print(f"  ✓ {field_name}: {actual_fields[field_name]}")
        else:
            print(f"  ✗ MISSING: {field_name}")
            all_present = False
    
    # Check for extra fields
    extra_fields = set(actual_fields.keys()) - set(required_fields.keys())
    if extra_fields:
        print(f"\nExtra fields (not in spec): {extra_fields}")
    
    if all_present:
        print("\n✓ BrowserSession: All required fields present")
        return True
    else:
        print("\n✗ BrowserSession: Missing required fields")
        return False


def verify_retry_config():
    """
    Verify RetryConfig dataclass matches design specifications.
    
    Requirements: 8.1, 8.2
    Design spec: max_retries, retry_delay_seconds, exponential_backoff, 
                 backoff_multiplier, error-specific retry limits
    """
    print("\n" + "=" * 70)
    print("Verifying RetryConfig dataclass")
    print("=" * 70)
    
    required_fields = {
        'max_retries': int,
        'retry_delay_seconds': float,
        'exponential_backoff': bool,
        'backoff_multiplier': float,
        # Error-specific retry limits
        'element_not_found_retries': int,
        'page_load_retries': int,
        'invalid_action_retries': int,
        'network_error_retries': int
    }
    
    actual_fields = {f.name: f.type for f in fields(RetryConfig)}
    
    print(f"\nRequired fields: {len(required_fields)}")
    print(f"Actual fields: {len(actual_fields)}")
    
    all_present = True
    for field_name, expected_type in required_fields.items():
        if field_name in actual_fields:
            print(f"  ✓ {field_name}: {actual_fields[field_name]}")
        else:
            print(f"  ✗ MISSING: {field_name}")
            all_present = False
    
    # Check default values
    print("\nDefault values:")
    config = RetryConfig()
    print(f"  max_retries: {config.max_retries} (expected: 2)")
    print(f"  retry_delay_seconds: {config.retry_delay_seconds} (expected: 1.0)")
    print(f"  exponential_backoff: {config.exponential_backoff} (expected: True)")
    print(f"  backoff_multiplier: {config.backoff_multiplier} (expected: 2.0)")
    print(f"  element_not_found_retries: {config.element_not_found_retries} (expected: 3)")
    print(f"  page_load_retries: {config.page_load_retries} (expected: 2)")
    print(f"  invalid_action_retries: {config.invalid_action_retries} (expected: 3)")
    print(f"  network_error_retries: {config.network_error_retries} (expected: 2)")
    
    if all_present:
        print("\n✓ RetryConfig: All required fields present")
        return True
    else:
        print("\n✗ RetryConfig: Missing required fields")
        return False


def verify_app_config():
    """
    Verify AppConfig dataclass matches design specifications.
    
    Requirements: 7.1, 7.2
    Design spec: app_name, url, login_url, login_selectors, 
                 authenticated_indicator, navigation_map, profile_name
    """
    print("\n" + "=" * 70)
    print("Verifying AppConfig dataclass")
    print("=" * 70)
    
    required_fields = {
        'app_name': str,
        'url': str,
        'login_url': str,
        'login_selectors': dict,  # Dict[str, ElementSelectors]
        'authenticated_indicator': ElementSelectors,
        'navigation_map': dict,  # Dict[str, str]
        'profile_name': str
    }
    
    actual_fields = {f.name: f.type for f in fields(AppConfig)}
    
    print(f"\nRequired fields: {len(required_fields)}")
    print(f"Actual fields: {len(actual_fields)}")
    
    all_present = True
    for field_name, expected_type in required_fields.items():
        if field_name in actual_fields:
            print(f"  ✓ {field_name}: {actual_fields[field_name]}")
        else:
            print(f"  ✗ MISSING: {field_name}")
            all_present = False
    
    if all_present:
        print("\n✓ AppConfig: All required fields present")
        return True
    else:
        print("\n✗ AppConfig: Missing required fields")
        return False


def verify_session_state_enum():
    """Verify SessionState enum has all required states."""
    print("\n" + "=" * 70)
    print("Verifying SessionState enum")
    print("=" * 70)
    
    required_states = {'CREATING', 'ACTIVE', 'IDLE', 'CRASHED', 'CLOSING'}
    actual_states = {state.name for state in SessionState}
    
    print(f"\nRequired states: {required_states}")
    print(f"Actual states: {actual_states}")
    
    if required_states == actual_states:
        print("\n✓ SessionState: All required states present")
        return True
    else:
        missing = required_states - actual_states
        extra = actual_states - required_states
        if missing:
            print(f"\n✗ Missing states: {missing}")
        if extra:
            print(f"\n  Extra states: {extra}")
        return False


def test_instantiation():
    """Test that data models can be instantiated correctly."""
    print("\n" + "=" * 70)
    print("Testing data model instantiation")
    print("=" * 70)
    
    try:
        # Test BrowserSession
        session = BrowserSession(
            session_id="test-123",
            profile_name="default",
            domain="example.com",
            playwright_context=None,
            playwright_page=None,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            is_headless=True,
            state=SessionState.ACTIVE
        )
        print("\n✓ BrowserSession instantiation successful")
        print(f"  session_id: {session.session_id}")
        print(f"  profile_name: {session.profile_name}")
        print(f"  is_headless: {session.is_headless}")
        print(f"  state: {session.state}")
        
        # Test RetryConfig
        retry_config = RetryConfig()
        print("\n✓ RetryConfig instantiation successful (with defaults)")
        print(f"  max_retries: {retry_config.max_retries}")
        print(f"  exponential_backoff: {retry_config.exponential_backoff}")
        
        # Test AppConfig
        app_config = AppConfig(
            app_name="TestApp",
            url="https://test.com",
            login_url="https://test.com/login",
            login_selectors={},
            authenticated_indicator=ElementSelectors(
                css_selector=".user-menu",
                xpath="//div[@class='user-menu']"
            ),
            navigation_map={"home": "/", "settings": "/settings"},
            profile_name="default"
        )
        print("\n✓ AppConfig instantiation successful")
        print(f"  app_name: {app_config.app_name}")
        print(f"  url: {app_config.url}")
        print(f"  profile_name: {app_config.profile_name}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Instantiation failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("\n" + "=" * 70)
    print("TASK 2.4 VERIFICATION: Data Models for Sessions and Configurations")
    print("=" * 70)
    print("\nRequirements: 7.1, 7.2, 8.1, 8.2")
    print("Verifying: BrowserSession, RetryConfig, AppConfig")
    
    results = []
    
    # Run all verification checks
    results.append(("BrowserSession", verify_browser_session()))
    results.append(("RetryConfig", verify_retry_config()))
    results.append(("AppConfig", verify_app_config()))
    results.append(("SessionState", verify_session_state_enum()))
    results.append(("Instantiation", test_instantiation()))
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL CHECKS PASSED - Task 2.4 Complete")
        print("=" * 70)
        return 0
    else:
        print("✗ SOME CHECKS FAILED - Review required")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
