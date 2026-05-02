"""
Unit tests for Security Module.

Tests security features including:
- Sensitive data filtering
- Memory clearing
- SSL certificate validation
- Banking website permissions
- Payment confirmation workflow

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
import ssl

from alice_browser_automation.security import (
    SecurityManager,
    SensitiveDataContext,
    PaymentConfirmation,
    SensitiveDataFilter,
    install_sensitive_data_filter,
    BANKING_DOMAINS,
    PAYMENT_KEYWORDS
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def security_manager():
    """Create SecurityManager instance for testing."""
    return SecurityManager(
        require_payment_confirmation=True,
        block_banking_sites=False,
        validate_ssl=True,
        clear_sensitive_data=True
    )


@pytest.fixture
def strict_security_manager():
    """Create strict SecurityManager that blocks banking sites."""
    return SecurityManager(
        require_payment_confirmation=True,
        block_banking_sites=True,
        validate_ssl=True,
        clear_sensitive_data=True
    )


# ============================================================================
# Test Sensitive Data Filtering (Requirement 10.1, 10.2)
# ============================================================================

class TestSensitiveDataFiltering:
    """Test sensitive data filtering in logs."""
    
    def test_filter_credit_card_numbers(self, security_manager):
        """Test filtering credit card numbers."""
        text = "Card number: 4532-1234-5678-9010"
        filtered = security_manager.filter_sensitive_data(text)
        
        assert "4532-1234-5678-9010" not in filtered
        assert "[REDACTED_CC]" in filtered
    
    def test_filter_credit_card_no_dashes(self, security_manager):
        """Test filtering credit card without dashes."""
        text = "Card: 4532123456789010"
        filtered = security_manager.filter_sensitive_data(text)
        
        assert "4532123456789010" not in filtered
        assert "[REDACTED_CC]" in filtered
    
    def test_filter_ssn(self, security_manager):
        """Test filtering social security numbers."""
        text = "SSN: 123-45-6789"
        filtered = security_manager.filter_sensitive_data(text)
        
        assert "123-45-6789" not in filtered
        assert "[REDACTED_SSN]" in filtered
    
    def test_filter_otp_codes(self, security_manager):
        """Test filtering OTP codes."""
        text = "Your code is 123456"
        filtered = security_manager.filter_sensitive_data(text)
        
        assert "123456" not in filtered
        assert "[REDACTED_OTP]" in filtered
    
    def test_filter_api_keys(self, security_manager):
        """Test filtering API keys."""
        text = "api_key: sk_test_1234567890"
        filtered = security_manager.filter_sensitive_data(text)
        
        assert "[REDACTED_KEY]" in filtered
    
    def test_filter_email_addresses(self, security_manager):
        """Test filtering email addresses (partial)."""
        text = "Email: user@example.com"
        filtered = security_manager.filter_sensitive_data(text)
        
        # Should partially redact email
        assert "user@example.com" not in filtered
        assert "us***@example.com" in filtered or "[REDACTED_EMAIL]" in filtered
    
    def test_filter_multiple_sensitive_items(self, security_manager):
        """Test filtering multiple sensitive items in one text."""
        text = "Card: 4532123456789010, SSN: 123-45-6789, OTP: 123456"
        filtered = security_manager.filter_sensitive_data(text)
        
        assert "4532123456789010" not in filtered
        assert "123-45-6789" not in filtered
        assert "123456" not in filtered
        assert "[REDACTED_CC]" in filtered
        assert "[REDACTED_SSN]" in filtered
        assert "[REDACTED_OTP]" in filtered
    
    def test_is_sensitive_field_password(self, security_manager):
        """Test detecting password fields."""
        assert security_manager.is_sensitive_field("password", "password")
        assert security_manager.is_sensitive_field("user_password", "text")
        assert security_manager.is_sensitive_field("pwd", "text")
        assert not security_manager.is_sensitive_field("username", "text")
    
    def test_is_sensitive_field_credit_card(self, security_manager):
        """Test detecting credit card fields."""
        assert security_manager.is_sensitive_field("card_number", "text")
        assert security_manager.is_sensitive_field("credit_card", "text")
        assert security_manager.is_sensitive_field("cc_number", "text")
    
    def test_is_sensitive_field_cvv(self, security_manager):
        """Test detecting CVV fields."""
        assert security_manager.is_sensitive_field("cvv", "text")
        assert security_manager.is_sensitive_field("cvc", "text")
        assert security_manager.is_sensitive_field("security_code", "text")
    
    def test_is_sensitive_field_ssn(self, security_manager):
        """Test detecting SSN fields."""
        assert security_manager.is_sensitive_field("ssn", "text")
        assert security_manager.is_sensitive_field("social_security", "text")


# ============================================================================
# Test Memory Clearing (Requirement 10.4)
# ============================================================================

class TestMemoryClearing:
    """Test clearing sensitive data from memory."""
    
    def test_register_sensitive_data(self, security_manager):
        """Test registering sensitive data for tracking."""
        context = security_manager.register_sensitive_data(
            field_name="password",
            field_type="password",
            value="secret123"
        )
        
        assert context.field_name == "password"
        assert context.field_type == "password"
        assert context.value == "secret123"
        assert not context.cleared
    
    def test_clear_sensitive_context(self, security_manager):
        """Test clearing individual sensitive context."""
        context = SensitiveDataContext(
            field_name="password",
            field_type="password",
            value="secret123"
        )
        
        context.clear()
        
        assert context.value is None
        assert context.cleared
    
    def test_clear_all_sensitive_data(self, security_manager):
        """Test clearing all registered sensitive data."""
        # Register multiple sensitive fields
        security_manager.register_sensitive_data("password", "password", "secret1")
        security_manager.register_sensitive_data("card_number", "credit_card", "4532123456789010")
        security_manager.register_sensitive_data("cvv", "cvv", "123")
        
        assert len(security_manager._sensitive_contexts) == 3
        
        # Clear all
        security_manager.clear_all_sensitive_data()
        
        # All contexts should be cleared
        assert len(security_manager._sensitive_contexts) == 0
    
    def test_clear_sensitive_data_disabled(self):
        """Test that clearing can be disabled."""
        manager = SecurityManager(clear_sensitive_data=False)
        
        manager.register_sensitive_data("password", "password", "secret1")
        manager.clear_all_sensitive_data()
        
        # Should not clear when disabled
        # (In real implementation, contexts would remain but not be cleared)


# ============================================================================
# Test SSL Certificate Validation (Requirement 10.5)
# ============================================================================

class TestSSLValidation:
    """Test SSL certificate validation."""
    
    def test_validate_ssl_https_url(self, security_manager):
        """Test SSL validation for HTTPS URL."""
        # Test with a real HTTPS site (google.com should have valid cert)
        with patch('ssl.create_connection') as mock_conn:
            with patch('ssl.SSLContext.wrap_socket') as mock_wrap:
                mock_socket = MagicMock()
                mock_socket.getpeercert.return_value = {'subject': 'test'}
                mock_wrap.return_value.__enter__.return_value = mock_socket
                
                result = security_manager.validate_ssl_certificate("https://google.com")
                assert result is True
    
    def test_validate_ssl_http_url(self, security_manager):
        """Test that HTTP URLs are not validated."""
        result = security_manager.validate_ssl_certificate("http://example.com")
        assert result is True  # HTTP URLs pass through
    
    def test_validate_ssl_invalid_certificate(self, security_manager):
        """Test handling of invalid SSL certificate."""
        with patch('ssl.create_connection') as mock_conn:
            mock_conn.side_effect = ssl.SSLError("Certificate verification failed")
            
            with pytest.raises(ssl.SSLError):
                security_manager.validate_ssl_certificate("https://invalid-cert.com")
    
    def test_validate_ssl_disabled(self):
        """Test that SSL validation can be disabled."""
        manager = SecurityManager(validate_ssl=False)
        
        # Should pass even with invalid cert when disabled
        result = manager.validate_ssl_certificate("https://invalid-cert.com")
        assert result is True


# ============================================================================
# Test Banking Website Permissions (Requirement 10.6)
# ============================================================================

class TestBankingPermissions:
    """Test banking website permission checks."""
    
    def test_is_banking_website_exact_match(self, security_manager):
        """Test detecting banking websites by exact domain match."""
        assert security_manager.is_banking_website("https://chase.com")
        assert security_manager.is_banking_website("https://bankofamerica.com")
        assert security_manager.is_banking_website("https://paypal.com")
    
    def test_is_banking_website_subdomain(self, security_manager):
        """Test detecting banking websites by subdomain."""
        assert security_manager.is_banking_website("https://online.chase.com")
        assert security_manager.is_banking_website("https://secure.bankofamerica.com")
    
    def test_is_not_banking_website(self, security_manager):
        """Test non-banking websites."""
        assert not security_manager.is_banking_website("https://google.com")
        assert not security_manager.is_banking_website("https://amazon.com")
        assert not security_manager.is_banking_website("https://example.com")
    
    def test_check_banking_permission_non_banking(self, security_manager):
        """Test permission check for non-banking site."""
        result = security_manager.check_banking_permission("https://google.com")
        assert result is True
    
    def test_check_banking_permission_allowed(self, security_manager):
        """Test permission check when banking site is allowed."""
        # Grant permission first
        security_manager.grant_banking_permission("https://chase.com")
        
        result = security_manager.check_banking_permission("https://chase.com")
        assert result is True
    
    def test_check_banking_permission_blocked(self, strict_security_manager):
        """Test permission check when banking site is blocked."""
        with pytest.raises(PermissionError) as exc_info:
            strict_security_manager.check_banking_permission("https://chase.com")
        
        assert "explicit permission" in str(exc_info.value)
    
    def test_grant_banking_permission(self, security_manager):
        """Test granting banking permission."""
        security_manager.grant_banking_permission("https://chase.com")
        
        assert "chase.com" in security_manager._banking_permissions
        
        # Should now pass permission check
        result = security_manager.check_banking_permission("https://chase.com")
        assert result is True
    
    def test_revoke_banking_permission(self, security_manager):
        """Test revoking banking permission."""
        # Grant first
        security_manager.grant_banking_permission("https://chase.com")
        assert "chase.com" in security_manager._banking_permissions
        
        # Revoke
        security_manager.revoke_banking_permission("https://chase.com")
        assert "chase.com" not in security_manager._banking_permissions


# ============================================================================
# Test Payment Confirmation (Requirement 10.3, 10.4)
# ============================================================================

class TestPaymentConfirmation:
    """Test payment confirmation workflow."""
    
    def test_is_payment_action_by_description(self, security_manager):
        """Test detecting payment actions by description."""
        assert security_manager.is_payment_action("Click payment button")
        assert security_manager.is_payment_action("Complete checkout")
        assert security_manager.is_payment_action("Submit payment information")
        assert not security_manager.is_payment_action("Click search button")
    
    def test_is_payment_action_by_page_content(self, security_manager):
        """Test detecting payment actions by page content."""
        page_content = "Enter your credit card number and CVV to complete purchase"
        
        assert security_manager.is_payment_action("Click button", page_content)
    
    def test_create_payment_confirmation(self, security_manager):
        """Test creating payment confirmation."""
        confirmation = security_manager.create_payment_confirmation(
            task_id="task_123",
            amount="$99.99",
            merchant="Example Store",
            payment_method="1234"
        )
        
        assert confirmation.amount == "$99.99"
        assert confirmation.merchant == "Example Store"
        assert confirmation.payment_method == "1234"
        assert not confirmation.confirmed
        
        assert "task_123" in security_manager._pending_payments
    
    def test_confirm_payment(self, security_manager):
        """Test confirming a payment."""
        security_manager.create_payment_confirmation(
            task_id="task_123",
            amount="$99.99"
        )
        
        result = security_manager.confirm_payment("task_123")
        assert result is True
        
        assert security_manager.is_payment_confirmed("task_123")
    
    def test_confirm_nonexistent_payment(self, security_manager):
        """Test confirming non-existent payment."""
        result = security_manager.confirm_payment("nonexistent")
        assert result is False
    
    def test_is_payment_confirmed_no_confirmation_required(self):
        """Test payment confirmation when not required."""
        manager = SecurityManager(require_payment_confirmation=False)
        
        # Should always return True when confirmation not required
        assert manager.is_payment_confirmed("any_task")
    
    def test_is_payment_confirmed_no_pending(self, security_manager):
        """Test checking confirmation when no pending payment."""
        # Should return True if no pending payment
        assert security_manager.is_payment_confirmed("task_123")
    
    def test_cancel_payment(self, security_manager):
        """Test cancelling a payment."""
        security_manager.create_payment_confirmation(
            task_id="task_123",
            amount="$99.99"
        )
        
        assert "task_123" in security_manager._pending_payments
        
        security_manager.cancel_payment("task_123")
        
        assert "task_123" not in security_manager._pending_payments
    
    def test_get_payment_summary(self, security_manager):
        """Test getting payment summary."""
        security_manager.create_payment_confirmation(
            task_id="task_123",
            amount="$99.99",
            merchant="Example Store",
            payment_method="1234"
        )
        
        summary = security_manager.get_payment_summary("task_123")
        
        assert "$99.99" in summary
        assert "Example Store" in summary
        assert "1234" in summary
    
    def test_get_payment_summary_nonexistent(self, security_manager):
        """Test getting summary for non-existent payment."""
        summary = security_manager.get_payment_summary("nonexistent")
        assert summary is None


# ============================================================================
# Test Logging Filter (Requirement 10.2)
# ============================================================================

class TestLoggingFilter:
    """Test sensitive data logging filter."""
    
    def test_sensitive_data_filter_message(self, security_manager):
        """Test filtering sensitive data in log messages."""
        filter_instance = SensitiveDataFilter(security_manager)
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Card number: 4532123456789010",
            args=(),
            exc_info=None
        )
        
        filter_instance.filter(record)
        
        assert "4532123456789010" not in record.msg
        assert "[REDACTED_CC]" in record.msg
    
    def test_sensitive_data_filter_args(self, security_manager):
        """Test filtering sensitive data in log arguments."""
        filter_instance = SensitiveDataFilter(security_manager)
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Processing: %s",
            args=("Card: 4532123456789010",),
            exc_info=None
        )
        
        filter_instance.filter(record)
        
        assert "4532123456789010" not in record.args[0]
        assert "[REDACTED_CC]" in record.args[0]
    
    def test_install_sensitive_data_filter(self, security_manager):
        """Test installing filter on loggers."""
        # This should not raise any errors
        install_sensitive_data_filter(security_manager)
        
        # Verify filter is installed
        root_logger = logging.getLogger()
        assert any(isinstance(f, SensitiveDataFilter) for f in root_logger.filters)


# ============================================================================
# Integration Tests
# ============================================================================

class TestSecurityIntegration:
    """Integration tests for security features."""
    
    def test_full_payment_workflow(self, security_manager):
        """Test complete payment confirmation workflow."""
        task_id = "booking_123"
        
        # Detect payment action
        assert security_manager.is_payment_action("Complete checkout")
        
        # Create confirmation
        confirmation = security_manager.create_payment_confirmation(
            task_id=task_id,
            amount="$150.00",
            merchant="Travel Agency",
            payment_method="5678"
        )
        
        # Check not confirmed yet
        assert not security_manager.is_payment_confirmed(task_id)
        
        # Get summary for user
        summary = security_manager.get_payment_summary(task_id)
        assert "$150.00" in summary
        
        # User confirms
        security_manager.confirm_payment(task_id)
        
        # Now confirmed
        assert security_manager.is_payment_confirmed(task_id)
    
    def test_sensitive_data_lifecycle(self, security_manager):
        """Test complete lifecycle of sensitive data handling."""
        # Register sensitive data
        ctx1 = security_manager.register_sensitive_data(
            "password", "password", "secret123"
        )
        ctx2 = security_manager.register_sensitive_data(
            "card_number", "credit_card", "4532123456789010"
        )
        
        assert len(security_manager._sensitive_contexts) == 2
        
        # Filter in logs
        log_text = "Password: secret123, Card: 4532123456789010"
        filtered = security_manager.filter_sensitive_data(log_text)
        
        assert "secret123" not in filtered
        assert "4532123456789010" not in filtered
        
        # Clear all sensitive data
        security_manager.clear_all_sensitive_data()
        
        assert len(security_manager._sensitive_contexts) == 0
    
    def test_banking_site_workflow(self, strict_security_manager):
        """Test banking site access workflow."""
        url = "https://chase.com/login"
        
        # Initially blocked
        with pytest.raises(PermissionError):
            strict_security_manager.check_banking_permission(url)
        
        # Grant permission
        strict_security_manager.grant_banking_permission(url)
        
        # Now allowed
        assert strict_security_manager.check_banking_permission(url)
        
        # Revoke permission
        strict_security_manager.revoke_banking_permission(url)
        
        # Blocked again
        with pytest.raises(PermissionError):
            strict_security_manager.check_banking_permission(url)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
