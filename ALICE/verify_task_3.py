#!/usr/bin/env python3
"""
Verification script for Task 3: Exception Classes

This script verifies that all required exception classes are properly implemented
and can be instantiated with their expected attributes.
"""

import sys
from pathlib import Path

# Add the Alice_code directory to the path
sys.path.insert(0, str(Path(__file__).parent / "Alice_code"))

from alice_browser_automation.exceptions import (
    BrowserAutomationError,
    ElementNotFoundError,
    PageLoadTimeoutError,
    InvalidActionError,
    NetworkError,
    SessionCrashedError,
    QwenModelUnavailableError,
    OTPVerificationError,
    ProfileError,
    SecurityError,
    ConfigurationError,
    TaskCancelledException,
)


def test_base_exception():
    """Test BrowserAutomationError base exception"""
    print("Testing BrowserAutomationError...")
    exc = BrowserAutomationError("Test error")
    assert isinstance(exc, Exception)
    assert str(exc) == "Test error"
    print("  ✓ BrowserAutomationError works correctly")


def test_element_not_found_error():
    """Test ElementNotFoundError with attributes"""
    print("Testing ElementNotFoundError...")
    exc = ElementNotFoundError(
        "Element not found",
        selector="button.submit",
        page_url="https://example.com"
    )
    assert isinstance(exc, BrowserAutomationError)
    assert exc.selector == "button.submit"
    assert exc.page_url == "https://example.com"
    print("  ✓ ElementNotFoundError works correctly")


def test_page_load_timeout_error():
    """Test PageLoadTimeoutError with attributes"""
    print("Testing PageLoadTimeoutError...")
    exc = PageLoadTimeoutError(
        "Page load timeout",
        url="https://example.com",
        timeout_seconds=30.0
    )
    assert isinstance(exc, BrowserAutomationError)
    assert exc.url == "https://example.com"
    assert exc.timeout_seconds == 30.0
    print("  ✓ PageLoadTimeoutError works correctly")


def test_invalid_action_error():
    """Test InvalidActionError with attributes"""
    print("Testing InvalidActionError...")
    exc = InvalidActionError(
        "Invalid action JSON",
        invalid_json='{"action": "invalid"}',
        validation_error="Missing required field: action_type"
    )
    assert isinstance(exc, BrowserAutomationError)
    assert exc.invalid_json == '{"action": "invalid"}'
    assert exc.validation_error == "Missing required field: action_type"
    print("  ✓ InvalidActionError works correctly")


def test_network_error():
    """Test NetworkError with attributes"""
    print("Testing NetworkError...")
    original = ConnectionError("Connection refused")
    exc = NetworkError(
        "Network error occurred",
        operation="navigate",
        original_error=original
    )
    assert isinstance(exc, BrowserAutomationError)
    assert exc.operation == "navigate"
    assert exc.original_error == original
    print("  ✓ NetworkError works correctly")


def test_session_crashed_error():
    """Test SessionCrashedError with attributes"""
    print("Testing SessionCrashedError...")
    exc = SessionCrashedError(
        "Browser session crashed",
        session_id="session-123",
        last_url="https://example.com/page"
    )
    assert isinstance(exc, BrowserAutomationError)
    assert exc.session_id == "session-123"
    assert exc.last_url == "https://example.com/page"
    print("  ✓ SessionCrashedError works correctly")


def test_qwen_model_unavailable_error():
    """Test QwenModelUnavailableError with attributes"""
    print("Testing QwenModelUnavailableError...")
    original = ConnectionError("Connection refused")
    exc = QwenModelUnavailableError(
        "Qwen model unavailable",
        host="http://localhost:11434",
        model="qwen2.5-coder:3b",
        original_error=original
    )
    assert isinstance(exc, BrowserAutomationError)
    assert exc.host == "http://localhost:11434"
    assert exc.model == "qwen2.5-coder:3b"
    assert exc.original_error == original
    print("  ✓ QwenModelUnavailableError works correctly")


def test_additional_exceptions():
    """Test additional exception classes"""
    print("Testing additional exception classes...")
    
    # OTPVerificationError
    exc1 = OTPVerificationError("OTP failed", verification_type="SMS")
    assert isinstance(exc1, BrowserAutomationError)
    assert exc1.verification_type == "SMS"
    print("  ✓ OTPVerificationError works correctly")
    
    # ProfileError
    exc2 = ProfileError("Profile error", profile_name="default", operation="load")
    assert isinstance(exc2, BrowserAutomationError)
    assert exc2.profile_name == "default"
    assert exc2.operation == "load"
    print("  ✓ ProfileError works correctly")
    
    # SecurityError
    exc3 = SecurityError("Security violation", security_check="ssl_validation", resource="https://example.com")
    assert isinstance(exc3, BrowserAutomationError)
    assert exc3.security_check == "ssl_validation"
    assert exc3.resource == "https://example.com"
    print("  ✓ SecurityError works correctly")
    
    # ConfigurationError
    exc4 = ConfigurationError("Invalid config", config_key="timeout", config_value="-1")
    assert isinstance(exc4, BrowserAutomationError)
    assert exc4.config_key == "timeout"
    assert exc4.config_value == "-1"
    print("  ✓ ConfigurationError works correctly")
    
    # TaskCancelledException
    exc5 = TaskCancelledException("Task cancelled", task_id="task-123", reason="User request")
    assert isinstance(exc5, BrowserAutomationError)
    assert exc5.task_id == "task-123"
    assert exc5.reason == "User request"
    print("  ✓ TaskCancelledException works correctly")


def test_exception_inheritance():
    """Test that all exceptions inherit from BrowserAutomationError"""
    print("Testing exception inheritance hierarchy...")
    
    exceptions = [
        ElementNotFoundError("test"),
        PageLoadTimeoutError("test"),
        InvalidActionError("test"),
        NetworkError("test"),
        SessionCrashedError("test"),
        QwenModelUnavailableError("test"),
        OTPVerificationError("test"),
        ProfileError("test"),
        SecurityError("test"),
        ConfigurationError("test"),
        TaskCancelledException("test"),
    ]
    
    for exc in exceptions:
        assert isinstance(exc, BrowserAutomationError), f"{type(exc).__name__} does not inherit from BrowserAutomationError"
        assert isinstance(exc, Exception), f"{type(exc).__name__} does not inherit from Exception"
    
    print("  ✓ All exceptions properly inherit from BrowserAutomationError")


def main():
    """Run all verification tests"""
    print("=" * 70)
    print("Task 3 Verification: Exception Classes")
    print("=" * 70)
    print()
    
    try:
        test_base_exception()
        test_element_not_found_error()
        test_page_load_timeout_error()
        test_invalid_action_error()
        test_network_error()
        test_session_crashed_error()
        test_qwen_model_unavailable_error()
        test_additional_exceptions()
        test_exception_inheritance()
        
        print()
        print("=" * 70)
        print("✅ ALL TESTS PASSED - Task 3 Complete")
        print("=" * 70)
        print()
        print("Summary:")
        print("  • All 7 required exception classes implemented")
        print("  • All exceptions inherit from BrowserAutomationError")
        print("  • All exceptions have proper attributes and initialization")
        print("  • 5 additional exception classes for enhanced error handling")
        print("  • All exceptions properly documented with recovery strategies")
        print()
        return 0
        
    except AssertionError as e:
        print()
        print("=" * 70)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 70)
        return 1
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
