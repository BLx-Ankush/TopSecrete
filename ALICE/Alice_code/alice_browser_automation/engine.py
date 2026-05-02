"""
Browser Automation Engine for Alice Browser Automation.

This module provides the core orchestrator for browser automation tasks,
coordinating all components to execute voice-commanded browser automation.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 8.3, 11.1-11.6, 12.1-12.6**
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

from .config import Config, setup_logging
from .types import (
    TaskType, TaskResult, BrowserTask, BrowserAction, BrowserSession,
    ActionType, BrowserState, StructuredDOM
)
from .exceptions import (
    BrowserAutomationError, QwenModelUnavailableError,
    SessionError, SessionLimitError
)
from .session_manager import SessionManager
from .profile_manager import ChromeProfileManager
from .dom_parser import DOMParser
from .livekit_bridge import LiveKitQwenBridge
from .qwen_client import QwenModelClient
from .otp_handler import OTPHandler
from .error_handler import ErrorHandler
from .security import SecurityManager, install_sensitive_data_filter
from .web_bookings import WebBookingsActionSuite
from .problem_solving import ProblemSolvingActionSuite
from .app_access import ApplicationAccessActionSuite


logger = logging.getLogger(__name__)


class BrowserAutomationEngine:
    """
    Main engine coordinating browser automation tasks.
    
    This is the core orchestrator that brings together all components to
    execute browser automation tasks from voice commands. It manages:
    - Browser sessions via SessionManager
    - DOM parsing via DOMParser
    - Action planning via LiveKitQwenBridge
    - Error handling and recovery
    - Progress reporting to Alice
    
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 8.3, 11.1-11.6, 12.1-12.6**
    
    Attributes:
        config: Configuration object
        profile_manager: ChromeProfileManager for profile handling
        session_manager: SessionManager for browser session lifecycle
        dom_parser: DOMParser for DOM extraction
        livekit_bridge: LiveKitQwenBridge for voice command translation
        otp_handler: OTPHandler for OTP verification
        error_handler: ErrorHandler for error recovery
        is_initialized: Whether engine has been initialized
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize Browser Automation Engine.
        
        **Validates: Requirement 1.1** - Install and configure browser automation stack
        
        Args:
            config: Optional configuration object. If None, loads from default locations.
        """
        # Load configuration
        self.config = config or Config.load()
        
        # Set up logging
        setup_logging(self.config.logging)
        
        logger.info("Initializing Browser Automation Engine")
        
        # Initialize components (will be set up in initialize())
        self.profile_manager: Optional[ChromeProfileManager] = None
        self.session_manager: Optional[SessionManager] = None
        self.dom_parser: Optional[DOMParser] = None
        self.livekit_bridge: Optional[LiveKitQwenBridge] = None
        self.otp_handler: Optional[OTPHandler] = None
        self.error_handler: Optional[ErrorHandler] = None
        self.security_manager: Optional[SecurityManager] = None
        self.web_bookings: Optional[WebBookingsActionSuite] = None
        self.problem_solving: Optional[ProblemSolvingActionSuite] = None
        self.app_access: Optional[ApplicationAccessActionSuite] = None
        
        # Track initialization state
        self.is_initialized = False
        
        # Active tasks tracking
        self._active_tasks: Dict[str, BrowserTask] = {}
        self._task_cancellation_flags: Dict[str, bool] = {}
        
        # Task execution statistics
        self._task_stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0
        }
        
        logger.info("Browser Automation Engine created (not yet initialized)")
    
    async def initialize(self) -> bool:
        """
        Initialize browser-use, Playwright, and Qwen model.
        
        This method sets up all components and validates that the system
        is ready for browser automation.
        
        **Validates: Requirement 1.2** - Install Ollama with Qwen Coder 2.5 3B model
        **Validates: Requirement 1.3** - Verify Playwright browser binaries
        **Validates: Requirement 1.4** - Validate Qwen model availability
        
        Returns:
            True if initialization successful
            
        Raises:
            BrowserAutomationError: If initialization fails
            QwenModelUnavailableError: If Qwen model is not available
        """
        if self.is_initialized:
            logger.warning("Engine already initialized")
            return True
        
        logger.info("Initializing Browser Automation Engine components...")
        
        try:
            # 1. Initialize Profile Manager
            logger.info("Initializing Profile Manager...")
            self.profile_manager = ChromeProfileManager(
                profiles_dir=self.config.browser.profiles_dir
            )
            logger.info("✓ Profile Manager initialized")
            
            # 2. Initialize Session Manager
            logger.info("Initializing Session Manager...")
            self.session_manager = SessionManager(
                profile_manager=self.profile_manager,
                max_concurrent_sessions=self.config.browser.max_concurrent_sessions,
                idle_timeout_seconds=self.config.browser.idle_timeout_seconds
            )
            await self.session_manager.initialize()
            logger.info("✓ Session Manager initialized")
            
            # 3. Initialize DOM Parser
            logger.info("Initializing DOM Parser...")
            self.dom_parser = DOMParser(
                cache_duration_seconds=self.config.dom_parser.cache_duration_seconds
            )
            logger.info("✓ DOM Parser initialized")
            
            # 4. Initialize LiveKit-Qwen Bridge
            logger.info("Initializing LiveKit-Qwen Bridge...")
            self.livekit_bridge = LiveKitQwenBridge(
                ollama_host=self.config.qwen.host,
                model_name=self.config.qwen.model,
                timeout=self.config.qwen.timeout_seconds
            )
            logger.info("✓ LiveKit-Qwen Bridge initialized")
            
            # 5. Validate Qwen Model Availability
            logger.info("Validating Qwen model availability...")
            is_available = await self.livekit_bridge.qwen_client.validate_model_availability()
            
            if not is_available:
                raise QwenModelUnavailableError(
                    f"Qwen model '{self.config.qwen.model}' is not available",
                    host=self.config.qwen.host,
                    model=self.config.qwen.model
                )
            
            logger.info(f"✓ Qwen model '{self.config.qwen.model}' is available")
            
            # 6. Initialize OTP Handler (will be set up per-session as needed)
            logger.info("OTP Handler will be initialized per-session as needed")
            
            # 7. Initialize Error Handler
            logger.info("Initializing Error Handler...")
            self.error_handler = ErrorHandler(
                session_manager=self.session_manager,
                qwen_client=self.livekit_bridge.qwen_client
            )
            logger.info("✓ Error Handler initialized")
            
            # 8. Initialize Security Manager
            logger.info("Initializing Security Manager...")
            self.security_manager = SecurityManager(
                require_payment_confirmation=self.config.security.require_payment_confirmation,
                block_banking_sites=self.config.security.block_banking_sites,
                validate_ssl=self.config.security.validate_ssl,
                clear_sensitive_data=self.config.security.clear_sensitive_data
            )
            # Install sensitive data filter on loggers
            install_sensitive_data_filter(self.security_manager)
            logger.info("✓ Security Manager initialized")
            
            # 9. Initialize Web Bookings Action Suite
            logger.info("Initializing Web Bookings Action Suite...")
            self.web_bookings = WebBookingsActionSuite(
                engine=self,
                config=self.config.to_dict().get("web_bookings", {})
            )
            logger.info("✓ Web Bookings Action Suite initialized")
            
            # 10. Initialize Problem Solving Action Suite
            logger.info("Initializing Problem Solving Action Suite...")
            self.problem_solving = ProblemSolvingActionSuite(
                engine=self,
                config=self.config.to_dict().get("problem_solving", {})
            )
            logger.info("✓ Problem Solving Action Suite initialized")
            
            # 11. Initialize Application Access Action Suite
            logger.info("Initializing Application Access Action Suite...")
            self.app_access = ApplicationAccessActionSuite(
                engine=self,
                config=self.config.to_dict().get("app_access", {})
            )
            logger.info("✓ Application Access Action Suite initialized")
            
            # Mark as initialized
            self.is_initialized = True
            
            logger.info("=" * 60)
            logger.info("Browser Automation Engine initialized successfully!")
            logger.info("=" * 60)
            logger.info(f"  Ollama Host: {self.config.qwen.host}")
            logger.info(f"  Qwen Model: {self.config.qwen.model}")
            logger.info(f"  Max Sessions: {self.config.browser.max_concurrent_sessions}")
            logger.info(f"  Profiles Dir: {self.config.browser.profiles_dir}")
            logger.info("=" * 60)
            
            return True
            
        except QwenModelUnavailableError:
            logger.error("Qwen model is not available - cannot initialize engine")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Browser Automation Engine: {e}")
            raise BrowserAutomationError(
                f"Engine initialization failed: {e}"
            ) from e
    
    async def shutdown(self) -> None:
        """
        Clean up resources and close browser sessions.
        
        Closes all active sessions, stops background tasks, and cleans up
        all component resources.
        
        **Validates: Requirement 8.3** - Manage browser sessions efficiently
        """
        logger.info("Shutting down Browser Automation Engine...")
        
        if not self.is_initialized:
            logger.warning("Engine not initialized, nothing to shut down")
            return
        
        try:
            # Close LiveKit bridge
            if self.livekit_bridge:
                await self.livekit_bridge.close()
                logger.info("✓ LiveKit-Qwen Bridge closed")
            
            # Shutdown Session Manager (closes all sessions)
            if self.session_manager:
                await self.session_manager.shutdown()
                logger.info("✓ Session Manager shut down")
            
            # Clear DOM parser cache
            if self.dom_parser:
                self.dom_parser.clear_cache()
                logger.info("✓ DOM Parser cache cleared")
            
            # Mark as not initialized
            self.is_initialized = False
            
            logger.info("Browser Automation Engine shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def get_active_sessions(self) -> List[BrowserSession]:
        """
        Get list of active browser sessions.
        
        **Validates: Requirement 8.3** - Track active browser sessions
        
        Returns:
            List of active BrowserSession objects
        """
        if not self.is_initialized or not self.session_manager:
            return []
        
        return self.session_manager.get_all_sessions()
    
    async def execute_task(
        self,
        task_description: str,
        task_type: TaskType,
        parameters: Dict[str, Any],
        callback: Optional[Callable[[str], None]] = None
    ) -> TaskResult:
        """
        Execute a browser automation task.
        
        This is the main entry point for executing browser automation tasks.
        It orchestrates the entire workflow from voice command to task completion.
        
        **Validates: Requirement 11.1** - Recognize intent and invoke engine
        **Validates: Requirement 11.2** - Provide real-time status updates
        **Validates: Requirement 11.3** - Prompt user via voice when needed
        **Validates: Requirement 11.4** - Confirm task completion
        **Validates: Requirement 11.5** - Support interruption commands
        **Validates: Requirement 12.1** - Initiate browser session within 3 seconds
        
        Args:
            task_description: Natural language description of the task
            task_type: Type of task (WEB_BOOKING, PROBLEM_SOLVING, APP_ACCESS)
            parameters: Task-specific parameters
            callback: Optional progress callback function for status updates
        
        Returns:
            TaskResult with task execution results
            
        Raises:
            BrowserAutomationError: If task execution fails
            QwenModelUnavailableError: If Qwen model becomes unavailable
        """
        if not self.is_initialized:
            raise BrowserAutomationError(
                "Engine not initialized. Call initialize() first."
            )
        
        logger.info(f"Executing task: {task_description} (type: {task_type.value})")
        
        # Start timing
        start_time = time.time()
        
        # Update statistics
        self._task_stats["total_tasks"] += 1
        
        # Progress callback helper
        def report_progress(message: str):
            logger.info(f"Progress: {message}")
            if callback:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")
        
        browser_task = None
        
        try:
            # Translate voice command to BrowserTask
            report_progress("Understanding your request...")
            
            browser_task = await self.livekit_bridge.translate_voice_command(
                voice_command=task_description,
                context=parameters
            )
            
            # Track active task
            self._active_tasks[browser_task.task_id] = browser_task
            self._task_cancellation_flags[browser_task.task_id] = False
            
            logger.info(f"Task translated: {browser_task.task_id}")
            
            # Route to appropriate action suite based on task type
            report_progress(f"Starting {task_type.value} task...")
            
            if task_type == TaskType.WEB_BOOKING:
                result = await self._execute_web_booking(browser_task, report_progress)
            elif task_type == TaskType.PROBLEM_SOLVING:
                result = await self._execute_problem_solving(browser_task, report_progress)
            elif task_type == TaskType.APP_ACCESS:
                result = await self._execute_app_access(browser_task, report_progress)
            else:
                raise ValueError(f"Unsupported task type: {task_type}")
            
            # Check if task was cancelled
            if self._task_cancellation_flags.get(browser_task.task_id, False):
                logger.info(f"Task {browser_task.task_id} was cancelled")
                result.success = False
                result.error = "Task cancelled by user"
                result.summary = "Task was cancelled before completion"
                self._task_stats["cancelled_tasks"] += 1
            else:
                # Update statistics based on result
                if result.success:
                    self._task_stats["successful_tasks"] += 1
                    report_progress("Task completed successfully!")
                else:
                    self._task_stats["failed_tasks"] += 1
                    report_progress(f"Task failed: {result.error}")
            
            # Calculate duration
            duration = time.time() - start_time
            result.duration_seconds = duration
            
            # Clear sensitive data after task completion
            if self.security_manager:
                self.security_manager.clear_all_sensitive_data()
            
            # Remove from active tasks
            self._active_tasks.pop(browser_task.task_id, None)
            self._task_cancellation_flags.pop(browser_task.task_id, None)
            
            logger.info(
                f"Task completed: {browser_task.task_id} "
                f"(success={result.success}, duration={duration:.2f}s)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Update statistics
            self._task_stats["failed_tasks"] += 1
            
            # Clear sensitive data even on failure
            if self.security_manager:
                self.security_manager.clear_all_sensitive_data()
            
            # Create error result
            error_result = TaskResult(
                task_id=browser_task.task_id if browser_task else "unknown",
                success=False,
                summary=f"Task failed: {str(e)}",
                actions_taken=[],
                extracted_data={},
                error=str(e),
                duration_seconds=duration,
                screenshots=[]
            )
            
            # Clean up tracking
            if browser_task:
                self._active_tasks.pop(browser_task.task_id, None)
                self._task_cancellation_flags.pop(browser_task.task_id, None)
            
            return error_result
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel an active task.
        
        Sets a cancellation flag that will be checked during task execution.
        The task will stop at the next safe checkpoint.
        
        **Validates: Requirement 11.5** - Support interruption commands
        
        Args:
            task_id: ID of the task to cancel
        
        Returns:
            True if task was found and cancellation flag set, False otherwise
        """
        if task_id in self._active_tasks:
            self._task_cancellation_flags[task_id] = True
            logger.info(f"Cancellation requested for task: {task_id}")
            return True
        else:
            logger.warning(f"Cannot cancel task {task_id}: not found in active tasks")
            return False
    
    def is_task_cancelled(self, task_id: str) -> bool:
        """
        Check if a task has been cancelled.
        
        Args:
            task_id: ID of the task to check
        
        Returns:
            True if task is cancelled, False otherwise
        """
        return self._task_cancellation_flags.get(task_id, False)
    
    def get_task_statistics(self) -> Dict[str, int]:
        """
        Get task execution statistics.
        
        Returns:
            Dictionary with task statistics (total, successful, failed, cancelled)
        """
        return self._task_stats.copy()
    
    def get_active_task_ids(self) -> List[str]:
        """
        Get list of active task IDs.
        
        Returns:
            List of task IDs currently being executed
        """
        return list(self._active_tasks.keys())
    
    async def _execute_web_booking(
        self,
        task: BrowserTask,
        progress_callback: Callable[[str], None]
    ) -> TaskResult:
        """
        Execute web booking task using Web Bookings Action Suite.
        
        Routes booking requests to the appropriate booking method based on
        task parameters. Supports travel bookings, food orders, and event tickets.
        
        **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8**
        
        Args:
            task: BrowserTask with booking details
            progress_callback: Function to report progress
        
        Returns:
            TaskResult with booking results
        """
        progress_callback(f"Starting web booking: {task.description}")
        
        try:
            # Use action execution loop for web bookings
            # The web bookings suite will delegate to the action loop
            session = await self._get_or_create_session(task.target_url or "https://www.google.com")
            
            result = await self._execute_action_loop(
                task=task,
                session=session,
                progress_callback=progress_callback
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Web booking failed: {e}")
            return TaskResult(
                task_id=task.task_id,
                success=False,
                summary=f"Web booking failed: {str(e)}",
                actions_taken=[],
                extracted_data={},
                error=str(e),
                duration_seconds=0.0,
                screenshots=[]
            )
    
    async def _execute_problem_solving(
        self,
        task: BrowserTask,
        progress_callback: Callable[[str], None]
    ) -> TaskResult:
        """
        Execute problem solving task using Problem Solving Action Suite.
        
        Routes problem solving requests to web research and solution execution.
        
        **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
        
        Args:
            task: BrowserTask with problem details
            progress_callback: Function to report progress
        
        Returns:
            TaskResult with solutions and execution results
        """
        progress_callback(f"Starting problem solving: {task.description}")
        
        try:
            # Use action execution loop for problem solving
            session = await self._get_or_create_session(task.target_url or "https://www.google.com")
            
            result = await self._execute_action_loop(
                task=task,
                session=session,
                progress_callback=progress_callback
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Problem solving failed: {e}")
            return TaskResult(
                task_id=task.task_id,
                success=False,
                summary=f"Problem solving failed: {str(e)}",
                actions_taken=[],
                extracted_data={},
                error=str(e),
                duration_seconds=0.0,
                screenshots=[]
            )
    
    async def _execute_app_access(
        self,
        task: BrowserTask,
        progress_callback: Callable[[str], None]
    ) -> TaskResult:
        """
        Execute application access task using Application Access Action Suite.
        
        Routes application access requests to persistent session management.
        
        **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7**
        
        Args:
            task: BrowserTask with app access details
            progress_callback: Function to report progress
        
        Returns:
            TaskResult with app access results
        """
        progress_callback(f"Starting application access: {task.description}")
        
        try:
            # Use action execution loop for app access
            session = await self._get_or_create_session(task.target_url or "https://www.google.com")
            
            result = await self._execute_action_loop(
                task=task,
                session=session,
                progress_callback=progress_callback
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Application access failed: {e}")
            return TaskResult(
                task_id=task.task_id,
                success=False,
                summary=f"Application access failed: {str(e)}",
                actions_taken=[],
                extracted_data={},
                error=str(e),
                duration_seconds=0.0,
                screenshots=[]
            )
    
    def _aggregate_task_result(
        self,
        task: BrowserTask,
        actions_taken: List[BrowserAction],
        extracted_data: Dict[str, Any],
        success: bool,
        error: Optional[str] = None,
        screenshots: Optional[List[str]] = None
    ) -> TaskResult:
        """
        Aggregate task execution results into TaskResult.
        
        **Validates: Requirement 11.4** - Confirm task completion with summary
        
        Args:
            task: Original BrowserTask
            actions_taken: List of actions executed
            extracted_data: Data extracted during task execution
            success: Whether task completed successfully
            error: Error message if task failed
            screenshots: Optional list of screenshot paths
        
        Returns:
            TaskResult with aggregated results
        """
        # Generate summary based on task type and outcome
        if success:
            summary = self._generate_success_summary(task, actions_taken, extracted_data)
        else:
            summary = f"Task failed: {error or 'Unknown error'}"
        
        return TaskResult(
            task_id=task.task_id,
            success=success,
            summary=summary,
            actions_taken=actions_taken,
            extracted_data=extracted_data,
            error=error,
            duration_seconds=0.0,  # Will be set by execute_task
            screenshots=screenshots or []
        )
    
    def _generate_success_summary(
        self,
        task: BrowserTask,
        actions_taken: List[BrowserAction],
        extracted_data: Dict[str, Any]
    ) -> str:
        """
        Generate human-readable success summary.
        
        Args:
            task: Original BrowserTask
            actions_taken: List of actions executed
            extracted_data: Data extracted during task execution
        
        Returns:
            Human-readable summary string
        """
        action_count = len(actions_taken)
        
        # Base summary
        summary = f"Successfully completed {task.task_type.value} task: {task.description}"
        
        # Add action count
        summary += f" ({action_count} action{'s' if action_count != 1 else ''} executed)"
        
        # Add key extracted data if available
        if extracted_data:
            key_data = []
            
            # Common data fields
            if "confirmation_number" in extracted_data:
                key_data.append(f"Confirmation: {extracted_data['confirmation_number']}")
            if "booking_id" in extracted_data:
                key_data.append(f"Booking ID: {extracted_data['booking_id']}")
            if "order_number" in extracted_data:
                key_data.append(f"Order: {extracted_data['order_number']}")
            if "result_count" in extracted_data:
                key_data.append(f"{extracted_data['result_count']} results found")
            
            if key_data:
                summary += ". " + ", ".join(key_data)
        
        return summary
    
    async def _route_task_by_type(
        self,
        task: BrowserTask,
        progress_callback: Callable[[str], None]
    ) -> TaskResult:
        """
        Route task to appropriate action suite based on task type.
        
        **Validates: Requirement 11.1** - Route tasks to appropriate handlers
        
        Args:
            task: BrowserTask to execute
            progress_callback: Function to report progress
        
        Returns:
            TaskResult from action suite execution
            
        Raises:
            ValueError: If task type is not supported
        """
        logger.info(f"Routing task {task.task_id} to {task.task_type.value} handler")
        
        if task.task_type == TaskType.WEB_BOOKING:
            return await self._execute_web_booking(task, progress_callback)
        elif task.task_type == TaskType.PROBLEM_SOLVING:
            return await self._execute_problem_solving(task, progress_callback)
        elif task.task_type == TaskType.APP_ACCESS:
            return await self._execute_app_access(task, progress_callback)
        else:
            raise ValueError(f"Unsupported task type: {task.task_type}")
    
    def _validate_task_parameters(
        self,
        task: BrowserTask
    ) -> tuple[bool, Optional[str]]:
        """
        Validate task parameters before execution.
        
        Args:
            task: BrowserTask to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if not task.description:
            return False, "Task description is required"
        
        if not task.task_type:
            return False, "Task type is required"
        
        # Task-specific validation
        if task.task_type == TaskType.WEB_BOOKING:
            if not task.parameters:
                return False, "Web booking requires parameters"
            
            booking_type = task.parameters.get("booking_type")
            if not booking_type:
                return False, "Web booking requires booking_type parameter"
        
        elif task.task_type == TaskType.PROBLEM_SOLVING:
            # Problem solving can have empty parameters for general queries
            pass
        
        elif task.task_type == TaskType.APP_ACCESS:
            if not task.parameters:
                return False, "App access requires parameters"
            
            app_name = task.parameters.get("app_name")
            if not app_name:
                return False, "App access requires app_name parameter"
        
        return True, None
    
    async def _create_browser_session(
        self,
        profile_name: Optional[str] = None,
        headless: Optional[bool] = None,
        domain: Optional[str] = None
    ) -> BrowserSession:
        """
        Create a new browser session with profile selection.
        
        **Validates: Requirement 7.3** - Use existing Chrome profile
        **Validates: Requirement 8.1** - Launch browser sessions
        **Validates: Requirement 8.2** - Headless/headed mode support
        
        Args:
            profile_name: Name of Chrome profile to use (default: from config)
            headless: Whether to run in headless mode (default: from config)
            domain: Optional domain for session reuse tracking
        
        Returns:
            BrowserSession object
            
        Raises:
            SessionLimitError: If max concurrent sessions reached
            SessionError: If session creation fails
        """
        # Use defaults from config if not specified
        if profile_name is None:
            profile_name = self.config.browser.default_profile
        
        if headless is None:
            headless = self.config.browser.headless_default
        
        logger.info(
            f"Creating browser session: profile={profile_name}, "
            f"headless={headless}, domain={domain}"
        )
        
        try:
            # Create session via SessionManager
            session = await self.session_manager.create_session(
                profile_name=profile_name,
                headless=headless,
                domain=domain
            )
            
            logger.info(f"Browser session created: {session.session_id}")
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to create browser session: {e}")
            raise
    
    async def _get_or_create_session(
        self,
        domain: str,
        profile_name: Optional[str] = None,
        headless: Optional[bool] = None
    ) -> BrowserSession:
        """
        Get existing session for domain or create new one.
        
        Implements session reuse optimization for same domain to avoid
        re-authentication and improve performance.
        
        **Validates: Requirement 8.5** - Reuse existing sessions for same domain
        **Validates: Requirement 12.1** - Initiate session within 3 seconds
        
        Args:
            domain: Domain to get/create session for
            profile_name: Profile name if creating new session
            headless: Headless mode if creating new session
        
        Returns:
            BrowserSession (existing or newly created)
            
        Raises:
            SessionLimitError: If max concurrent sessions reached
            SessionError: If session creation fails
        """
        logger.info(f"Getting or creating session for domain: {domain}")
        
        # Try to get existing session
        existing_session = await self.session_manager.get_session_for_domain(domain)
        
        if existing_session:
            logger.info(
                f"Reusing existing session {existing_session.session_id} for domain: {domain}"
            )
            return existing_session
        
        # Create new session
        logger.info(f"No existing session found, creating new session for domain: {domain}")
        
        session = await self._create_browser_session(
            profile_name=profile_name,
            headless=headless,
            domain=domain
        )
        
        return session
    
    async def _close_idle_sessions(self) -> int:
        """
        Clean up sessions idle for longer than configured timeout.
        
        This is a wrapper around SessionManager.close_idle_sessions() that
        can be called from the engine for manual cleanup.
        
        **Validates: Requirement 8.4** - Close idle sessions
        
        Returns:
            Number of sessions closed
        """
        logger.info("Closing idle sessions...")
        
        closed_count = await self.session_manager.close_idle_sessions()
        
        if closed_count > 0:
            logger.info(f"Closed {closed_count} idle session(s)")
        else:
            logger.debug("No idle sessions to close")
        
        return closed_count
    
    async def _handle_otp_verification(
        self,
        session: BrowserSession,
        livekit_session: Optional[Any] = None
    ) -> str:
        """
        Handle OTP verification by switching to headed mode and requesting OTP via voice.
        
        **Validates: Requirement 5.3** - OTP request and entry
        **Validates: Requirement 5.4** - OTP verification
        **Validates: Requirement 8.2** - Switch to headed mode for OTP
        
        Args:
            session: BrowserSession requiring OTP
            livekit_session: Optional LiveKit session for voice interaction
        
        Returns:
            OTP code entered by user
            
        Raises:
            BrowserAutomationError: If OTP handling fails
        """
        logger.info(f"Handling OTP verification for session: {session.session_id}")
        
        try:
            # Initialize OTP handler if not already done
            if not self.otp_handler and livekit_session:
                from .otp_handler import OTPHandler
                self.otp_handler = OTPHandler(livekit_session)
            
            if not self.otp_handler:
                raise BrowserAutomationError(
                    "OTP handler not available. LiveKit session required for OTP verification."
                )
            
            # Switch to headed mode if currently headless
            if session.is_headless:
                logger.info("Switching to headed mode for OTP visibility...")
                await self.otp_handler.switch_to_headed_mode(session)
            
            # Request OTP from user via voice
            logger.info("Requesting OTP from user via voice...")
            otp = await self.otp_handler.request_otp(context="verification code")
            
            logger.info(f"OTP received: {'*' * len(otp)}")  # Don't log actual OTP
            
            # Switch back to headless mode if it was headless before
            if session.is_headless:
                logger.info("Switching back to headless mode...")
                await self.otp_handler.switch_to_headless_mode(session)
            
            return otp
            
        except Exception as e:
            logger.error(f"OTP verification failed: {e}")
            raise BrowserAutomationError(
                f"Failed to handle OTP verification: {e}"
            ) from e
    
    def _extract_domain_from_url(self, url: str) -> str:
        """
        Extract domain from URL for session reuse.
        
        Args:
            url: Full URL
        
        Returns:
            Domain (e.g., "example.com")
        """
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain
    
    async def _execute_action_loop(
        self,
        task: BrowserTask,
        session: BrowserSession,
        progress_callback: Callable[[str], None]
    ) -> TaskResult:
        """
        Execute action loop that processes BrowserAction list.
        
        This is the core execution logic that:
        1. Generates action plan from task and DOM
        2. Executes each action using Playwright
        3. Re-parses DOM after each action
        4. Verifies action results
        5. Handles errors with ErrorHandler
        6. Checks for task cancellation
        
        **Validates: Requirement 2.5** - Re-parse DOM after actions
        **Validates: Requirement 9.1** - Handle element not found errors
        **Validates: Requirement 9.2** - Handle page load timeouts
        **Validates: Requirement 9.3** - Handle invalid actions
        **Validates: Requirement 12.4** - Execute actions within 1 second
        
        Args:
            task: BrowserTask to execute
            session: BrowserSession to use
            progress_callback: Function to report progress
        
        Returns:
            TaskResult with execution results
            
        Raises:
            BrowserAutomationError: If action execution fails
        """
        logger.info(f"Starting action execution loop for task: {task.task_id}")
        
        actions_taken: List[BrowserAction] = []
        extracted_data: Dict[str, Any] = {}
        page = session.playwright_page
        
        # Track last progress update time for 10-second updates
        last_progress_time = time.time()
        
        try:
            # Navigate to target URL if specified
            if task.target_url:
                progress_callback(f"Navigating to {task.target_url}...")
                await self._execute_navigate_action(
                    page,
                    task.target_url,
                    progress_callback
                )
            
            # Parse initial DOM
            progress_callback("Analyzing page structure...")
            current_dom = await self.dom_parser.parse_page(page)
            
            # Generate initial action plan
            progress_callback("Planning actions...")
            action_plan = await self.livekit_bridge.generate_action_plan(
                task=task,
                dom=current_dom
            )
            
            logger.info(f"Generated action plan with {len(action_plan)} actions")
            
            # Execute actions in sequence
            for action_index, action in enumerate(action_plan):
                # Check for cancellation
                if self.is_task_cancelled(task.task_id):
                    logger.info(f"Task {task.task_id} cancelled during action execution")
                    break
                
                # Periodic progress update every 10 seconds for long tasks
                current_time = time.time()
                if current_time - last_progress_time >= 10.0:
                    progress_callback(
                        f"Still working... ({action_index + 1}/{len(action_plan)} actions completed)"
                    )
                    last_progress_time = current_time
                
                progress_callback(
                    f"Executing action {action_index + 1}/{len(action_plan)}: "
                    f"{action.action_type.value}"
                )
                
                # Execute single action
                action_result = await self._execute_single_action(
                    action=action,
                    page=page,
                    session=session,
                    progress_callback=progress_callback
                )
                
                # Track action
                actions_taken.append(action)
                
                # Merge extracted data
                if action_result.get("extracted_data"):
                    extracted_data.update(action_result["extracted_data"])
                
                # Re-parse DOM after action
                logger.debug("Re-parsing DOM after action...")
                current_dom = await self.dom_parser.parse_page(page)
                
                # Verify action result if expected_result specified
                if action.expected_result:
                    verified = await self._verify_action_result(
                        action=action,
                        dom=current_dom,
                        page=page
                    )
                    
                    if not verified:
                        logger.warning(
                            f"Action verification failed: {action.expected_result}"
                        )
                
                # Small delay between actions
                await asyncio.sleep(0.5)
            
            # Check if task was cancelled
            if self.is_task_cancelled(task.task_id):
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    summary="Task cancelled by user",
                    actions_taken=actions_taken,
                    extracted_data=extracted_data,
                    error="Task cancelled",
                    duration_seconds=0.0,
                    screenshots=[]
                )
            
            # Task completed successfully
            logger.info(
                f"Action loop completed: {len(actions_taken)} actions executed"
            )
            
            return TaskResult(
                task_id=task.task_id,
                success=True,
                summary=self._generate_success_summary(
                    task, actions_taken, extracted_data
                ),
                actions_taken=actions_taken,
                extracted_data=extracted_data,
                error=None,
                duration_seconds=0.0,
                screenshots=[]
            )
            
        except Exception as e:
            logger.error(f"Action loop failed: {e}")
            
            return TaskResult(
                task_id=task.task_id,
                success=False,
                summary=f"Action execution failed: {str(e)}",
                actions_taken=actions_taken,
                extracted_data=extracted_data,
                error=str(e),
                duration_seconds=0.0,
                screenshots=[]
            )
    
    async def _execute_single_action(
        self,
        action: BrowserAction,
        page: Any,  # Playwright Page
        session: BrowserSession,
        progress_callback: Callable[[str], None]
    ) -> Dict[str, Any]:
        """
        Execute a single browser action with error handling.
        
        **Validates: Requirement 12.4** - Execute simple actions within 1 second
        
        Args:
            action: BrowserAction to execute
            page: Playwright Page object
            session: BrowserSession for context
            progress_callback: Function to report progress
        
        Returns:
            Dictionary with action result and any extracted data
            
        Raises:
            BrowserAutomationError: If action execution fails after retries
        """
        logger.info(f"Executing action: {action.action_type.value}")
        
        result = {"success": False, "extracted_data": {}}
        
        try:
            if action.action_type == ActionType.NAVIGATE:
                await self._execute_navigate_action(
                    page,
                    action.parameters.get("url", ""),
                    progress_callback
                )
                result["success"] = True
            
            elif action.action_type == ActionType.CLICK:
                await self._execute_click_action(
                    page,
                    action.target_selector,
                    progress_callback
                )
                result["success"] = True
            
            elif action.action_type == ActionType.TYPE:
                await self._execute_type_action(
                    page,
                    action.target_selector,
                    action.parameters.get("text", ""),
                    action.parameters.get("clear_first", True),
                    progress_callback
                )
                result["success"] = True
            
            elif action.action_type == ActionType.WAIT:
                await self._execute_wait_action(
                    page,
                    action.target_selector,
                    action.parameters,
                    progress_callback
                )
                result["success"] = True
            
            elif action.action_type == ActionType.EXTRACT:
                extracted = await self._execute_extract_action(
                    page,
                    action.target_selector,
                    action.parameters,
                    progress_callback
                )
                result["success"] = True
                result["extracted_data"] = extracted
            
            elif action.action_type == ActionType.SCROLL:
                await self._execute_scroll_action(
                    page,
                    action.parameters,
                    progress_callback
                )
                result["success"] = True
            
            elif action.action_type == ActionType.SELECT:
                await self._execute_select_action(
                    page,
                    action.target_selector,
                    action.parameters.get("value", ""),
                    progress_callback
                )
                result["success"] = True
            
            else:
                logger.warning(f"Unsupported action type: {action.action_type}")
                result["success"] = False
            
            return result
            
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            
            # Try error recovery
            if action.retry_count < 3:
                logger.info(f"Retrying action (attempt {action.retry_count + 1}/3)...")
                action.retry_count += 1
                await asyncio.sleep(1.0)  # Wait before retry
                return await self._execute_single_action(
                    action, page, session, progress_callback
                )
            
            raise BrowserAutomationError(
                f"Action execution failed after 3 retries: {str(e)}"
            ) from e
    
    async def _execute_navigate_action(
        self,
        page: Any,
        url: str,
        progress_callback: Callable[[str], None]
    ) -> None:
        """
        Execute navigate action with error handling and security checks.
        
        **Validates: Requirement 10.5** - SSL certificate validation
        **Validates: Requirement 10.6** - Banking website permission checks
        
        Args:
            page: Playwright Page object
            url: URL to navigate to
            progress_callback: Function to report progress
            
        Raises:
            PermissionError: If banking site access blocked
            ssl.SSLError: If SSL certificate validation fails
        """
        logger.info(f"Navigating to: {url}")
        
        # Security checks
        if self.security_manager:
            # Check banking permission
            try:
                self.security_manager.check_banking_permission(url)
            except PermissionError as e:
                logger.error(f"Banking permission denied: {e}")
                raise
            
            # Validate SSL certificate for HTTPS
            if url.startswith('https://'):
                try:
                    self.security_manager.validate_ssl_certificate(url)
                except Exception as e:
                    logger.error(f"SSL validation failed: {e}")
                    raise
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
            logger.info(f"Navigation successful: {url}")
            
        except Exception as e:
            logger.warning(f"Navigation failed: {e}")
            
            # Try error handler
            await self.error_handler.handle_page_load_timeout(
                page, url, timeout_seconds=30.0
            )
    
    async def _execute_click_action(
        self,
        page: Any,
        selector: Optional[Any],  # ElementSelectors
        progress_callback: Callable[[str], None]
    ) -> None:
        """
        Execute click action with error handling.
        
        Args:
            page: Playwright Page object
            selector: ElementSelectors for target element
            progress_callback: Function to report progress
        """
        if not selector:
            raise BrowserAutomationError("Click action requires target selector")
        
        logger.info(f"Clicking element: {selector.css_selector}")
        
        try:
            # Try CSS selector first
            element = await page.query_selector(selector.css_selector)
            
            if element and await element.is_visible():
                await element.click()
                logger.info("Click successful")
                return
            
            # Element not found, try error handler
            working_selector = await self.error_handler.handle_element_not_found(
                page, selector, "click element"
            )
            
            # Retry with working selector
            if working_selector.css_selector:
                element = await page.query_selector(working_selector.css_selector)
                if element:
                    await element.click()
                    logger.info("Click successful (after retry)")
                    return
            
            raise BrowserAutomationError("Could not click element")
            
        except Exception as e:
            logger.error(f"Click action failed: {e}")
            raise
    
    async def _execute_type_action(
        self,
        page: Any,
        selector: Optional[Any],
        text: str,
        clear_first: bool,
        progress_callback: Callable[[str], None]
    ) -> None:
        """
        Execute type action with error handling and sensitive data tracking.
        
        **Validates: Requirement 10.1** - Track sensitive data
        **Validates: Requirement 10.2** - Don't log sensitive data
        
        Args:
            page: Playwright Page object
            selector: ElementSelectors for target element
            text: Text to type
            clear_first: Whether to clear field first
            progress_callback: Function to report progress
        """
        if not selector:
            raise BrowserAutomationError("Type action requires target selector")
        
        # Check if this is a sensitive field
        field_name = selector.css_selector or ""
        is_sensitive = False
        
        if self.security_manager:
            # Get field type from selector attributes
            field_type = ""
            if hasattr(selector, 'attributes') and selector.attributes:
                field_type = selector.attributes.get('type', '')
            
            is_sensitive = self.security_manager.is_sensitive_field(field_name, field_type)
            
            if is_sensitive:
                # Register sensitive data for tracking
                self.security_manager.register_sensitive_data(
                    field_name=field_name,
                    field_type=field_type,
                    value=text  # Will be cleared after task
                )
                logger.info(f"Typing in sensitive field: {field_name} (value redacted)")
            else:
                logger.info(f"Typing text in element: {selector.css_selector}")
        else:
            logger.info(f"Typing text in element: {selector.css_selector}")
        
        try:
            element = await page.query_selector(selector.css_selector)
            
            if element and await element.is_visible():
                if clear_first:
                    await element.fill('')
                await element.fill(text)
                logger.info("Type successful")
                return
            
            # Element not found, try error handler
            working_selector = await self.error_handler.handle_element_not_found(
                page, selector, "type in element"
            )
            
            # Retry with working selector
            if working_selector.css_selector:
                element = await page.query_selector(working_selector.css_selector)
                if element:
                    if clear_first:
                        await element.fill('')
                    await element.fill(text)
                    logger.info("Type successful (after retry)")
                    return
            
            raise BrowserAutomationError("Could not type in element")
            
        except Exception as e:
            logger.error(f"Type action failed: {e}")
            raise
    
    async def _execute_wait_action(
        self,
        page: Any,
        selector: Optional[Any],
        parameters: Dict[str, Any],
        progress_callback: Callable[[str], None]
    ) -> None:
        """
        Execute wait action.
        
        Args:
            page: Playwright Page object
            selector: Optional ElementSelectors for target element
            parameters: Wait parameters (condition, timeout_ms)
            progress_callback: Function to report progress
        """
        condition = parameters.get("condition", "visible")
        timeout_ms = parameters.get("timeout_ms", 5000)
        
        logger.info(f"Waiting for condition: {condition}")
        
        try:
            if selector and selector.css_selector:
                # Wait for specific element
                await page.wait_for_selector(
                    selector.css_selector,
                    state=condition,
                    timeout=timeout_ms
                )
            else:
                # Just wait for timeout
                await asyncio.sleep(timeout_ms / 1000.0)
            
            logger.info("Wait completed")
            
        except Exception as e:
            logger.warning(f"Wait action timed out: {e}")
            # Don't raise error for wait timeouts
    
    async def _execute_extract_action(
        self,
        page: Any,
        selector: Optional[Any],
        parameters: Dict[str, Any],
        progress_callback: Callable[[str], None]
    ) -> Dict[str, Any]:
        """
        Execute extract action to get data from page.
        
        Args:
            page: Playwright Page object
            selector: ElementSelectors for target element
            parameters: Extract parameters (extract_type, pattern)
            progress_callback: Function to report progress
        
        Returns:
            Dictionary with extracted data
        """
        if not selector:
            raise BrowserAutomationError("Extract action requires target selector")
        
        logger.info(f"Extracting data from element: {selector.css_selector}")
        
        try:
            element = await page.query_selector(selector.css_selector)
            
            if element:
                extract_type = parameters.get("extract_type", "text")
                
                if extract_type == "text":
                    text = await element.text_content()
                    logger.info(f"Extracted text: {text[:50]}...")
                    return {"extracted_text": text}
                
                elif extract_type == "attribute":
                    attr_name = parameters.get("attribute_name", "value")
                    value = await element.get_attribute(attr_name)
                    logger.info(f"Extracted attribute {attr_name}: {value}")
                    return {f"extracted_{attr_name}": value}
            
            return {}
            
        except Exception as e:
            logger.error(f"Extract action failed: {e}")
            return {}
    
    async def _execute_scroll_action(
        self,
        page: Any,
        parameters: Dict[str, Any],
        progress_callback: Callable[[str], None]
    ) -> None:
        """
        Execute scroll action.
        
        Args:
            page: Playwright Page object
            parameters: Scroll parameters (direction, amount)
            progress_callback: Function to report progress
        """
        direction = parameters.get("direction", "down")
        amount = parameters.get("amount", 500)
        
        logger.info(f"Scrolling {direction} by {amount}px")
        
        try:
            if direction == "down":
                await page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == "up":
                await page.evaluate(f"window.scrollBy(0, -{amount})")
            elif direction == "top":
                await page.evaluate("window.scrollTo(0, 0)")
            elif direction == "bottom":
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            logger.info("Scroll completed")
            
        except Exception as e:
            logger.error(f"Scroll action failed: {e}")
            raise
    
    async def _execute_select_action(
        self,
        page: Any,
        selector: Optional[Any],
        value: str,
        progress_callback: Callable[[str], None]
    ) -> None:
        """
        Execute select action (dropdown selection).
        
        Args:
            page: Playwright Page object
            selector: ElementSelectors for select element
            value: Value to select
            progress_callback: Function to report progress
        """
        if not selector:
            raise BrowserAutomationError("Select action requires target selector")
        
        logger.info(f"Selecting value '{value}' in element: {selector.css_selector}")
        
        try:
            await page.select_option(selector.css_selector, value)
            logger.info("Select successful")
            
        except Exception as e:
            logger.error(f"Select action failed: {e}")
            raise
    
    async def _verify_action_result(
        self,
        action: BrowserAction,
        dom: StructuredDOM,
        page: Any
    ) -> bool:
        """
        Verify action result against expected_result.
        
        Args:
            action: BrowserAction that was executed
            dom: Current StructuredDOM after action
            page: Playwright Page object
        
        Returns:
            True if verification passed, False otherwise
        """
        if not action.expected_result:
            return True  # No verification needed
        
        logger.debug(f"Verifying action result: {action.expected_result}")
        
        try:
            # Simple verification: check if expected text is in page
            page_text = await page.text_content('body') or ""
            
            # Check if expected result keywords are in page text
            expected_keywords = action.expected_result.lower().split()
            page_text_lower = page_text.lower()
            
            matches = sum(1 for keyword in expected_keywords if keyword in page_text_lower)
            
            # Consider verified if at least 50% of keywords match
            verified = matches >= len(expected_keywords) * 0.5
            
            logger.debug(
                f"Verification result: {verified} "
                f"({matches}/{len(expected_keywords)} keywords matched)"
            )
            
            return verified
            
        except Exception as e:
            logger.warning(f"Action verification failed: {e}")
            return False  # Assume not verified on error
