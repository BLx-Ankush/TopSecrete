"""
Unit tests for Browser Automation Engine Session Management (Task 13.3).

Tests browser session management methods including session creation,
session reuse, idle session cleanup, OTP verification handling, and
domain extraction.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from alice_browser_automation.engine import BrowserAutomationEngine
from alice_browser_automation.config import Config
from alice_browser_automation.types import (
    BrowserSession, SessionState
)
from alice_browser_automation.exceptions import (
    SessionError, SessionLimitError, BrowserAutomationError
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return Config()


@pytest.fixture
def initialized_engine(mock_config):
    """Create an initialized engine for testing."""
    engine = BrowserAutomationEngine(config=mock_config)
    engine.is_initialized = True
    
    # Mock components
    engine.session_manager = AsyncMock()
    engine.profile_manager = Mock()
    engine.otp_handler = AsyncMock()
    
    return engine


@pytest.fixture
def mock_session():
    """Create a mock browser session."""
    return BrowserSession(
        session_id="test-session-123",
        profile_name="default",
        domain="example.com",
        playwright_context=Mock(),
        playwright_page=Mock(),
        created_at=datetime.now(),
        last_activity=datetime.now(),
        is_headless=True,
        state=SessionState.ACTIVE
    )


# ============================================================================
# Test: _create_browser_session
# ============================================================================

class TestCreateBrowserSession:
    """Test _create_browser_session method."""
    
    @pytest.mark.asyncio
    async def test_create_session_with_defaults(self, initialized_engine, mock_session):
        """Test creating session with default parameters."""
        # Mock session manager
        initialized_engine.session_manager.create_session = AsyncMock(
            return_value=mock_session
        )
        
        # Create session with defaults
        session = await initialized_engine._create_browser_session()
        
        # Assertions
        assert session == mock_session
        initialized_engine.session_manager.create_session.assert_called_once_with(
            profile_name=initialized_engine.config.browser.default_profile,
            headless=initialized_engine.config.browser.headless_default,
            domain=None
        )
    
    @pytest.mark.asyncio
    async def test_create_session_with_custom_params(self, initialized_engine, mock_session):
        """Test creating session with custom parameters."""
        # Mock session manager
        initialized_engine.session_manager.create_session = AsyncMock(
            return_value=mock_session
        )
        
        # Create session with custom params
        session = await initialized_engine._create_browser_session(
            profile_name="work",
            headless=False,
            domain="github.com"
        )
        
        # Assertions
        assert session == mock_session
        initialized_engine.session_manager.create_session.assert_called_once_with(
            profile_name="work",
            headless=False,
            domain="github.com"
        )
    
    @pytest.mark.asyncio
    async def test_create_session_headless_mode(self, initialized_engine, mock_session):
        """Test creating session in headless mode."""
        mock_session.is_headless = True
        initialized_engine.session_manager.create_session = AsyncMock(
            return_value=mock_session
        )
        
        session = await initialized_engine._create_browser_session(headless=True)
        
        assert session.is_headless is True
    
    @pytest.mark.asyncio
    async def test_create_session_headed_mode(self, initialized_engine, mock_session):
        """Test creating session in headed mode."""
        mock_session.is_headless = False
        initialized_engine.session_manager.create_session = AsyncMock(
            return_value=mock_session
        )
        
        session = await initialized_engine._create_browser_session(headless=False)
        
        assert session.is_headless is False
    
    @pytest.mark.asyncio
    async def test_create_session_with_domain(self, initialized_engine, mock_session):
        """Test creating session with domain for tracking."""
        mock_session.domain = "example.com"
        initialized_engine.session_manager.create_session = AsyncMock(
            return_value=mock_session
        )
        
        session = await initialized_engine._create_browser_session(domain="example.com")
        
        assert session.domain == "example.com"
    
    @pytest.mark.asyncio
    async def test_create_session_limit_error(self, initialized_engine):
        """Test creating session when limit reached."""
        # Mock session manager to raise limit error
        initialized_engine.session_manager.create_session = AsyncMock(
            side_effect=SessionLimitError(
                "Max sessions reached",
                current_count=3,
                max_limit=3
            )
        )
        
        # Should propagate the error
        with pytest.raises(SessionLimitError):
            await initialized_engine._create_browser_session()
    
    @pytest.mark.asyncio
    async def test_create_session_error(self, initialized_engine):
        """Test creating session with error."""
        # Mock session manager to raise error
        initialized_engine.session_manager.create_session = AsyncMock(
            side_effect=SessionError(
                "Failed to create session",
                session_id=None,
                operation="create"
            )
        )
        
        # Should propagate the error
        with pytest.raises(SessionError):
            await initialized_engine._create_browser_session()


# ============================================================================
# Test: _get_or_create_session
# ============================================================================

class TestGetOrCreateSession:
    """Test _get_or_create_session method."""
    
    @pytest.mark.asyncio
    async def test_get_existing_session(self, initialized_engine, mock_session):
        """Test getting existing session for domain."""
        # Mock session manager to return existing session
        initialized_engine.session_manager.get_session_for_domain = AsyncMock(
            return_value=mock_session
        )
        
        # Get or create session
        session = await initialized_engine._get_or_create_session("example.com")
        
        # Assertions
        assert session == mock_session
        initialized_engine.session_manager.get_session_for_domain.assert_called_once_with("example.com")
        # Should not create new session
        initialized_engine.session_manager.create_session.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_new_session_when_none_exists(self, initialized_engine, mock_session):
        """Test creating new session when none exists for domain."""
        # Mock session manager to return None (no existing session)
        initialized_engine.session_manager.get_session_for_domain = AsyncMock(
            return_value=None
        )
        initialized_engine.session_manager.create_session = AsyncMock(
            return_value=mock_session
        )
        
        # Get or create session
        session = await initialized_engine._get_or_create_session("example.com")
        
        # Assertions
        assert session == mock_session
        initialized_engine.session_manager.get_session_for_domain.assert_called_once_with("example.com")
        initialized_engine.session_manager.create_session.assert_called_once_with(
            profile_name=initialized_engine.config.browser.default_profile,
            headless=initialized_engine.config.browser.headless_default,
            domain="example.com"
        )
    
    @pytest.mark.asyncio
    async def test_get_or_create_with_custom_profile(self, initialized_engine, mock_session):
        """Test get or create with custom profile name."""
        # Mock session manager to return None (no existing session)
        initialized_engine.session_manager.get_session_for_domain = AsyncMock(
            return_value=None
        )
        initialized_engine.session_manager.create_session = AsyncMock(
            return_value=mock_session
        )
        
        # Get or create session with custom profile
        session = await initialized_engine._get_or_create_session(
            "example.com",
            profile_name="work"
        )
        
        # Assertions
        initialized_engine.session_manager.create_session.assert_called_once_with(
            profile_name="work",
            headless=initialized_engine.config.browser.headless_default,
            domain="example.com"
        )
    
    @pytest.mark.asyncio
    async def test_get_or_create_with_custom_headless(self, initialized_engine, mock_session):
        """Test get or create with custom headless setting."""
        # Mock session manager to return None (no existing session)
        initialized_engine.session_manager.get_session_for_domain = AsyncMock(
            return_value=None
        )
        initialized_engine.session_manager.create_session = AsyncMock(
            return_value=mock_session
        )
        
        # Get or create session with custom headless
        session = await initialized_engine._get_or_create_session(
            "example.com",
            headless=False
        )
        
        # Assertions
        initialized_engine.session_manager.create_session.assert_called_once_with(
            profile_name=initialized_engine.config.browser.default_profile,
            headless=False,
            domain="example.com"
        )
    
    @pytest.mark.asyncio
    async def test_get_or_create_reuses_active_session(self, initialized_engine, mock_session):
        """Test that active session is reused for same domain."""
        mock_session.state = SessionState.ACTIVE
        
        # Mock session manager to return active session
        initialized_engine.session_manager.get_session_for_domain = AsyncMock(
            return_value=mock_session
        )
        
        # Get or create session twice
        session1 = await initialized_engine._get_or_create_session("example.com")
        session2 = await initialized_engine._get_or_create_session("example.com")
        
        # Assertions - should return same session
        assert session1 == session2
        assert session1.session_id == session2.session_id
        # Should not create new session
        initialized_engine.session_manager.create_session.assert_not_called()


# ============================================================================
# Test: _close_idle_sessions
# ============================================================================

class TestCloseIdleSessions:
    """Test _close_idle_sessions method."""
    
    @pytest.mark.asyncio
    async def test_close_idle_sessions_none_idle(self, initialized_engine):
        """Test closing idle sessions when none are idle."""
        # Mock session manager to return 0 closed
        initialized_engine.session_manager.close_idle_sessions = AsyncMock(
            return_value=0
        )
        
        # Close idle sessions
        closed_count = await initialized_engine._close_idle_sessions()
        
        # Assertions
        assert closed_count == 0
        initialized_engine.session_manager.close_idle_sessions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_idle_sessions_some_idle(self, initialized_engine):
        """Test closing idle sessions when some are idle."""
        # Mock session manager to return 2 closed
        initialized_engine.session_manager.close_idle_sessions = AsyncMock(
            return_value=2
        )
        
        # Close idle sessions
        closed_count = await initialized_engine._close_idle_sessions()
        
        # Assertions
        assert closed_count == 2
        initialized_engine.session_manager.close_idle_sessions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_idle_sessions_multiple_calls(self, initialized_engine):
        """Test multiple calls to close idle sessions."""
        # Mock session manager to return different counts
        initialized_engine.session_manager.close_idle_sessions = AsyncMock(
            side_effect=[2, 1, 0]
        )
        
        # Close idle sessions multiple times
        count1 = await initialized_engine._close_idle_sessions()
        count2 = await initialized_engine._close_idle_sessions()
        count3 = await initialized_engine._close_idle_sessions()
        
        # Assertions
        assert count1 == 2
        assert count2 == 1
        assert count3 == 0
        assert initialized_engine.session_manager.close_idle_sessions.call_count == 3


# ============================================================================
# Test: _handle_otp_verification
# ============================================================================

class TestHandleOTPVerification:
    """Test _handle_otp_verification method."""
    
    @pytest.mark.asyncio
    async def test_handle_otp_with_livekit_session(self, initialized_engine, mock_session):
        """Test handling OTP with LiveKit session."""
        # Mock OTP handler
        mock_otp_handler = AsyncMock()
        mock_otp_handler.request_otp = AsyncMock(return_value="123456")
        mock_otp_handler.switch_to_headed_mode = AsyncMock()
        mock_otp_handler.switch_to_headless_mode = AsyncMock()
        
        initialized_engine.otp_handler = mock_otp_handler
        
        # Handle OTP
        otp = await initialized_engine._handle_otp_verification(
            session=mock_session,
            livekit_session=Mock()
        )
        
        # Assertions
        assert otp == "123456"
        mock_otp_handler.request_otp.assert_called_once_with(context="verification code")
    
    @pytest.mark.asyncio
    async def test_handle_otp_switches_to_headed_mode(self, initialized_engine, mock_session):
        """Test that OTP handling switches to headed mode for headless sessions."""
        mock_session.is_headless = True
        
        # Mock OTP handler
        mock_otp_handler = AsyncMock()
        mock_otp_handler.request_otp = AsyncMock(return_value="123456")
        mock_otp_handler.switch_to_headed_mode = AsyncMock()
        mock_otp_handler.switch_to_headless_mode = AsyncMock()
        
        initialized_engine.otp_handler = mock_otp_handler
        
        # Handle OTP
        await initialized_engine._handle_otp_verification(
            session=mock_session,
            livekit_session=Mock()
        )
        
        # Assertions
        mock_otp_handler.switch_to_headed_mode.assert_called_once_with(mock_session)
        mock_otp_handler.switch_to_headless_mode.assert_called_once_with(mock_session)
    
    @pytest.mark.asyncio
    async def test_handle_otp_no_mode_switch_for_headed(self, initialized_engine, mock_session):
        """Test that OTP handling doesn't switch mode for already headed sessions."""
        mock_session.is_headless = False
        
        # Mock OTP handler
        mock_otp_handler = AsyncMock()
        mock_otp_handler.request_otp = AsyncMock(return_value="123456")
        mock_otp_handler.switch_to_headed_mode = AsyncMock()
        mock_otp_handler.switch_to_headless_mode = AsyncMock()
        
        initialized_engine.otp_handler = mock_otp_handler
        
        # Handle OTP
        await initialized_engine._handle_otp_verification(
            session=mock_session,
            livekit_session=Mock()
        )
        
        # Assertions - should not switch modes
        mock_otp_handler.switch_to_headed_mode.assert_not_called()
        mock_otp_handler.switch_to_headless_mode.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_otp_without_livekit_session(self, initialized_engine, mock_session):
        """Test handling OTP without LiveKit session raises error."""
        initialized_engine.otp_handler = None
        
        # Handle OTP without LiveKit session should raise error
        with pytest.raises(BrowserAutomationError, match="OTP handler not available"):
            await initialized_engine._handle_otp_verification(
                session=mock_session,
                livekit_session=None
            )
    
    @pytest.mark.asyncio
    async def test_handle_otp_error_handling(self, initialized_engine, mock_session):
        """Test error handling in OTP verification."""
        # Mock OTP handler to raise error
        mock_otp_handler = AsyncMock()
        mock_otp_handler.request_otp = AsyncMock(
            side_effect=Exception("OTP request failed")
        )
        mock_otp_handler.switch_to_headed_mode = AsyncMock()
        
        initialized_engine.otp_handler = mock_otp_handler
        
        # Handle OTP should raise BrowserAutomationError
        with pytest.raises(BrowserAutomationError, match="Failed to handle OTP verification"):
            await initialized_engine._handle_otp_verification(
                session=mock_session,
                livekit_session=Mock()
            )


# ============================================================================
# Test: _extract_domain_from_url
# ============================================================================

class TestExtractDomainFromURL:
    """Test _extract_domain_from_url method."""
    
    def test_extract_domain_simple(self, initialized_engine):
        """Test extracting domain from simple URL."""
        url = "https://example.com/path"
        domain = initialized_engine._extract_domain_from_url(url)
        
        assert domain == "example.com"
    
    def test_extract_domain_with_www(self, initialized_engine):
        """Test extracting domain removes www prefix."""
        url = "https://www.example.com/path"
        domain = initialized_engine._extract_domain_from_url(url)
        
        assert domain == "example.com"
    
    def test_extract_domain_with_subdomain(self, initialized_engine):
        """Test extracting domain with subdomain."""
        url = "https://api.example.com/endpoint"
        domain = initialized_engine._extract_domain_from_url(url)
        
        assert domain == "api.example.com"
    
    def test_extract_domain_with_port(self, initialized_engine):
        """Test extracting domain with port."""
        url = "https://example.com:8080/path"
        domain = initialized_engine._extract_domain_from_url(url)
        
        assert domain == "example.com:8080"
    
    def test_extract_domain_http(self, initialized_engine):
        """Test extracting domain from HTTP URL."""
        url = "http://example.com/path"
        domain = initialized_engine._extract_domain_from_url(url)
        
        assert domain == "example.com"
    
    def test_extract_domain_no_path(self, initialized_engine):
        """Test extracting domain from URL without path."""
        url = "https://example.com"
        domain = initialized_engine._extract_domain_from_url(url)
        
        assert domain == "example.com"
    
    def test_extract_domain_with_query(self, initialized_engine):
        """Test extracting domain from URL with query parameters."""
        url = "https://example.com/path?param=value"
        domain = initialized_engine._extract_domain_from_url(url)
        
        assert domain == "example.com"
    
    def test_extract_domain_with_fragment(self, initialized_engine):
        """Test extracting domain from URL with fragment."""
        url = "https://example.com/path#section"
        domain = initialized_engine._extract_domain_from_url(url)
        
        assert domain == "example.com"
    
    def test_extract_domain_localhost(self, initialized_engine):
        """Test extracting domain from localhost URL."""
        url = "http://localhost:3000/app"
        domain = initialized_engine._extract_domain_from_url(url)
        
        assert domain == "localhost:3000"
    
    def test_extract_domain_ip_address(self, initialized_engine):
        """Test extracting domain from IP address URL."""
        url = "http://192.168.1.1/admin"
        domain = initialized_engine._extract_domain_from_url(url)
        
        assert domain == "192.168.1.1"


# ============================================================================
# Test: Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Test integration scenarios combining multiple methods."""
    
    @pytest.mark.asyncio
    async def test_session_reuse_workflow(self, initialized_engine, mock_session):
        """Test complete session reuse workflow."""
        # First request - no existing session
        initialized_engine.session_manager.get_session_for_domain = AsyncMock(
            return_value=None
        )
        initialized_engine.session_manager.create_session = AsyncMock(
            return_value=mock_session
        )
        
        # Get or create session
        session1 = await initialized_engine._get_or_create_session("example.com")
        assert session1 == mock_session
        
        # Second request - existing session
        initialized_engine.session_manager.get_session_for_domain = AsyncMock(
            return_value=mock_session
        )
        
        session2 = await initialized_engine._get_or_create_session("example.com")
        assert session2 == mock_session
        assert session1.session_id == session2.session_id
    
    @pytest.mark.asyncio
    async def test_otp_workflow_with_mode_switching(self, initialized_engine, mock_session):
        """Test complete OTP workflow with mode switching."""
        mock_session.is_headless = True
        
        # Mock OTP handler
        mock_otp_handler = AsyncMock()
        mock_otp_handler.request_otp = AsyncMock(return_value="654321")
        mock_otp_handler.switch_to_headed_mode = AsyncMock()
        mock_otp_handler.switch_to_headless_mode = AsyncMock()
        
        initialized_engine.otp_handler = mock_otp_handler
        
        # Handle OTP
        otp = await initialized_engine._handle_otp_verification(
            session=mock_session,
            livekit_session=Mock()
        )
        
        # Verify complete workflow
        assert otp == "654321"
        mock_otp_handler.switch_to_headed_mode.assert_called_once()
        mock_otp_handler.request_otp.assert_called_once()
        mock_otp_handler.switch_to_headless_mode.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_domain_extraction_and_session_creation(self, initialized_engine, mock_session):
        """Test extracting domain and creating session."""
        url = "https://www.github.com/user/repo"
        
        # Extract domain
        domain = initialized_engine._extract_domain_from_url(url)
        assert domain == "github.com"
        
        # Create session with extracted domain
        initialized_engine.session_manager.create_session = AsyncMock(
            return_value=mock_session
        )
        
        session = await initialized_engine._create_browser_session(domain=domain)
        
        initialized_engine.session_manager.create_session.assert_called_once_with(
            profile_name=initialized_engine.config.browser.default_profile,
            headless=initialized_engine.config.browser.headless_default,
            domain="github.com"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
