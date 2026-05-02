"""
Unit tests for ErrorHandler.

Tests error handling and recovery strategies including element not found,
page load timeout, invalid action, session crash, and network errors.

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6**
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from alice_browser_automation.error_handler import ErrorHandler
from alice_browser_automation.types import (
    BrowserSession,
    ElementSelectors,
    RetryConfig,
    SessionState
)
from alice_browser_automation.exceptions import (
    ElementNotFoundError,
    PageLoadTimeoutError,
    InvalidActionError,
    NetworkError,
    SessionCrashedError
)


class TestErrorHandlerInitialization:
    """Test ErrorHandler initialization."""
    
    def test_init_default_config(self):
        """Test initialization with default retry config."""
        handler = ErrorHandler()
        
        assert handler.retry_config is not None
        assert handler.retry_config.max_retries == 2
        assert handler.error_stats['element_not_found'] == 0
    
    def test_init_custom_config(self):
        """Test initialization with custom retry config."""
        config = RetryConfig(
            max_retries=5,
            retry_delay_seconds=2.0,
            exponential_backoff=False
        )
        
        handler = ErrorHandler(retry_config=config)
        
        assert handler.retry_config.max_retries == 5
        assert handler.retry_config.retry_delay_seconds == 2.0
        assert handler.retry_config.exponential_backoff is False


class TestElementNotFoundHandling:
    """Test element not found error handling."""
    
    @pytest.fixture
    def handler(self):
        """Create ErrorHandler instance."""
        return ErrorHandler()
    
    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright Page."""
        page = AsyncMock()
        page.url = "https://example.com/test"
        return page
    
    @pytest.fixture
    def selector(self):
        """Create test ElementSelectors."""
        return ElementSelectors(
            css_selector="button.submit",
            xpath="//button[@class='submit']",
            aria_label="Submit",
            text_content="Submit"
        )
    
    @pytest.mark.asyncio
    async def test_handle_element_not_found_css_success(self, handler, mock_page, selector):
        """Test successful element recovery using CSS selector."""
        # Mock element found with CSS selector
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        result = await handler.handle_element_not_found(
            mock_page,
            selector,
            "click submit button"
        )
        
        assert result is not None
        assert result.css_selector == selector.css_selector
        assert handler.error_stats['element_not_found'] == 1
        assert handler.error_stats['successful_recoveries'] == 1
    
    @pytest.mark.asyncio
    async def test_handle_element_not_found_xpath_fallback(self, handler, mock_page, selector):
        """Test element recovery using XPath fallback."""
        # CSS selector fails, XPath succeeds
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)
        
        async def query_selector_side_effect(sel):
            if sel == selector.css_selector:
                return None  # CSS fails
            elif sel.startswith("xpath="):
                return mock_element  # XPath succeeds
            return None
        
        mock_page.query_selector = AsyncMock(side_effect=query_selector_side_effect)
        
        result = await handler.handle_element_not_found(
            mock_page,
            selector,
            "click submit button"
        )
        
        assert result is not None
        assert result.xpath == selector.xpath
    
    @pytest.mark.asyncio
    async def test_handle_element_not_found_all_fail(self, handler, mock_page, selector):
        """Test element not found when all selectors fail."""
        # All selectors fail
        mock_page.query_selector = AsyncMock(return_value=None)
        
        with pytest.raises(ElementNotFoundError, match="after .* retries"):
            await handler.handle_element_not_found(
                mock_page,
                selector,
                "click submit button"
            )
        
        assert handler.error_stats['failed_recoveries'] == 1


class TestPageLoadTimeoutHandling:
    """Test page load timeout error handling."""
    
    @pytest.fixture
    def handler(self):
        """Create ErrorHandler instance."""
        return ErrorHandler()
    
    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright Page."""
        page = AsyncMock()
        page.url = "https://example.com"
        return page
    
    @pytest.mark.asyncio
    async def test_handle_page_load_timeout_success_on_retry(self, handler, mock_page):
        """Test successful page load on retry."""
        url = "https://example.com/slow-page"
        
        # First call fails, second succeeds
        call_count = 0
        
        async def goto_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                from playwright.async_api import TimeoutError as PlaywrightTimeoutError
                raise PlaywrightTimeoutError("Timeout")
            return None
        
        mock_page.goto = AsyncMock(side_effect=goto_side_effect)
        
        result = await handler.handle_page_load_timeout(mock_page, url, timeout_seconds=10)
        
        assert result is True
        assert handler.error_stats['page_load_timeout'] == 1
        assert handler.error_stats['successful_recoveries'] == 1
    
    @pytest.mark.asyncio
    async def test_handle_page_load_timeout_all_fail(self, handler, mock_page):
        """Test page load timeout when all retries fail."""
        url = "https://example.com/unreachable"
        
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        mock_page.goto = AsyncMock(side_effect=PlaywrightTimeoutError("Timeout"))
        
        with pytest.raises(PageLoadTimeoutError, match="after .* retries"):
            await handler.handle_page_load_timeout(mock_page, url, timeout_seconds=5)
        
        assert handler.error_stats['failed_recoveries'] == 1


class TestInvalidActionHandling:
    """Test invalid action error handling."""
    
    @pytest.fixture
    def handler(self):
        """Create ErrorHandler instance."""
        return ErrorHandler()
    
    @pytest.mark.asyncio
    async def test_handle_invalid_action_no_qwen_client(self, handler):
        """Test invalid action handling without Qwen client."""
        invalid_json = '{"action": "invalid"}'
        validation_error = "Missing required field: action_type"
        context = {'task_description': 'Click button'}
        
        with pytest.raises(InvalidActionError, match="QwenModelClient not available"):
            await handler.handle_invalid_action(invalid_json, validation_error, context)
        
        assert handler.error_stats['invalid_action'] == 1


class TestSessionCrashHandling:
    """Test session crash error handling."""
    
    @pytest.fixture
    def handler(self):
        """Create ErrorHandler with mock SessionManager."""
        mock_session_manager = Mock()  # Use Mock instead of AsyncMock
        mock_session_manager.mark_session_crashed = Mock()  # Synchronous method
        mock_session_manager.restart_crashed_session = AsyncMock()  # Async method
        return ErrorHandler(session_manager=mock_session_manager)
    
    @pytest.fixture
    def mock_session(self):
        """Create mock BrowserSession."""
        session = Mock()
        session.session_id = "crashed-session-id"
        session.profile_name = "test-profile"
        session.domain = "example.com"
        session.state = SessionState.CRASHED
        
        mock_page = AsyncMock()
        mock_page.url = "https://example.com/page"
        session.playwright_page = mock_page
        
        return session
    
    @pytest.mark.asyncio
    async def test_handle_session_crashed_success(self, handler, mock_session):
        """Test successful session crash recovery."""
        # Mock new session after restart
        new_session = Mock()
        new_session.session_id = "new-session-id"
        new_session.profile_name = "test-profile"
        new_session.domain = "example.com"
        new_session.state = SessionState.ACTIVE
        
        handler.session_manager.restart_crashed_session = AsyncMock(return_value=new_session)
        
        result = await handler.handle_session_crashed(mock_session)
        
        assert result == new_session
        assert handler.error_stats['session_crashed'] == 1
        assert handler.error_stats['successful_recoveries'] == 1
        handler.session_manager.mark_session_crashed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_session_crashed_no_manager(self, mock_session):
        """Test session crash handling without SessionManager."""
        handler = ErrorHandler()  # No session manager
        
        with pytest.raises(SessionCrashedError, match="SessionManager not available"):
            await handler.handle_session_crashed(mock_session)


class TestNetworkErrorHandling:
    """Test network error handling."""
    
    @pytest.fixture
    def handler(self):
        """Create ErrorHandler instance."""
        return ErrorHandler()
    
    @pytest.mark.asyncio
    async def test_handle_network_error_success_on_retry(self, handler):
        """Test successful operation on retry after network error."""
        operation = "fetch data"
        original_error = Exception("Connection refused")
        
        # Mock connectivity check
        async def mock_check_connectivity():
            return True
        
        with patch.object(handler, '_check_connectivity', side_effect=mock_check_connectivity):
            # Mock retry callback that succeeds on second try
            call_count = 0
            
            async def retry_callback():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("Network error")
                return "success"
            
            result = await handler.handle_network_error(
                operation,
                original_error,
                retry_callback
            )
            
            assert result == "success"
            assert handler.error_stats['network_error'] == 1
            assert handler.error_stats['successful_recoveries'] == 1
    
    @pytest.mark.asyncio
    async def test_handle_network_error_no_connectivity(self, handler):
        """Test network error when connectivity check fails."""
        operation = "fetch data"
        original_error = Exception("Connection refused")
        
        # Mock connectivity check failure
        async def mock_check_connectivity():
            return False
        
        with patch.object(handler, '_check_connectivity', side_effect=mock_check_connectivity):
            with pytest.raises(NetworkError, match="Network connectivity check failed"):
                await handler.handle_network_error(operation, original_error)
            
            assert handler.error_stats['failed_recoveries'] == 1
    
    @pytest.mark.asyncio
    async def test_handle_network_error_all_retries_fail(self, handler):
        """Test network error when all retries fail."""
        operation = "fetch data"
        original_error = Exception("Connection refused")
        
        # Mock connectivity check success
        async def mock_check_connectivity():
            return True
        
        with patch.object(handler, '_check_connectivity', side_effect=mock_check_connectivity):
            # Mock retry callback that always fails
            async def retry_callback():
                raise Exception("Network error")
            
            with pytest.raises(NetworkError, match="after .* retries"):
                await handler.handle_network_error(
                    operation,
                    original_error,
                    retry_callback
                )
            
            assert handler.error_stats['failed_recoveries'] == 1


class TestExponentialBackoff:
    """Test exponential backoff strategy."""
    
    @pytest.fixture
    def handler(self):
        """Create ErrorHandler with exponential backoff enabled."""
        config = RetryConfig(
            exponential_backoff=True,
            retry_delay_seconds=1.0,
            backoff_multiplier=2.0
        )
        return ErrorHandler(retry_config=config)
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_increases_delay(self, handler):
        """Test that exponential backoff increases delay."""
        import time
        
        # Test first retry (2^0 = 1 second)
        start = time.time()
        await handler._exponential_backoff(0)
        elapsed = time.time() - start
        assert 0.9 <= elapsed <= 1.2  # Allow some tolerance
        
        # Test second retry (2^1 = 2 seconds)
        start = time.time()
        await handler._exponential_backoff(1)
        elapsed = time.time() - start
        assert 1.9 <= elapsed <= 2.2
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_caps_at_max(self, handler):
        """Test that exponential backoff caps at maximum delay."""
        import time
        
        # Test large retry count (should cap at 30 seconds)
        start = time.time()
        await handler._exponential_backoff(10)  # Would be 1024 seconds without cap
        elapsed = time.time() - start
        assert elapsed <= 31  # Should be capped at 30 seconds


class TestErrorStatistics:
    """Test error statistics tracking."""
    
    @pytest.fixture
    def handler(self):
        """Create ErrorHandler instance."""
        return ErrorHandler()
    
    def test_get_error_stats(self, handler):
        """Test getting error statistics."""
        stats = handler.get_error_stats()
        
        assert 'element_not_found' in stats
        assert 'page_load_timeout' in stats
        assert 'invalid_action' in stats
        assert 'session_crashed' in stats
        assert 'network_error' in stats
        assert 'total_retries' in stats
        assert 'successful_recoveries' in stats
        assert 'failed_recoveries' in stats
    
    def test_reset_error_stats(self, handler):
        """Test resetting error statistics."""
        # Increment some stats
        handler.error_stats['element_not_found'] = 5
        handler.error_stats['total_retries'] = 10
        
        # Reset
        handler.reset_error_stats()
        
        # Verify all reset to 0
        stats = handler.get_error_stats()
        for value in stats.values():
            assert value == 0


class TestErrorLogging:
    """Test error logging functionality."""
    
    @pytest.fixture
    def handler(self):
        """Create ErrorHandler instance."""
        return ErrorHandler()
    
    def test_log_error_with_context(self, handler, caplog):
        """Test error logging with context."""
        import logging
        caplog.set_level(logging.ERROR)
        
        handler._log_error(
            "TestError",
            {
                'key1': 'value1',
                'key2': 'value2'
            }
        )
        
        # Check that error was logged
        assert "TestError" in caplog.text
        assert "key1" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
