"""
Unit tests for SessionManager.

Tests session creation, lifecycle management, idle cleanup, crash recovery,
and concurrent session limits.

**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 9.6, 12.1**
"""

import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from alice_browser_automation.session_manager import SessionManager
from alice_browser_automation.profile_manager import ChromeProfileManager
from alice_browser_automation.types import SessionState
from alice_browser_automation.exceptions import (
    SessionError,
    SessionLimitError,
    SessionCrashedError
)


class TestSessionManagerInitialization:
    """Test SessionManager initialization and shutdown."""
    
    @pytest.fixture
    def temp_profiles_dir(self):
        """Create temporary profiles directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def profile_manager(self, temp_profiles_dir):
        """Create ChromeProfileManager instance."""
        return ChromeProfileManager(profiles_dir=temp_profiles_dir)
    
    def test_init_default_values(self, profile_manager):
        """Test SessionManager initialization with default values."""
        manager = SessionManager(profile_manager)
        
        assert manager.max_concurrent_sessions == 3
        assert manager.idle_timeout == timedelta(seconds=300)
        assert manager.browser_type == "chromium"
        assert len(manager.active_sessions) == 0
        assert len(manager.domain_sessions) == 0
    
    def test_init_custom_values(self, profile_manager):
        """Test SessionManager initialization with custom values."""
        manager = SessionManager(
            profile_manager,
            max_concurrent_sessions=5,
            idle_timeout_seconds=600,
            browser_type="firefox"
        )
        
        assert manager.max_concurrent_sessions == 5
        assert manager.idle_timeout == timedelta(seconds=600)
        assert manager.browser_type == "firefox"
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, profile_manager):
        """Test successful SessionManager initialization."""
        manager = SessionManager(profile_manager)
        
        with patch('alice_browser_automation.session_manager.async_playwright') as mock_pw:
            # Mock Playwright
            mock_playwright_instance = AsyncMock()
            mock_browser = AsyncMock()
            mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
            
            mock_pw.return_value.start = AsyncMock(return_value=mock_playwright_instance)
            
            await manager.initialize()
            
            assert manager._playwright is not None
            assert manager._browser is not None
            assert manager._cleanup_task is not None
    
    @pytest.mark.asyncio
    async def test_shutdown_closes_all_sessions(self, profile_manager):
        """Test that shutdown closes all active sessions."""
        manager = SessionManager(profile_manager)
        
        # Mock sessions
        mock_session1 = Mock()
        mock_session1.session_id = "session1"
        mock_session1.playwright_page = AsyncMock()
        mock_session1.playwright_context = AsyncMock()
        mock_session1.domain = "example.com"
        mock_session1.state = SessionState.ACTIVE
        
        mock_session2 = Mock()
        mock_session2.session_id = "session2"
        mock_session2.playwright_page = AsyncMock()
        mock_session2.playwright_context = AsyncMock()
        mock_session2.domain = "test.com"
        mock_session2.state = SessionState.ACTIVE
        
        manager.active_sessions = {
            "session1": mock_session1,
            "session2": mock_session2
        }
        manager.domain_sessions = {
            "example.com": "session1",
            "test.com": "session2"
        }
        
        # Mock browser and playwright
        manager._browser = AsyncMock()
        manager._playwright = AsyncMock()
        manager._cleanup_task = None
        
        await manager.shutdown()
        
        # Verify all sessions closed
        assert len(manager.active_sessions) == 0
        assert len(manager.domain_sessions) == 0
        
        # Verify browser and playwright stopped
        manager._browser.close.assert_called_once()
        manager._playwright.stop.assert_called_once()


class TestSessionCreation:
    """Test session creation functionality."""
    
    @pytest.fixture
    def temp_profiles_dir(self):
        """Create temporary profiles directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def profile_manager(self, temp_profiles_dir):
        """Create ChromeProfileManager instance."""
        return ChromeProfileManager(profiles_dir=temp_profiles_dir)
    
    @pytest.fixture
    def manager(self, profile_manager):
        """Create SessionManager instance."""
        manager = SessionManager(profile_manager)
        # Mock browser
        manager._browser = AsyncMock()
        return manager
    
    @pytest.mark.asyncio
    async def test_create_session_success(self, manager, profile_manager):
        """Test successful session creation."""
        # Create profile
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        session = await manager.create_session("test_profile", headless=True, domain="example.com")
        
        assert session is not None
        assert session.profile_name == "test_profile"
        assert session.domain == "example.com"
        assert session.is_headless is True
        assert session.state == SessionState.ACTIVE
        assert session.session_id in manager.active_sessions
        assert manager.domain_sessions["example.com"] == session.session_id
    
    @pytest.mark.asyncio
    async def test_create_session_enforces_limit(self, manager, profile_manager):
        """Test that session creation enforces concurrent limit."""
        # Create profile
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        # Create max sessions
        for i in range(manager.max_concurrent_sessions):
            await manager.create_session("test_profile", domain=f"example{i}.com")
        
        # Try to create one more - should fail
        with pytest.raises(SessionLimitError) as exc_info:
            await manager.create_session("test_profile")
        
        assert "Maximum concurrent sessions limit reached" in str(exc_info.value)
        assert exc_info.value.current_count == 3
        assert exc_info.value.max_limit == 3
    
    @pytest.mark.asyncio
    async def test_create_session_tracks_activity(self, manager, profile_manager):
        """Test that session creation sets activity timestamps."""
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        before_creation = datetime.now()
        session = await manager.create_session("test_profile")
        after_creation = datetime.now()
        
        assert before_creation <= session.created_at <= after_creation
        assert before_creation <= session.last_activity <= after_creation


class TestSessionReuse:
    """Test session reuse for same domain."""
    
    @pytest.fixture
    def temp_profiles_dir(self):
        """Create temporary profiles directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def profile_manager(self, temp_profiles_dir):
        """Create ChromeProfileManager instance."""
        return ChromeProfileManager(profiles_dir=temp_profiles_dir)
    
    @pytest.fixture
    def manager(self, profile_manager):
        """Create SessionManager instance."""
        manager = SessionManager(profile_manager)
        manager._browser = AsyncMock()
        return manager
    
    @pytest.mark.asyncio
    async def test_get_session_for_domain_found(self, manager, profile_manager):
        """Test getting existing session for domain."""
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        # Create session
        original_session = await manager.create_session("test_profile", domain="example.com")
        
        # Get session for same domain
        retrieved_session = await manager.get_session_for_domain("example.com")
        
        assert retrieved_session is not None
        assert retrieved_session.session_id == original_session.session_id
        assert retrieved_session.state == SessionState.ACTIVE
    
    @pytest.mark.asyncio
    async def test_get_session_for_domain_not_found(self, manager):
        """Test getting session for domain that doesn't exist."""
        session = await manager.get_session_for_domain("nonexistent.com")
        assert session is None
    
    @pytest.mark.asyncio
    async def test_get_session_for_domain_updates_activity(self, manager, profile_manager):
        """Test that getting session updates last activity."""
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        # Create session
        session = await manager.create_session("test_profile", domain="example.com")
        original_activity = session.last_activity
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        # Get session
        retrieved_session = await manager.get_session_for_domain("example.com")
        
        assert retrieved_session.last_activity > original_activity


class TestSessionClosure:
    """Test session closure functionality."""
    
    @pytest.fixture
    def temp_profiles_dir(self):
        """Create temporary profiles directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def profile_manager(self, temp_profiles_dir):
        """Create ChromeProfileManager instance."""
        return ChromeProfileManager(profiles_dir=temp_profiles_dir)
    
    @pytest.fixture
    def manager(self, profile_manager):
        """Create SessionManager instance."""
        manager = SessionManager(profile_manager)
        manager._browser = AsyncMock()
        return manager
    
    @pytest.mark.asyncio
    async def test_close_session_success(self, manager, profile_manager):
        """Test successful session closure."""
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        # Create session
        session = await manager.create_session("test_profile", domain="example.com")
        session_id = session.session_id
        
        # Close session
        await manager.close_session(session_id)
        
        # Verify session removed
        assert session_id not in manager.active_sessions
        assert "example.com" not in manager.domain_sessions
        
        # Verify Playwright resources closed
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_session_nonexistent(self, manager):
        """Test closing non-existent session raises error."""
        with pytest.raises(ValueError, match="Session not found"):
            await manager.close_session("nonexistent_session_id")


class TestIdleSessionCleanup:
    """Test idle session cleanup functionality."""
    
    @pytest.fixture
    def temp_profiles_dir(self):
        """Create temporary profiles directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def profile_manager(self, temp_profiles_dir):
        """Create ChromeProfileManager instance."""
        return ChromeProfileManager(profiles_dir=temp_profiles_dir)
    
    @pytest.fixture
    def manager(self, profile_manager):
        """Create SessionManager with short idle timeout."""
        manager = SessionManager(profile_manager, idle_timeout_seconds=1)
        manager._browser = AsyncMock()
        return manager
    
    @pytest.mark.asyncio
    async def test_close_idle_sessions(self, manager, profile_manager):
        """Test that idle sessions are closed."""
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        # Create session
        session = await manager.create_session("test_profile", domain="example.com")
        session_id = session.session_id
        
        # Make session idle by setting old last_activity
        session.last_activity = datetime.now() - timedelta(seconds=10)
        
        # Close idle sessions
        closed_count = await manager.close_idle_sessions()
        
        assert closed_count == 1
        assert session_id not in manager.active_sessions
    
    @pytest.mark.asyncio
    async def test_close_idle_sessions_keeps_active(self, manager, profile_manager):
        """Test that active sessions are not closed."""
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        # Create session
        session = await manager.create_session("test_profile", domain="example.com")
        session_id = session.session_id
        
        # Session is active (recent activity)
        session.last_activity = datetime.now()
        
        # Close idle sessions
        closed_count = await manager.close_idle_sessions()
        
        assert closed_count == 0
        assert session_id in manager.active_sessions


class TestCrashRecovery:
    """Test session crash recovery functionality."""
    
    @pytest.fixture
    def temp_profiles_dir(self):
        """Create temporary profiles directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def profile_manager(self, temp_profiles_dir):
        """Create ChromeProfileManager instance."""
        return ChromeProfileManager(profiles_dir=temp_profiles_dir)
    
    @pytest.fixture
    def manager(self, profile_manager):
        """Create SessionManager instance."""
        manager = SessionManager(profile_manager)
        manager._browser = AsyncMock()
        return manager
    
    @pytest.mark.asyncio
    async def test_mark_session_crashed(self, manager, profile_manager):
        """Test marking session as crashed."""
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        # Create session
        session = await manager.create_session("test_profile")
        session_id = session.session_id
        
        # Mark as crashed
        manager.mark_session_crashed(session_id)
        
        assert session.state == SessionState.CRASHED
    
    @pytest.mark.asyncio
    async def test_restart_crashed_session(self, manager, profile_manager):
        """Test restarting a crashed session."""
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        # Create session
        session = await manager.create_session("test_profile", domain="example.com")
        old_session_id = session.session_id
        
        # Mark as crashed
        manager.mark_session_crashed(old_session_id)
        
        # Restart session
        new_session = await manager.restart_crashed_session(old_session_id)
        
        assert new_session.session_id != old_session_id
        assert new_session.profile_name == "test_profile"
        assert new_session.domain == "example.com"
        assert new_session.state == SessionState.ACTIVE
        assert old_session_id not in manager.active_sessions
        assert new_session.session_id in manager.active_sessions
    
    @pytest.mark.asyncio
    async def test_restart_non_crashed_session_fails(self, manager, profile_manager):
        """Test that restarting non-crashed session raises error."""
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        # Create session
        session = await manager.create_session("test_profile")
        
        # Try to restart active session
        with pytest.raises(ValueError, match="is not crashed"):
            await manager.restart_crashed_session(session.session_id)


class TestSessionActivityTracking:
    """Test session activity tracking."""
    
    @pytest.fixture
    def temp_profiles_dir(self):
        """Create temporary profiles directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def profile_manager(self, temp_profiles_dir):
        """Create ChromeProfileManager instance."""
        return ChromeProfileManager(profiles_dir=temp_profiles_dir)
    
    @pytest.fixture
    def manager(self, profile_manager):
        """Create SessionManager instance."""
        manager = SessionManager(profile_manager)
        manager._browser = AsyncMock()
        return manager
    
    @pytest.mark.asyncio
    async def test_update_session_activity(self, manager, profile_manager):
        """Test updating session activity timestamp."""
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        # Create session
        session = await manager.create_session("test_profile")
        original_activity = session.last_activity
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        # Update activity
        manager.update_session_activity(session.session_id)
        
        assert session.last_activity > original_activity
    
    @pytest.mark.asyncio
    async def test_update_activity_changes_idle_to_active(self, manager, profile_manager):
        """Test that updating activity changes IDLE state to ACTIVE."""
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        # Create session
        session = await manager.create_session("test_profile")
        
        # Set to IDLE
        session.state = SessionState.IDLE
        
        # Update activity
        manager.update_session_activity(session.session_id)
        
        assert session.state == SessionState.ACTIVE


class TestSessionQueries:
    """Test session query methods."""
    
    @pytest.fixture
    def temp_profiles_dir(self):
        """Create temporary profiles directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def profile_manager(self, temp_profiles_dir):
        """Create ChromeProfileManager instance."""
        return ChromeProfileManager(profiles_dir=temp_profiles_dir)
    
    @pytest.fixture
    def manager(self, profile_manager):
        """Create SessionManager instance."""
        manager = SessionManager(profile_manager)
        manager._browser = AsyncMock()
        return manager
    
    @pytest.mark.asyncio
    async def test_get_session(self, manager, profile_manager):
        """Test getting session by ID."""
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        # Create session
        session = await manager.create_session("test_profile")
        
        # Get session
        retrieved = manager.get_session(session.session_id)
        
        assert retrieved is not None
        assert retrieved.session_id == session.session_id
    
    @pytest.mark.asyncio
    async def test_get_all_sessions(self, manager, profile_manager):
        """Test getting all active sessions."""
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        # Create multiple sessions
        session1 = await manager.create_session("test_profile", domain="example1.com")
        session2 = await manager.create_session("test_profile", domain="example2.com")
        
        # Get all sessions
        all_sessions = manager.get_all_sessions()
        
        assert len(all_sessions) == 2
        assert session1 in all_sessions
        assert session2 in all_sessions
    
    @pytest.mark.asyncio
    async def test_get_session_count(self, manager, profile_manager):
        """Test getting session count."""
        profile_manager.get_or_create_profile("test_profile")
        
        # Mock browser context and page
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        manager._browser.new_context = AsyncMock(return_value=mock_context)
        
        assert manager.get_session_count() == 0
        
        # Create sessions
        await manager.create_session("test_profile", domain="example1.com")
        assert manager.get_session_count() == 1
        
        await manager.create_session("test_profile", domain="example2.com")
        assert manager.get_session_count() == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
