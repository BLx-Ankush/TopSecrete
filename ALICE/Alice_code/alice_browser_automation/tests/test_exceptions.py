"""
Unit tests for exception classes.
"""

import pytest
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


class TestExceptions:
    """Test exception classes and their attributes"""
    
    def test_base_exception(self):
        """Test base BrowserAutomationError"""
        error = BrowserAutomationError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_element_not_found_error(self):
        """Test ElementNotFoundError with attributes"""
        error = ElementNotFoundError(
            "Element not found",
            selector="button#submit",
            page_url="https://example.com"
        )
        
        assert str(error) == "Element not found"
        assert error.selector == "button#submit"
        assert error.page_url == "https://example.com"
        assert isinstance(error, BrowserAutomationError)
    
    def test_page_load_timeout_error(self):
        """Test PageLoadTimeoutError with attributes"""
        error = PageLoadTimeoutError(
            "Page load timeout",
            url="https://example.com",
            timeout_seconds=30.0
        )
        
        assert str(error) == "Page load timeout"
        assert error.url == "https://example.com"
        assert error.timeout_seconds == 30.0
        assert isinstance(error, BrowserAutomationError)
    
    def test_invalid_action_error(self):
        """Test InvalidActionError with attributes"""
        error = InvalidActionError(
            "Invalid JSON",
            invalid_json='{"action": "click"',
            validation_error="Unexpected end of JSON"
        )
        
        assert str(error) == "Invalid JSON"
        assert error.invalid_json == '{"action": "click"'
        assert error.validation_error == "Unexpected end of JSON"
        assert isinstance(error, BrowserAutomationError)
    
    def test_network_error(self):
        """Test NetworkError with attributes"""
        original = ConnectionError("Connection refused")
        error = NetworkError(
            "Network error",
            operation="navigate",
            original_error=original
        )
        
        assert str(error) == "Network error"
        assert error.operation == "navigate"
        assert error.original_error == original
        assert isinstance(error, BrowserAutomationError)
    
    def test_session_crashed_error(self):
        """Test SessionCrashedError with attributes"""
        error = SessionCrashedError(
            "Session crashed",
            session_id="session-123",
            last_url="https://example.com"
        )
        
        assert str(error) == "Session crashed"
        assert error.session_id == "session-123"
        assert error.last_url == "https://example.com"
        assert isinstance(error, BrowserAutomationError)
    
    def test_qwen_model_unavailable_error(self):
        """Test QwenModelUnavailableError with attributes"""
        original = ConnectionError("Connection refused")
        error = QwenModelUnavailableError(
            "Model unavailable",
            host="http://localhost:11434",
            model="qwen2.5-coder:3b",
            original_error=original
        )
        
        assert str(error) == "Model unavailable"
        assert error.host == "http://localhost:11434"
        assert error.model == "qwen2.5-coder:3b"
        assert error.original_error == original
        assert isinstance(error, BrowserAutomationError)
    
    def test_otp_verification_error(self):
        """Test OTPVerificationError with attributes"""
        error = OTPVerificationError(
            "OTP verification failed",
            verification_type="SMS"
        )
        
        assert str(error) == "OTP verification failed"
        assert error.verification_type == "SMS"
        assert isinstance(error, BrowserAutomationError)
    
    def test_profile_error(self):
        """Test ProfileError with attributes"""
        error = ProfileError(
            "Profile error",
            profile_name="default",
            operation="load"
        )
        
        assert str(error) == "Profile error"
        assert error.profile_name == "default"
        assert error.operation == "load"
        assert isinstance(error, BrowserAutomationError)
    
    def test_security_error(self):
        """Test SecurityError with attributes"""
        error = SecurityError(
            "Security check failed",
            security_check="ssl_validation",
            resource="https://example.com"
        )
        
        assert str(error) == "Security check failed"
        assert error.security_check == "ssl_validation"
        assert error.resource == "https://example.com"
        assert isinstance(error, BrowserAutomationError)
    
    def test_configuration_error(self):
        """Test ConfigurationError with attributes"""
        error = ConfigurationError(
            "Invalid configuration",
            config_key="max_sessions",
            config_value="invalid"
        )
        
        assert str(error) == "Invalid configuration"
        assert error.config_key == "max_sessions"
        assert error.config_value == "invalid"
        assert isinstance(error, BrowserAutomationError)
    
    def test_task_cancelled_exception(self):
        """Test TaskCancelledException with attributes"""
        error = TaskCancelledException(
            "Task cancelled",
            task_id="task-123",
            reason="User requested cancellation"
        )
        
        assert str(error) == "Task cancelled"
        assert error.task_id == "task-123"
        assert error.reason == "User requested cancellation"
        assert isinstance(error, BrowserAutomationError)
