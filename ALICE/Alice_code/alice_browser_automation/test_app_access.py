"""
Integration tests for Application Access Action Suite (Task 16.3).

Tests application access with valid session, re-authentication, navigation,
information extraction, and profile persistence.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from alice_browser_automation.app_access import (
    ApplicationAccessActionSuite, AppConfig, AppAccessResult,
    AppType, GMAIL_CONFIG, GITHUB_CONFIG, LINKEDIN_CONFIG
)
from alice_browser_automation.types import TaskResult, TaskType, BrowserSession, SessionState
from alice_browser_automation.engine import BrowserAutomationEngine
from alice_browser_automation.config import Config


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return Config()


@pytest.fixture
def mock_engine(mock_config):
    """Create a mock browser automation engine."""
    engine = Mock(spec=BrowserAutomationEngine)
    engine.config = mock_config
    engine.execute_task = AsyncMock()
    return engine


@pytest.fixture
def app_access_suite(mock_engine):
    """Create Application Access Action Suite for testing."""
    return ApplicationAccessActionSuite(engine=mock_engine)


@pytest.fixture
def mock_session():
    """Create a mock browser session."""
    mock_page = AsyncMock()
    mock_page.url = "https://mail.google.com"
    mock_page.goto = AsyncMock()
    mock_page.query_selector = AsyncMock()
    mock_page.title = AsyncMock(return_value="Gmail")
    mock_page.text_content = AsyncMock(return_value="Email content")
    
    return BrowserSession(
        session_id="test-session-123",
        profile_name="gmail_profile",
        domain="mail.google.com",
        playwright_context=Mock(),
        playwright_page=mock_page,
        created_at=datetime.now(),
        last_activity=datetime.now(),
        is_headless=True,
        state=SessionState.ACTIVE
    )


@pytest.fixture
def sample_app_config():
    """Create a sample app configuration."""
    return AppConfig(
        app_name="TestApp",
        app_type=AppType.PRODUCTIVITY,
        url="https://testapp.com",
        login_url="https://testapp.com/login",
        profile_name="test_profile",
        logged_in_indicator="div.user-menu",
        sections={
            "dashboard": "https://testapp.com/dashboard",
            "settings": "https://testapp.com/settings"
        }
    )


# ============================================================================
# Test: Initialization
# ============================================================================

class TestAppAccessInitialization:
    """Test Application Access Action Suite initialization."""
    
    def test_initialization_default_config(self, mock_engine):
        """Test initialization with default configuration."""
        suite = ApplicationAccessActionSuite(engine=mock_engine)
        
        assert suite.engine == mock_engine
        assert "gmail" in suite.app_configs
        assert "github" in suite.app_configs
        assert "linkedin" in suite.app_configs
    
    def test_initialization_with_custom_apps(self, mock_engine):
        """Test initialization with custom app configurations."""
        custom_config = {
            "applications": {
                "custom_app": {
                    "app_name": "CustomApp",
                    "app_type": "other",
                    "url": "https://custom.com"
                }
            }
        }
        
        suite = ApplicationAccessActionSuite(engine=mock_engine, config=custom_config)
        
        assert "custom_app" in suite.app_configs
        assert suite.app_configs["custom_app"].app_name == "CustomApp"
    
    def test_predefined_configs_exist(self, app_access_suite):
        """Test that predefined app configs are loaded."""
        assert app_access_suite.get_app_config("gmail") is not None
        assert app_access_suite.get_app_config("github") is not None
        assert app_access_suite.get_app_config("linkedin") is not None


# ============================================================================
# Test: Application Access with Valid Session
# ============================================================================

class TestApplicationAccessValidSession:
    """Test application access with valid session."""
    
    @pytest.mark.asyncio
    async def test_access_application_success(
        self, app_access_suite, mock_engine
    ):
        """Test successful application access."""
        # Mock successful result
        mock_result = TaskResult(
            task_id="app_access_123",
            success=True,
            summary="Gmail accessed successfully",
            actions_taken=["navigate", "check_auth"],
            extracted_data={"authenticated": True, "info": {"title": "Gmail"}},
            error="",
            duration_seconds=2.0
        )
        mock_engine.execute_task.return_value = mock_result
        
        # Execute access
        result = await app_access_suite.access_application(
            app_name="gmail",
            action="open"
        )
        
        # Assertions
        assert result.success is True
        assert result.authenticated is True
        assert result.app_name == "Gmail"
        mock_engine.execute_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_access_application_with_section(
        self, app_access_suite, mock_engine
    ):
        """Test application access with specific section."""
        mock_result = TaskResult(
            task_id="app_access_123",
            success=True,
            summary="Gmail inbox accessed",
            actions_taken=["navigate"],
            extracted_data={"authenticated": True},
            error="",
            duration_seconds=1.5
        )
        mock_engine.execute_task.return_value = mock_result
        
        result = await app_access_suite.access_application(
            app_name="gmail",
            section="inbox"
        )
        
        assert result.success is True
        assert result.section_accessed == "inbox"
        
        # Verify section was passed in parameters
        call_args = mock_engine.execute_task.call_args
        assert call_args.kwargs["parameters"]["section"] == "inbox"
    
    @pytest.mark.asyncio
    async def test_access_application_with_info_extraction(
        self, app_access_suite, mock_engine
    ):
        """Test application access with information extraction."""
        mock_result = TaskResult(
            task_id="app_access_123",
            success=True,
            summary="Information extracted",
            actions_taken=["navigate", "extract"],
            extracted_data={
                "authenticated": True,
                "info": {"title": "Gmail", "unread_count": 5}
            },
            error="",
            duration_seconds=3.0
        )
        mock_engine.execute_task.return_value = mock_result
        
        result = await app_access_suite.access_application(
            app_name="gmail",
            extract_info=["title", "unread_count"]
        )
        
        assert result.success is True
        assert result.extracted_info is not None
        assert "title" in result.extracted_info


# ============================================================================
# Test: Re-authentication on Expired Session
# ============================================================================

class TestReAuthentication:
    """Test re-authentication when session expires."""
    
    @pytest.mark.asyncio
    async def test_check_authentication_logged_in(
        self, app_access_suite, sample_app_config, mock_session
    ):
        """Test authentication check when user is logged in."""
        # Mock element found (logged in)
        mock_element = Mock()
        mock_session.playwright_page.query_selector = AsyncMock(
            return_value=mock_element
        )
        
        is_authenticated = await app_access_suite.check_authentication(
            app_config=sample_app_config,
            session=mock_session
        )
        
        assert is_authenticated is True
        mock_session.playwright_page.query_selector.assert_called_once_with(
            sample_app_config.logged_in_indicator
        )
    
    @pytest.mark.asyncio
    async def test_check_authentication_logged_out(
        self, app_access_suite, sample_app_config, mock_session
    ):
        """Test authentication check when user is logged out."""
        # Mock element not found (logged out)
        mock_session.playwright_page.query_selector = AsyncMock(
            return_value=None
        )
        
        is_authenticated = await app_access_suite.check_authentication(
            app_config=sample_app_config,
            session=mock_session
        )
        
        assert is_authenticated is False
    
    @pytest.mark.asyncio
    async def test_authenticate_success(
        self, app_access_suite, sample_app_config, mock_session
    ):
        """Test successful authentication."""
        result = await app_access_suite.authenticate(
            app_config=sample_app_config,
            session=mock_session
        )
        
        assert result is True
        # Verify navigation to login URL
        mock_session.playwright_page.goto.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_with_credentials(
        self, app_access_suite, sample_app_config, mock_session
    ):
        """Test authentication with provided credentials."""
        credentials = {"username": "test@example.com", "password": "password123"}
        
        result = await app_access_suite.authenticate(
            app_config=sample_app_config,
            session=mock_session,
            credentials=credentials
        )
        
        assert result is True


# ============================================================================
# Test: Navigation Within Application
# ============================================================================

class TestApplicationNavigation:
    """Test navigation within applications."""
    
    @pytest.mark.asyncio
    async def test_navigate_to_section_success(
        self, app_access_suite, sample_app_config, mock_session
    ):
        """Test successful navigation to section."""
        result = await app_access_suite.navigate_to_section(
            app_config=sample_app_config,
            section="dashboard",
            session=mock_session
        )
        
        assert result is True
        mock_session.playwright_page.goto.assert_called_once_with(
            "https://testapp.com/dashboard",
            wait_until='networkidle'
        )
    
    @pytest.mark.asyncio
    async def test_navigate_to_invalid_section(
        self, app_access_suite, sample_app_config, mock_session
    ):
        """Test navigation to non-existent section."""
        result = await app_access_suite.navigate_to_section(
            app_config=sample_app_config,
            section="nonexistent",
            session=mock_session
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_navigate_with_progress_callback(
        self, app_access_suite, sample_app_config, mock_session
    ):
        """Test navigation with progress callback."""
        progress_callback = Mock()
        
        result = await app_access_suite.navigate_to_section(
            app_config=sample_app_config,
            section="settings",
            session=mock_session,
            progress_callback=progress_callback
        )
        
        assert result is True
        progress_callback.assert_called()


# ============================================================================
# Test: Information Extraction
# ============================================================================

class TestInformationExtraction:
    """Test information extraction from applications."""
    
    @pytest.mark.asyncio
    async def test_extract_title(
        self, app_access_suite, sample_app_config, mock_session
    ):
        """Test extracting page title."""
        info = await app_access_suite.extract_information(
            app_config=sample_app_config,
            info_types=["title"],
            session=mock_session
        )
        
        assert "title" in info
        assert info["title"] == "Gmail"
    
    @pytest.mark.asyncio
    async def test_extract_url(
        self, app_access_suite, sample_app_config, mock_session
    ):
        """Test extracting current URL."""
        info = await app_access_suite.extract_information(
            app_config=sample_app_config,
            info_types=["url"],
            session=mock_session
        )
        
        assert "url" in info
        assert info["url"] == "https://mail.google.com"
    
    @pytest.mark.asyncio
    async def test_extract_multiple_types(
        self, app_access_suite, sample_app_config, mock_session
    ):
        """Test extracting multiple information types."""
        info = await app_access_suite.extract_information(
            app_config=sample_app_config,
            info_types=["title", "url", "text"],
            session=mock_session
        )
        
        assert "title" in info
        assert "url" in info
        assert "text" in info
    
    @pytest.mark.asyncio
    async def test_extract_with_progress_callback(
        self, app_access_suite, sample_app_config, mock_session
    ):
        """Test extraction with progress callback."""
        progress_callback = Mock()
        
        info = await app_access_suite.extract_information(
            app_config=sample_app_config,
            info_types=["title"],
            session=mock_session,
            progress_callback=progress_callback
        )
        
        assert "title" in info
        progress_callback.assert_called()


# ============================================================================
# Test: Profile Persistence
# ============================================================================

class TestProfilePersistence:
    """Test Chrome profile persistence."""
    
    def test_app_config_has_profile_name(self):
        """Test that app configs specify profile names."""
        assert GMAIL_CONFIG.profile_name == "gmail_profile"
        assert GITHUB_CONFIG.profile_name == "github_profile"
        assert LINKEDIN_CONFIG.profile_name == "linkedin_profile"
    
    def test_profile_persistence_across_sessions(self, app_access_suite):
        """Test that profile names are consistent."""
        gmail_config = app_access_suite.get_app_config("gmail")
        
        # Profile name should be consistent
        assert gmail_config.profile_name is not None
        assert gmail_config.profile_name == "gmail_profile"


# ============================================================================
# Test: Helper Methods
# ============================================================================

class TestHelperMethods:
    """Test helper methods."""
    
    def test_get_app_config(self, app_access_suite):
        """Test getting app configuration."""
        config = app_access_suite.get_app_config("gmail")
        
        assert config is not None
        assert config.app_name == "Gmail"
    
    def test_get_app_config_case_insensitive(self, app_access_suite):
        """Test getting app config is case-insensitive."""
        config1 = app_access_suite.get_app_config("Gmail")
        config2 = app_access_suite.get_app_config("GMAIL")
        config3 = app_access_suite.get_app_config("gmail")
        
        assert config1 == config2 == config3
    
    def test_get_app_config_not_found(self, app_access_suite):
        """Test getting non-existent app config."""
        config = app_access_suite.get_app_config("nonexistent")
        
        assert config is None
    
    def test_add_app_config(self, app_access_suite):
        """Test adding new app configuration."""
        new_config = AppConfig(
            app_name="NewApp",
            app_type=AppType.OTHER,
            url="https://newapp.com"
        )
        
        app_access_suite.add_app_config(new_config)
        
        retrieved = app_access_suite.get_app_config("newapp")
        assert retrieved is not None
        assert retrieved.app_name == "NewApp"
    
    def test_list_available_apps(self, app_access_suite):
        """Test listing available applications."""
        apps = app_access_suite.list_available_apps()
        
        assert "gmail" in apps
        assert "github" in apps
        assert "linkedin" in apps
        assert len(apps) >= 3
    
    def test_get_app_sections(self, app_access_suite):
        """Test getting app sections."""
        sections = app_access_suite.get_app_sections("gmail")
        
        assert "inbox" in sections
        assert "sent" in sections
        assert "drafts" in sections
        assert "starred" in sections
    
    def test_get_app_sections_invalid_app(self, app_access_suite):
        """Test getting sections for invalid app."""
        sections = app_access_suite.get_app_sections("nonexistent")
        
        assert sections == []


# ============================================================================
# Test: Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling."""
    
    @pytest.mark.asyncio
    async def test_access_application_not_configured(
        self, app_access_suite, mock_engine
    ):
        """Test accessing non-configured application."""
        result = await app_access_suite.access_application(
            app_name="nonexistent"
        )
        
        assert result.success is False
        assert "not configured" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_access_application_engine_failure(
        self, app_access_suite, mock_engine
    ):
        """Test handling engine execution failure."""
        mock_engine.execute_task.side_effect = Exception("Engine error")
        
        result = await app_access_suite.access_application(
            app_name="gmail"
        )
        
        assert result.success is False
        assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_check_authentication_error(
        self, app_access_suite, sample_app_config, mock_session
    ):
        """Test authentication check error handling."""
        mock_session.playwright_page.query_selector = AsyncMock(
            side_effect=Exception("Query error")
        )
        
        is_authenticated = await app_access_suite.check_authentication(
            app_config=sample_app_config,
            session=mock_session
        )
        
        assert is_authenticated is False
    
    @pytest.mark.asyncio
    async def test_navigate_to_section_error(
        self, app_access_suite, sample_app_config, mock_session
    ):
        """Test navigation error handling."""
        mock_session.playwright_page.goto = AsyncMock(
            side_effect=Exception("Navigation error")
        )
        
        result = await app_access_suite.navigate_to_section(
            app_config=sample_app_config,
            section="dashboard",
            session=mock_session
        )
        
        assert result is False


# ============================================================================
# Test: Predefined Configurations
# ============================================================================

class TestPredefinedConfigurations:
    """Test predefined application configurations."""
    
    def test_gmail_config(self):
        """Test Gmail configuration."""
        assert GMAIL_CONFIG.app_name == "Gmail"
        assert GMAIL_CONFIG.app_type == AppType.EMAIL
        assert GMAIL_CONFIG.requires_2fa is True
        assert len(GMAIL_CONFIG.sections) >= 4
    
    def test_github_config(self):
        """Test GitHub configuration."""
        assert GITHUB_CONFIG.app_name == "GitHub"
        assert GITHUB_CONFIG.app_type == AppType.PRODUCTIVITY
        assert GITHUB_CONFIG.username_selector is not None
        assert GITHUB_CONFIG.password_selector is not None
    
    def test_linkedin_config(self):
        """Test LinkedIn configuration."""
        assert LINKEDIN_CONFIG.app_name == "LinkedIn"
        assert LINKEDIN_CONFIG.app_type == AppType.SOCIAL_MEDIA
        assert len(LINKEDIN_CONFIG.sections) >= 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
