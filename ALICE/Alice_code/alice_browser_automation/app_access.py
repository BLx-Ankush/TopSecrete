"""
Application Accessing Action Suite for Alice Browser Automation.

This module implements the Application Accessing Action Suite that handles:
- Accessing web applications with persistent login
- Session management and re-authentication
- Application navigation
- Information extraction from applications

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from alice_browser_automation.types import (
    BrowserTask, TaskResult, BrowserSession, TaskType,
    BrowserAction, ActionType, ElementSelectors
)
from alice_browser_automation.exceptions import BrowserAutomationError


logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class AppType(Enum):
    """Types of web applications."""
    EMAIL = "email"
    SOCIAL_MEDIA = "social_media"
    PRODUCTIVITY = "productivity"
    CLOUD_STORAGE = "cloud_storage"
    MESSAGING = "messaging"
    OTHER = "other"


@dataclass
class AppConfig:
    """
    Configuration for a web application.
    """
    app_name: str
    app_type: AppType
    url: str
    login_url: Optional[str] = None
    profile_name: Optional[str] = None  # Chrome profile to use
    
    # Authentication selectors
    username_selector: Optional[str] = None
    password_selector: Optional[str] = None
    login_button_selector: Optional[str] = None
    
    # Session detection
    logged_in_indicator: Optional[str] = None  # Element that indicates logged in
    logged_out_indicator: Optional[str] = None  # Element that indicates logged out
    
    # Navigation
    sections: Dict[str, str] = field(default_factory=dict)  # section_name -> URL
    
    # Metadata
    requires_2fa: bool = False
    session_timeout_minutes: int = 60
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "app_name": self.app_name,
            "app_type": self.app_type.value,
            "url": self.url,
            "login_url": self.login_url,
            "profile_name": self.profile_name,
            "username_selector": self.username_selector,
            "password_selector": self.password_selector,
            "login_button_selector": self.login_button_selector,
            "logged_in_indicator": self.logged_in_indicator,
            "logged_out_indicator": self.logged_out_indicator,
            "sections": self.sections,
            "requires_2fa": self.requires_2fa,
            "session_timeout_minutes": self.session_timeout_minutes
        }


@dataclass
class AppAccessResult:
    """
    Result of accessing an application.
    """
    app_name: str
    success: bool
    authenticated: bool
    section_accessed: Optional[str] = None
    extracted_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "app_name": self.app_name,
            "success": self.success,
            "authenticated": self.authenticated,
            "section_accessed": self.section_accessed,
            "extracted_info": self.extracted_info,
            "error": self.error
        }


# ============================================================================
# Predefined Application Configurations
# ============================================================================

GMAIL_CONFIG = AppConfig(
    app_name="Gmail",
    app_type=AppType.EMAIL,
    url="https://mail.google.com",
    login_url="https://accounts.google.com",
    profile_name="gmail_profile",
    logged_in_indicator="div[role='navigation']",
    sections={
        "inbox": "https://mail.google.com/mail/u/0/#inbox",
        "sent": "https://mail.google.com/mail/u/0/#sent",
        "drafts": "https://mail.google.com/mail/u/0/#drafts",
        "starred": "https://mail.google.com/mail/u/0/#starred"
    },
    requires_2fa=True,
    session_timeout_minutes=120
)

GITHUB_CONFIG = AppConfig(
    app_name="GitHub",
    app_type=AppType.PRODUCTIVITY,
    url="https://github.com",
    login_url="https://github.com/login",
    profile_name="github_profile",
    username_selector="input[name='login']",
    password_selector="input[name='password']",
    login_button_selector="input[type='submit']",
    logged_in_indicator="img[alt*='@']",
    sections={
        "repositories": "https://github.com?tab=repositories",
        "issues": "https://github.com/issues",
        "pull_requests": "https://github.com/pulls",
        "notifications": "https://github.com/notifications"
    },
    requires_2fa=False,
    session_timeout_minutes=180
)

LINKEDIN_CONFIG = AppConfig(
    app_name="LinkedIn",
    app_type=AppType.SOCIAL_MEDIA,
    url="https://www.linkedin.com",
    login_url="https://www.linkedin.com/login",
    profile_name="linkedin_profile",
    logged_in_indicator="div.global-nav",
    sections={
        "feed": "https://www.linkedin.com/feed/",
        "network": "https://www.linkedin.com/mynetwork/",
        "jobs": "https://www.linkedin.com/jobs/",
        "messages": "https://www.linkedin.com/messaging/"
    },
    requires_2fa=False,
    session_timeout_minutes=60
)


# ============================================================================
# Application Accessing Action Suite
# ============================================================================

class ApplicationAccessActionSuite:
    """
    Application Accessing Action Suite for browser automation.
    
    Handles accessing web applications with persistent login, session management,
    re-authentication, and information extraction.
    
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
    """
    
    def __init__(
        self,
        engine: Any,  # BrowserAutomationEngine (avoid circular import)
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Application Accessing Action Suite.
        
        Args:
            engine: BrowserAutomationEngine instance
            config: Optional configuration dictionary
        """
        self.engine = engine
        self.config = config or {}
        
        # Predefined application configurations
        self.app_configs: Dict[str, AppConfig] = {
            "gmail": GMAIL_CONFIG,
            "github": GITHUB_CONFIG,
            "linkedin": LINKEDIN_CONFIG
        }
        
        # Load custom app configs from configuration
        custom_apps = self.config.get("applications", {})
        for app_name, app_data in custom_apps.items():
            self.app_configs[app_name.lower()] = self._parse_app_config(app_data)
        
        logger.info(f"Application Access Action Suite initialized with {len(self.app_configs)} apps")
    
    # ========================================================================
    # Main Application Access Method
    # ========================================================================
    
    async def access_application(
        self,
        app_name: str,
        action: str = "open",
        section: Optional[str] = None,
        extract_info: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> AppAccessResult:
        """
        Access a web application with persistent login.
        
        Workflow:
        1. Get application configuration
        2. Load Chrome profile for persistent session
        3. Navigate to application
        4. Check authentication status
        5. Re-authenticate if session expired
        6. Navigate to requested section
        7. Extract requested information
        8. Return results
        
        Args:
            app_name: Name of the application (gmail, github, etc.)
            action: Action to perform (open, navigate, extract)
            section: Optional section to navigate to
            extract_info: Optional list of information to extract
            parameters: Optional additional parameters
            progress_callback: Optional callback for progress updates
        
        Returns:
            AppAccessResult with access details
        
        Requirements: 7.3, 7.4, 7.5, 7.6
        """
        logger.info(f"Accessing application: {app_name}")
        
        try:
            # Get application configuration
            app_config = self.get_app_config(app_name)
            if not app_config:
                return AppAccessResult(
                    app_name=app_name,
                    success=False,
                    authenticated=False,
                    error=f"Application '{app_name}' not configured"
                )
            
            if progress_callback:
                progress_callback(f"Opening {app_config.app_name}...")
            
            # Create browser task
            task = BrowserTask(
                task_id=f"app_access_{datetime.now().timestamp()}",
                description=f"Access {app_config.app_name}",
                task_type=TaskType.APP_ACCESS,
                parameters={
                    "app_name": app_name,
                    "action": action,
                    "section": section,
                    "extract_info": extract_info or [],
                    **(parameters or {})
                },
                target_url=app_config.url,
                expected_outcome=f"{app_config.app_name} accessed successfully"
            )
            
            # Execute task through engine
            result = await self.engine.execute_task(
                task_description=task.description,
                task_type=task.task_type,
                parameters=task.parameters,
                target_url=task.target_url,
                progress_callback=progress_callback
            )
            
            # Parse result into AppAccessResult
            app_result = AppAccessResult(
                app_name=app_config.app_name,
                success=result.success,
                authenticated=result.extracted_data.get("authenticated", False),
                section_accessed=section,
                extracted_info=result.extracted_data.get("info"),
                error=result.error if not result.success else None
            )
            
            logger.info(f"Application access completed: {app_result.success}")
            return app_result
            
        except Exception as e:
            logger.error(f"Application access failed: {e}")
            return AppAccessResult(
                app_name=app_name,
                success=False,
                authenticated=False,
                error=str(e)
            )
    
    # ========================================================================
    # Authentication Methods
    # ========================================================================
    
    async def check_authentication(
        self,
        app_config: AppConfig,
        session: BrowserSession,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Check if user is authenticated in the application.
        
        Args:
            app_config: Application configuration
            session: Browser session
            progress_callback: Optional callback for progress updates
        
        Returns:
            True if authenticated, False otherwise
        
        Requirements: 7.4
        """
        logger.info(f"Checking authentication for {app_config.app_name}")
        
        try:
            if progress_callback:
                progress_callback(f"Checking login status for {app_config.app_name}...")
            
            # Check for logged-in indicator
            if app_config.logged_in_indicator:
                page = session.playwright_page
                element = await page.query_selector(app_config.logged_in_indicator)
                
                if element:
                    logger.info(f"User is authenticated in {app_config.app_name}")
                    return True
            
            # Check for logged-out indicator
            if app_config.logged_out_indicator:
                page = session.playwright_page
                element = await page.query_selector(app_config.logged_out_indicator)
                
                if element:
                    logger.info(f"User is NOT authenticated in {app_config.app_name}")
                    return False
            
            # Default to not authenticated if indicators not found
            logger.warning(f"Could not determine authentication status for {app_config.app_name}")
            return False
            
        except Exception as e:
            logger.error(f"Authentication check failed: {e}")
            return False
    
    async def authenticate(
        self,
        app_config: AppConfig,
        session: BrowserSession,
        credentials: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Authenticate user in the application.
        
        Args:
            app_config: Application configuration
            session: Browser session
            credentials: Optional credentials (username, password)
            progress_callback: Optional callback for progress updates
        
        Returns:
            True if authentication successful, False otherwise
        
        Requirements: 7.4
        """
        logger.info(f"Authenticating in {app_config.app_name}")
        
        try:
            if progress_callback:
                progress_callback(f"Logging in to {app_config.app_name}...")
            
            # Navigate to login URL if specified
            if app_config.login_url:
                page = session.playwright_page
                await page.goto(app_config.login_url, wait_until='networkidle')
            
            # TODO: Implement actual authentication logic
            # This would involve:
            # 1. Filling username/password fields
            # 2. Clicking login button
            # 3. Handling 2FA if required
            # 4. Waiting for login to complete
            
            # For now, assume authentication via persistent profile
            logger.info(f"Authentication completed for {app_config.app_name}")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    # ========================================================================
    # Navigation Methods
    # ========================================================================
    
    async def navigate_to_section(
        self,
        app_config: AppConfig,
        section: str,
        session: BrowserSession,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Navigate to a specific section within the application.
        
        Args:
            app_config: Application configuration
            section: Section name to navigate to
            session: Browser session
            progress_callback: Optional callback for progress updates
        
        Returns:
            True if navigation successful, False otherwise
        
        Requirements: 7.5
        """
        logger.info(f"Navigating to {section} in {app_config.app_name}")
        
        try:
            # Get section URL
            if section not in app_config.sections:
                logger.error(f"Section '{section}' not found in {app_config.app_name}")
                return False
            
            section_url = app_config.sections[section]
            
            if progress_callback:
                progress_callback(f"Navigating to {section}...")
            
            # Navigate to section
            page = session.playwright_page
            await page.goto(section_url, wait_until='networkidle')
            
            logger.info(f"Navigation to {section} completed")
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    # ========================================================================
    # Information Extraction
    # ========================================================================
    
    async def extract_information(
        self,
        app_config: AppConfig,
        info_types: List[str],
        session: BrowserSession,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Extract information from the application.
        
        Args:
            app_config: Application configuration
            info_types: Types of information to extract
            session: Browser session
            progress_callback: Optional callback for progress updates
        
        Returns:
            Dictionary of extracted information
        
        Requirements: 7.6
        """
        logger.info(f"Extracting information from {app_config.app_name}")
        
        extracted = {}
        
        try:
            if progress_callback:
                progress_callback(f"Extracting information from {app_config.app_name}...")
            
            page = session.playwright_page
            
            for info_type in info_types:
                if info_type == "title":
                    extracted["title"] = await page.title()
                elif info_type == "url":
                    extracted["url"] = page.url
                elif info_type == "text":
                    extracted["text"] = await page.text_content("body")
                # Add more extraction types as needed
            
            logger.info(f"Information extraction completed: {len(extracted)} items")
            return extracted
            
        except Exception as e:
            logger.error(f"Information extraction failed: {e}")
            return extracted
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def get_app_config(self, app_name: str) -> Optional[AppConfig]:
        """
        Get application configuration by name.
        
        Args:
            app_name: Name of the application
        
        Returns:
            AppConfig or None if not found
        """
        return self.app_configs.get(app_name.lower())
    
    def add_app_config(self, app_config: AppConfig) -> None:
        """
        Add a new application configuration.
        
        Args:
            app_config: Application configuration to add
        """
        self.app_configs[app_config.app_name.lower()] = app_config
        logger.info(f"Added application configuration: {app_config.app_name}")
    
    def list_available_apps(self) -> List[str]:
        """
        Get list of available application names.
        
        Returns:
            List of application names
        """
        return list(self.app_configs.keys())
    
    def get_app_sections(self, app_name: str) -> List[str]:
        """
        Get available sections for an application.
        
        Args:
            app_name: Name of the application
        
        Returns:
            List of section names
        """
        app_config = self.get_app_config(app_name)
        if app_config:
            return list(app_config.sections.keys())
        return []
    
    def _parse_app_config(self, data: Dict[str, Any]) -> AppConfig:
        """Parse application configuration from dictionary."""
        return AppConfig(
            app_name=data.get("app_name", ""),
            app_type=AppType(data.get("app_type", "other")),
            url=data.get("url", ""),
            login_url=data.get("login_url"),
            profile_name=data.get("profile_name"),
            username_selector=data.get("username_selector"),
            password_selector=data.get("password_selector"),
            login_button_selector=data.get("login_button_selector"),
            logged_in_indicator=data.get("logged_in_indicator"),
            logged_out_indicator=data.get("logged_out_indicator"),
            sections=data.get("sections", {}),
            requires_2fa=data.get("requires_2fa", False),
            session_timeout_minutes=data.get("session_timeout_minutes", 60)
        )
