"""
Session Manager for Alice Browser Automation.

This module manages browser session lifecycle, including creation, reuse,
idle cleanup, and crash recovery. It enforces resource limits and ensures
efficient session management.

**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 9.6, 12.1**
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .types import BrowserSession, SessionState
from .exceptions import SessionError, SessionLimitError, SessionCrashedError
from .profile_manager import ChromeProfileManager


logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manage browser session lifecycle and resource limits.
    
    Responsibilities:
    - Create and manage Playwright browser sessions
    - Enforce concurrent session limits
    - Track session activity and state
    - Clean up idle sessions automatically
    - Recover from crashed sessions
    - Reuse sessions for same domain
    
    **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 9.6, 12.1**
    """
    
    def __init__(
        self,
        profile_manager: ChromeProfileManager,
        max_concurrent_sessions: int = 3,
        idle_timeout_seconds: int = 300,
        browser_type: str = "chromium"
    ):
        """
        Initialize the Session Manager.
        
        Args:
            profile_manager: ChromeProfileManager instance for profile handling
            max_concurrent_sessions: Maximum number of concurrent browser sessions.
                                    Defaults to 3.
            idle_timeout_seconds: Seconds before idle session is closed.
                                 Defaults to 300 (5 minutes).
            browser_type: Browser type to use (chromium, firefox, webkit).
                         Defaults to "chromium".
        
        **Validates: Requirement 8.1**
        """
        self.profile_manager = profile_manager
        self.max_concurrent_sessions = max_concurrent_sessions
        self.idle_timeout = timedelta(seconds=idle_timeout_seconds)
        self.browser_type = browser_type
        
        # Active sessions tracking
        self.active_sessions: Dict[str, BrowserSession] = {}
        
        # Domain to session mapping for reuse
        self.domain_sessions: Dict[str, str] = {}  # domain -> session_id
        
        # Warm session pool (1 ready session)
        self._warm_session: Optional[BrowserSession] = None
        self._warm_session_lock = asyncio.Lock()
        
        # Playwright instances
        self._playwright = None
        self._browser: Optional[Browser] = None
        
        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info(
            f"SessionManager initialized: max_sessions={max_concurrent_sessions}, "
            f"idle_timeout={idle_timeout_seconds}s, browser={browser_type}"
        )
    
    async def initialize(self) -> None:
        """
        Initialize Playwright and browser.
        
        Must be called before creating sessions.
        
        Raises:
            SessionError: If initialization fails
        """
        try:
            logger.info("Initializing Playwright and browser...")
            
            # Start Playwright
            self._playwright = await async_playwright().start()
            
            # Launch browser
            if self.browser_type == "chromium":
                self._browser = await self._playwright.chromium.launch()
            elif self.browser_type == "firefox":
                self._browser = await self._playwright.firefox.launch()
            elif self.browser_type == "webkit":
                self._browser = await self._playwright.webkit.launch()
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")
            
            logger.info(f"Browser launched successfully: {self.browser_type}")
            
            # Start background cleanup task
            self._cleanup_task = asyncio.create_task(self._background_cleanup())
            logger.info("Background cleanup task started")
            
            # Create warm session for faster first request
            await self._create_warm_session()
            
        except Exception as e:
            raise SessionError(
                "Failed to initialize SessionManager",
                session_id=None,
                operation="initialize"
            ) from e
    
    async def shutdown(self) -> None:
        """
        Shutdown all sessions and cleanup resources.
        
        Closes all active sessions and stops Playwright.
        """
        logger.info("Shutting down SessionManager...")
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all active sessions
        session_ids = list(self.active_sessions.keys())
        for session_id in session_ids:
            try:
                await self.close_session(session_id)
            except Exception as e:
                logger.error(f"Error closing session {session_id}: {e}")
        
        # Close browser
        if self._browser:
            await self._browser.close()
            logger.info("Browser closed")
        
        # Stop Playwright
        if self._playwright:
            await self._playwright.stop()
            logger.info("Playwright stopped")
        
        logger.info("SessionManager shutdown complete")
    
    async def create_session(
        self,
        profile_name: str = "default",
        headless: bool = True,
        domain: Optional[str] = None
    ) -> BrowserSession:
        """
        Create a new browser session.
        
        Creates a new Playwright browser context and page with the specified
        profile. Enforces concurrent session limits.
        
        Args:
            profile_name: Name of the Chrome profile to use. Defaults to "default".
            headless: Whether to run browser in headless mode. Defaults to True.
            domain: Optional domain for session reuse tracking.
        
        Returns:
            BrowserSession object representing the new session
        
        Raises:
            SessionLimitError: If max concurrent sessions limit reached
            SessionError: If session creation fails
        
        **Validates: Requirements 8.1, 8.2, 8.5, 12.1**
        
        Example:
            >>> manager = SessionManager(profile_manager)
            >>> await manager.initialize()
            >>> session = await manager.create_session("work", headless=True)
        """
        # Check concurrent session limit
        if len(self.active_sessions) >= self.max_concurrent_sessions:
            raise SessionLimitError(
                f"Maximum concurrent sessions limit reached: {self.max_concurrent_sessions}",
                current_count=len(self.active_sessions),
                max_limit=self.max_concurrent_sessions
            )
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        logger.info(
            f"Creating session {session_id}: profile={profile_name}, "
            f"headless={headless}, domain={domain}"
        )
        
        try:
            # Get profile path
            profile_path = self.profile_manager.get_or_create_profile(profile_name)
            
            # Create browser context with profile
            context = await self._browser.new_context(
                user_data_dir=str(profile_path),
                headless=headless,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            # Create page
            page = await context.new_page()
            
            # Create session object
            session = BrowserSession(
                session_id=session_id,
                profile_name=profile_name,
                domain=domain or "",
                playwright_context=context,
                playwright_page=page,
                created_at=datetime.now(),
                last_activity=datetime.now(),
                is_headless=headless,
                state=SessionState.ACTIVE
            )
            
            # Track session
            self.active_sessions[session_id] = session
            
            # Track domain mapping if provided
            if domain:
                self.domain_sessions[domain] = session_id
            
            logger.info(
                f"Session {session_id} created successfully "
                f"({len(self.active_sessions)}/{self.max_concurrent_sessions} active)"
            )
            
            return session
            
        except Exception as e:
            raise SessionError(
                f"Failed to create session with profile '{profile_name}'",
                session_id=session_id,
                operation="create"
            ) from e
    
    async def get_session_for_domain(
        self,
        domain: str
    ) -> Optional[BrowserSession]:
        """
        Get existing session for domain or None.
        
        Enables session reuse for the same domain to avoid unnecessary
        re-authentication and improve performance.
        
        Args:
            domain: Domain to look up (e.g., "example.com")
        
        Returns:
            BrowserSession if found and active, None otherwise
        
        **Validates: Requirements 8.5, 12.1**
        
        Example:
            >>> session = await manager.get_session_for_domain("example.com")
            >>> if session:
            ...     # Reuse existing session
            ...     page = session.playwright_page
            >>> else:
            ...     # Create new session
            ...     session = await manager.create_session(domain="example.com")
        """
        session_id = self.domain_sessions.get(domain)
        
        if not session_id:
            logger.debug(f"No session found for domain: {domain}")
            return None
        
        session = self.active_sessions.get(session_id)
        
        if not session:
            # Session was closed, remove from domain mapping
            del self.domain_sessions[domain]
            logger.debug(f"Session for domain {domain} was closed")
            return None
        
        # Check if session is in usable state
        if session.state in (SessionState.ACTIVE, SessionState.IDLE):
            # Update last activity
            session.last_activity = datetime.now()
            session.state = SessionState.ACTIVE
            
            logger.info(f"Reusing session {session_id} for domain: {domain}")
            return session
        else:
            logger.warning(
                f"Session {session_id} for domain {domain} is in state {session.state}, "
                "cannot reuse"
            )
            return None
    
    async def close_session(self, session_id: str) -> None:
        """
        Close a specific browser session.
        
        Closes the Playwright page and context, and removes the session
        from tracking.
        
        Args:
            session_id: ID of the session to close
        
        Raises:
            ValueError: If session_id doesn't exist
        
        **Validates: Requirement 8.1**
        
        Example:
            >>> await manager.close_session(session.session_id)
        """
        session = self.active_sessions.get(session_id)
        
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        logger.info(f"Closing session {session_id}")
        
        try:
            # Update state
            session.state = SessionState.CLOSING
            
            # Close page
            if session.playwright_page:
                await session.playwright_page.close()
            
            # Close context
            if session.playwright_context:
                await session.playwright_context.close()
            
            # Remove from tracking
            del self.active_sessions[session_id]
            
            # Remove from domain mapping
            if session.domain and self.domain_sessions.get(session.domain) == session_id:
                del self.domain_sessions[session.domain]
            
            logger.info(
                f"Session {session_id} closed successfully "
                f"({len(self.active_sessions)}/{self.max_concurrent_sessions} active)"
            )
            
        except Exception as e:
            logger.error(f"Error closing session {session_id}: {e}")
            # Still remove from tracking even if close fails
            self.active_sessions.pop(session_id, None)
            if session.domain:
                self.domain_sessions.pop(session.domain, None)
    
    async def close_idle_sessions(self) -> int:
        """
        Close sessions that have been idle for longer than idle_timeout.
        
        Automatically called by background cleanup task. Can also be called
        manually for immediate cleanup.
        
        Returns:
            Number of sessions closed
        
        **Validates: Requirements 8.3, 8.4**
        
        Example:
            >>> closed_count = await manager.close_idle_sessions()
            >>> print(f"Closed {closed_count} idle sessions")
        """
        now = datetime.now()
        idle_sessions = []
        
        # Find idle sessions
        for session_id, session in self.active_sessions.items():
            time_since_activity = now - session.last_activity
            
            if time_since_activity > self.idle_timeout:
                idle_sessions.append(session_id)
                logger.info(
                    f"Session {session_id} idle for {time_since_activity.total_seconds():.0f}s, "
                    "marking for closure"
                )
        
        # Close idle sessions
        for session_id in idle_sessions:
            try:
                await self.close_session(session_id)
            except Exception as e:
                logger.error(f"Error closing idle session {session_id}: {e}")
        
        if idle_sessions:
            logger.info(f"Closed {len(idle_sessions)} idle session(s)")
        
        return len(idle_sessions)
    
    async def restart_crashed_session(
        self,
        session_id: str
    ) -> BrowserSession:
        """
        Restart a crashed browser session.
        
        Creates a new session with the same profile and domain as the
        crashed session.
        
        Args:
            session_id: ID of the crashed session
        
        Returns:
            New BrowserSession object
        
        Raises:
            ValueError: If session doesn't exist or is not crashed
            SessionError: If restart fails
        
        **Validates: Requirements 8.6, 9.6**
        
        Example:
            >>> try:
            ...     # Use session
            ...     await page.goto("https://example.com")
            ... except Exception:
            ...     # Session crashed
            ...     session = await manager.restart_crashed_session(session.session_id)
        """
        session = self.active_sessions.get(session_id)
        
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        if session.state != SessionState.CRASHED:
            raise ValueError(
                f"Session {session_id} is not crashed (state: {session.state})"
            )
        
        logger.info(f"Restarting crashed session {session_id}")
        
        # Save session details
        profile_name = session.profile_name
        headless = session.is_headless
        domain = session.domain
        
        try:
            # Close crashed session
            await self.close_session(session_id)
        except Exception as e:
            logger.warning(f"Error closing crashed session: {e}")
        
        # Create new session
        try:
            new_session = await self.create_session(
                profile_name=profile_name,
                headless=headless,
                domain=domain if domain else None
            )
            
            logger.info(
                f"Session restarted successfully: old={session_id}, new={new_session.session_id}"
            )
            
            return new_session
            
        except Exception as e:
            raise SessionError(
                f"Failed to restart crashed session {session_id}",
                session_id=session_id,
                operation="restart"
            ) from e
    
    def mark_session_crashed(self, session_id: str) -> None:
        """
        Mark a session as crashed.
        
        Updates session state to CRASHED for later recovery.
        
        Args:
            session_id: ID of the crashed session
        
        **Validates: Requirement 9.6**
        """
        session = self.active_sessions.get(session_id)
        
        if session:
            session.state = SessionState.CRASHED
            logger.warning(f"Session {session_id} marked as CRASHED")
        else:
            logger.warning(f"Cannot mark non-existent session as crashed: {session_id}")
    
    def update_session_activity(self, session_id: str) -> None:
        """
        Update last activity timestamp for a session.
        
        Should be called after each action to prevent idle timeout.
        
        Args:
            session_id: ID of the session
        
        **Validates: Requirement 8.4**
        """
        session = self.active_sessions.get(session_id)
        
        if session:
            session.last_activity = datetime.now()
            
            # Update state to ACTIVE if it was IDLE
            if session.state == SessionState.IDLE:
                session.state = SessionState.ACTIVE
                logger.debug(f"Session {session_id} state changed: IDLE -> ACTIVE")
        else:
            logger.warning(f"Cannot update activity for non-existent session: {session_id}")
    
    def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """
        Get session by ID.
        
        Args:
            session_id: ID of the session
        
        Returns:
            BrowserSession if found, None otherwise
        """
        return self.active_sessions.get(session_id)
    
    def get_all_sessions(self) -> List[BrowserSession]:
        """
        Get all active sessions.
        
        Returns:
            List of all active BrowserSession objects
        
        **Validates: Requirement 8.3**
        """
        return list(self.active_sessions.values())
    
    def get_session_count(self) -> int:
        """
        Get count of active sessions.
        
        Returns:
            Number of active sessions
        """
        return len(self.active_sessions)
    
    async def _background_cleanup(self) -> None:
        """
        Background task to periodically clean up idle sessions.
        
        Runs every 60 seconds to check for idle sessions.
        
        **Validates: Requirements 8.3, 8.4**
        """
        logger.info("Background cleanup task started")
        
        try:
            while True:
                await asyncio.sleep(60)  # Check every minute
                
                try:
                    closed_count = await self.close_idle_sessions()
                    
                    if closed_count > 0:
                        logger.info(f"Background cleanup closed {closed_count} idle session(s)")
                    
                except Exception as e:
                    logger.error(f"Error in background cleanup: {e}")
                
        except asyncio.CancelledError:
            logger.info("Background cleanup task cancelled")
            raise
    
    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from URL.
        
        Args:
            url: Full URL
        
        Returns:
            Domain (e.g., "example.com")
        """
        parsed = urlparse(url)
        return parsed.netloc or parsed.path
    
    async def _create_warm_session(self) -> None:
        """
        Create a warm session in the pool for faster first request.
        
        **Validates: Requirement 12.1** - Warm session pool
        """
        async with self._warm_session_lock:
            if self._warm_session is not None:
                return  # Already have a warm session
            
            try:
                logger.info("Creating warm session for pool...")
                
                # Create a session without domain (generic)
                session = await self.create_session(
                    profile_name="default",
                    headless=True,
                    domain=None
                )
                
                self._warm_session = session
                logger.info(f"Warm session created: {session.session_id}")
                
            except Exception as e:
                logger.warning(f"Failed to create warm session: {e}")
                self._warm_session = None
    
    async def get_or_use_warm_session(
        self,
        profile_name: str = "default",
        headless: bool = True,
        domain: Optional[str] = None
    ) -> BrowserSession:
        """
        Get warm session from pool or create new one.
        
        If a warm session is available and matches requirements, use it.
        Otherwise, create a new session. After using warm session, create
        a new one for the pool.
        
        **Validates: Requirement 12.1** - Warm session pool for faster startup
        
        Args:
            profile_name: Profile name for the session
            headless: Whether to run headless
            domain: Optional domain for tracking
        
        Returns:
            BrowserSession (warm or newly created)
        """
        async with self._warm_session_lock:
            # Check if warm session is available and matches requirements
            if (self._warm_session and 
                self._warm_session.profile_name == profile_name and
                self._warm_session.is_headless == headless and
                self._warm_session.state == SessionState.ACTIVE):
                
                # Use warm session
                session = self._warm_session
                self._warm_session = None
                
                # Update domain if provided
                if domain:
                    session.domain = domain
                    self.domain_sessions[domain] = session.session_id
                
                logger.info(f"Using warm session {session.session_id} (instant startup)")
                
                # Create new warm session in background
                asyncio.create_task(self._create_warm_session())
                
                return session
            else:
                # Create new session normally
                logger.debug("Warm session not available or doesn't match requirements")
                return await self.create_session(profile_name, headless, domain)
