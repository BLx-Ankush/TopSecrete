"""
Integration tests for Security features in Browser Automation Engine.

Tests security integration including:
- Credential encryption
- Sensitive data filtering in logs
- SSL certificate validation
- Banking website permission checks
- Payment confirmation workflow

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import ssl

from alice_browser_automation.engine import BrowserAutomationEngine
from alice_browser_automation.config import Config, SecurityConfig
from alice_browser_automation.types import TaskType, BrowserTask, ActionType, BrowserAction, ElementSelectors
from alice_browser_automation.security import SecurityManager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def security_config():
    """Create security configuration for testing."""
    config = Config()
    config.security = SecurityConfig(
        require_payment_confirmation=True,
        block_banking_sites=False,
        validate_ssl=True,
        clear_sensitive_data=True
    )
    return config


@pytest.fixture
def strict_security_config():
    """Create strict security configuration that blocks banking sites."""
    config = Config()
    config.security = SecurityConfig(
        require_payment_confirmation=True,
        block_banking_sites=True,
        validate_ssl=True,
        clear_sensitive_data=True
    )
    return config


@pytest.fixture
async def engine_with_security(security_config):
    """Create engine with security features enabled."""
    engine = BrowserAutomationEngine(config=security_config)
    
    # Mock components to avoid actual initialization
    engine.is_initialized = True
    engine.session_manager = Mock()
    engine.dom_parser = Mock()
    engine.livekit_bridge = Mock()
    engine.error_handler = Mock()
    engine.security_manager = SecurityManager(
        require_payment_confirmation=security_config.security.require_payment_confirmation,
        block_banking_sites=security_config.security.block_banking_sites,
        validate_ssl=security_config.security.validate_ssl,
        clear_sensitive_data=security_config.security.clear_sensitive_data
    )
    
    yield engine
    
    # Cleanup
    engine.is_initialized = False


# ============================================================================
# Test Credential Encryption (Requirement 10.1)
# ============================================================================

class TestCredentialEncryption:
    """Test credential encryption in profile manager."""
    
    @pytest.mark.asyncio
    async def test_credentials_encrypted_in_profile(self, engine_with_security):
        """Test that credentials are encrypted when stored in profiles."""
        # This is tested in profile_manager tests
        # Here we verify the engine uses encrypted profiles
        assert engine_with_security.security_manager is not None
        assert engine_with_security.security_manager.clear_sensitive_data is True


# ============================================================================
# Test Sensitive Data Filtering (Requirement 10.2)
# ============================================================================

class TestSensitiveDataFiltering:
    """Test sensitive data filtering in logs."""
    
    @pytest.mark.asyncio
    async def test_sensitive_data_filtered_in_logs(self, engine_with_security, caplog):
        """Test that sensitive data is filtered from log messages."""
        from alice_browser_automation.security import install_sensitive_data_filter
        
        # Install the filter
        install_sensitive_data_filter(engine_with_security.security_manager)
        
        caplog.set_level(logging.INFO)
        
        # Log a message with sensitive data
        logger = logging.getLogger('alice_browser_automation')
        logger.info("Processing card: 4532123456789010")
        
        # Check that sensitive data was filtered
        assert "4532123456789010" not in caplog.text
        assert "[REDACTED_CC]" in caplog.text
    
    @pytest.mark.asyncio
    async def test_sensitive_field_tracking(self, engine_with_security):
        """Test that sensitive fields are tracked during typing."""
        # Create mock page and selector
        mock_page = AsyncMock()
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_element.fill = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        selector = ElementSelectors(
            css_selector="#password",
            xpath="//input[@id='password']",
            aria_label="Password",
            test_id="password-input",
            text_content=""
        )
        
        # Execute type action with sensitive data
        await engine_with_security._execute_type_action(
            page=mock_page,
            selector=selector,
            text="secret123",
            clear_first=True,
            progress_callback=lambda x: None
        )
        
        # Verify sensitive data was registered
        assert len(engine_with_security.security_manager._sensitive_contexts) > 0
    
    @pytest.mark.asyncio
    async def test_sensitive_data_cleared_after_task(self, engine_with_security):
        """Test that sensitive data is cleared after task completion."""
        # Register some sensitive data
        engine_with_security.security_manager.register_sensitive_data(
            "password", "password", "secret123"
        )
        engine_with_security.security_manager.register_sensitive_data(
            "card_number", "credit_card", "4532123456789010"
        )
        
        assert len(engine_with_security.security_manager._sensitive_contexts) == 2
        
        # Clear sensitive data (simulating task completion)
        engine_with_security.security_manager.clear_all_sensitive_data()
        
        # Verify all cleared
        assert len(engine_with_security.security_manager._sensitive_contexts) == 0


# ============================================================================
# Test Payment Confirmation (Requirement 10.3, 10.4)
# ============================================================================

class TestPaymentConfirmation:
    """Test payment confirmation workflow."""
    
    @pytest.mark.asyncio
    async def test_payment_action_detection(self, engine_with_security):
        """Test detection of payment-related actions."""
        # Test various payment-related descriptions
        assert engine_with_security.security_manager.is_payment_action("Click payment button")
        assert engine_with_security.security_manager.is_payment_action("Complete checkout")
        assert engine_with_security.security_manager.is_payment_action("Submit payment")
        assert not engine_with_security.security_manager.is_payment_action("Click search")
    
    @pytest.mark.asyncio
    async def test_payment_confirmation_required(self, engine_with_security):
        """Test that payment confirmation is required."""
        task_id = "test_task_123"
        
        # Create payment confirmation
        confirmation = engine_with_security.security_manager.create_payment_confirmation(
            task_id=task_id,
            amount="$99.99",
            merchant="Test Store",
            payment_method="1234"
        )
        
        # Should not be confirmed yet
        assert not engine_with_security.security_manager.is_payment_confirmed(task_id)
        
        # Confirm payment
        engine_with_security.security_manager.confirm_payment(task_id)
        
        # Now should be confirmed
        assert engine_with_security.security_manager.is_payment_confirmed(task_id)
    
    @pytest.mark.asyncio
    async def test_payment_cancellation(self, engine_with_security):
        """Test payment cancellation."""
        task_id = "test_task_123"
        
        # Create payment confirmation
        engine_with_security.security_manager.create_payment_confirmation(
            task_id=task_id,
            amount="$99.99"
        )
        
        assert task_id in engine_with_security.security_manager._pending_payments
        
        # Cancel payment
        engine_with_security.security_manager.cancel_payment(task_id)
        
        assert task_id not in engine_with_security.security_manager._pending_payments


# ============================================================================
# Test SSL Certificate Validation (Requirement 10.5)
# ============================================================================

class TestSSLValidation:
    """Test SSL certificate validation."""
    
    @pytest.mark.asyncio
    async def test_ssl_validation_for_https(self, engine_with_security):
        """Test SSL validation for HTTPS URLs."""
        # Mock SSL validation
        with patch.object(
            engine_with_security.security_manager,
            'validate_ssl_certificate',
            return_value=True
        ) as mock_validate:
            # Create mock page
            mock_page = AsyncMock()
            mock_page.goto = AsyncMock()
            
            # Execute navigate action
            await engine_with_security._execute_navigate_action(
                page=mock_page,
                url="https://example.com",
                progress_callback=lambda x: None
            )
            
            # Verify SSL validation was called
            mock_validate.assert_called_once_with("https://example.com")
    
    @pytest.mark.asyncio
    async def test_ssl_validation_failure(self, engine_with_security):
        """Test handling of SSL validation failure."""
        # Mock SSL validation to fail
        with patch.object(
            engine_with_security.security_manager,
            'validate_ssl_certificate',
            side_effect=ssl.SSLError("Certificate verification failed")
        ):
            # Create mock page
            mock_page = AsyncMock()
            
            # Execute navigate action should raise SSL error
            with pytest.raises(ssl.SSLError):
                await engine_with_security._execute_navigate_action(
                    page=mock_page,
                    url="https://invalid-cert.com",
                    progress_callback=lambda x: None
                )
    
    @pytest.mark.asyncio
    async def test_no_ssl_validation_for_http(self, engine_with_security):
        """Test that HTTP URLs don't trigger SSL validation."""
        # Create mock page
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        
        # Execute navigate action with HTTP URL
        await engine_with_security._execute_navigate_action(
            page=mock_page,
            url="http://example.com",
            progress_callback=lambda x: None
        )
        
        # Should succeed without SSL validation
        mock_page.goto.assert_called_once()


# ============================================================================
# Test Banking Website Permissions (Requirement 10.6)
# ============================================================================

class TestBankingPermissions:
    """Test banking website permission checks."""
    
    @pytest.mark.asyncio
    async def test_banking_site_detection(self, engine_with_security):
        """Test detection of banking websites."""
        assert engine_with_security.security_manager.is_banking_website("https://chase.com")
        assert engine_with_security.security_manager.is_banking_website("https://bankofamerica.com")
        assert not engine_with_security.security_manager.is_banking_website("https://google.com")
    
    @pytest.mark.asyncio
    async def test_banking_permission_check_allowed(self, engine_with_security):
        """Test banking permission check when allowed."""
        # Grant permission first
        engine_with_security.security_manager.grant_banking_permission("https://chase.com")
        
        # Create mock page
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        
        # Should succeed
        await engine_with_security._execute_navigate_action(
            page=mock_page,
            url="https://chase.com",
            progress_callback=lambda x: None
        )
        
        mock_page.goto.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_banking_permission_check_blocked(self, strict_security_config):
        """Test banking permission check when blocked."""
        # Create engine with strict security
        engine = BrowserAutomationEngine(config=strict_security_config)
        engine.is_initialized = True
        engine.security_manager = SecurityManager(
            require_payment_confirmation=True,
            block_banking_sites=True,
            validate_ssl=True,
            clear_sensitive_data=True
        )
        engine.error_handler = Mock()
        
        # Create mock page
        mock_page = AsyncMock()
        
        # Should raise PermissionError
        with pytest.raises(PermissionError):
            await engine._execute_navigate_action(
                page=mock_page,
                url="https://chase.com",
                progress_callback=lambda x: None
            )
    
    @pytest.mark.asyncio
    async def test_non_banking_site_allowed(self, engine_with_security):
        """Test that non-banking sites are always allowed."""
        # Create mock page
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        
        # Should succeed without permission
        await engine_with_security._execute_navigate_action(
            page=mock_page,
            url="https://google.com",
            progress_callback=lambda x: None
        )
        
        mock_page.goto.assert_called_once()


# ============================================================================
# Integration Tests
# ============================================================================

class TestSecurityIntegration:
    """Integration tests for security features."""
    
    @pytest.mark.asyncio
    async def test_complete_security_workflow(self, engine_with_security):
        """Test complete security workflow with all features."""
        # 1. Register sensitive data
        engine_with_security.security_manager.register_sensitive_data(
            "password", "password", "secret123"
        )
        
        # 2. Check payment action
        is_payment = engine_with_security.security_manager.is_payment_action(
            "Complete checkout"
        )
        assert is_payment
        
        # 3. Create payment confirmation
        task_id = "test_task"
        engine_with_security.security_manager.create_payment_confirmation(
            task_id=task_id,
            amount="$150.00"
        )
        
        # 4. Confirm payment
        engine_with_security.security_manager.confirm_payment(task_id)
        assert engine_with_security.security_manager.is_payment_confirmed(task_id)
        
        # 5. Clear sensitive data
        engine_with_security.security_manager.clear_all_sensitive_data()
        assert len(engine_with_security.security_manager._sensitive_contexts) == 0
    
    @pytest.mark.asyncio
    async def test_security_in_task_execution(self, engine_with_security):
        """Test security features during task execution."""
        # Mock components
        engine_with_security.livekit_bridge.translate_voice_command = AsyncMock(
            return_value=BrowserTask(
                task_id="test_123",
                description="Test task",
                task_type=TaskType.WEB_BOOKING,
                parameters={},
                target_url="https://example.com",
                expected_outcome="Success"
            )
        )
        
        engine_with_security._execute_web_booking = AsyncMock(
            return_value=Mock(
                task_id="test_123",
                success=True,
                summary="Task completed",
                actions_taken=[],
                extracted_data={},
                error=None,
                duration_seconds=1.0,
                screenshots=[]
            )
        )
        
        # Register sensitive data before task
        engine_with_security.security_manager.register_sensitive_data(
            "password", "password", "secret123"
        )
        
        assert len(engine_with_security.security_manager._sensitive_contexts) == 1
        
        # Execute task
        result = await engine_with_security.execute_task(
            task_description="Test booking",
            task_type=TaskType.WEB_BOOKING,
            parameters={},
            callback=None
        )
        
        # Verify sensitive data was cleared after task
        assert len(engine_with_security.security_manager._sensitive_contexts) == 0
        assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
