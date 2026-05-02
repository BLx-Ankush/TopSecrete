"""
Error Handler for Alice Browser Automation.

This module provides comprehensive error handling and recovery strategies for
browser automation tasks. It handles element not found errors, page load timeouts,
invalid actions, session crashes, and network errors with appropriate retry logic
and fallback strategies.

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6**
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional, Any, Callable, List
from urllib.parse import urlparse

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from .types import (
    BrowserSession,
    BrowserAction,
    ElementSelectors,
    RetryConfig,
    SessionState
)
from .exceptions import (
    ElementNotFoundError,
    PageLoadTimeoutError,
    InvalidActionError,
    NetworkError,
    SessionCrashedError,
    SessionError
)


logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Handle browser automation errors with retry logic and recovery strategies.
    
    Responsibilities:
    - Handle element not found errors with alternative selectors
    - Handle page load timeouts with navigation retry
    - Handle invalid actions with corrected prompts
    - Handle session crashes with restart and state restoration
    - Handle network errors with connectivity checks
    - Implement exponential backoff for retries
    - Log all errors with context
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6**
    """
    
    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        session_manager: Optional[Any] = None,
        qwen_client: Optional[Any] = None
    ):
        """
        Initialize the Error Handler.
        
        Args:
            retry_config: Optional RetryConfig for retry behavior.
                         If None, uses default configuration.
            session_manager: Optional SessionManager for session recovery.
            qwen_client: Optional QwenModelClient for action correction.
        
        **Validates: Requirement 9.5**
        """
        self.retry_config = retry_config or RetryConfig()
        self.session_manager = session_manager
        self.qwen_client = qwen_client
        
        # Error statistics for monitoring
        self.error_stats = {
            'element_not_found': 0,
            'page_load_timeout': 0,
            'invalid_action': 0,
            'session_crashed': 0,
            'network_error': 0,
            'total_retries': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0
        }
        
        logger.info("ErrorHandler initialized with retry config")
    
    async def handle_element_not_found(
        self,
        page: Page,
        original_selector: ElementSelectors,
        action_description: str = "interact with element"
    ) -> Optional[ElementSelectors]:
        """
        Handle element not found error with alternative selector retry logic.
        
        Tries alternative selectors in order:
        1. CSS selector
        2. XPath
        3. ARIA label
        4. Text content match
        
        Args:
            page: Playwright Page object
            original_selector: Original ElementSelectors that failed
            action_description: Description of the action for logging
        
        Returns:
            Working ElementSelectors if found, None otherwise
        
        Raises:
            ElementNotFoundError: If all alternative selectors fail
        
        **Validates: Requirement 9.1**
        
        Example:
            >>> try:
            ...     element = await page.query_selector(selector.css_selector)
            ... except:
            ...     working_selector = await handler.handle_element_not_found(
            ...         page, selector, "click button"
            ...     )
        """
        self.error_stats['element_not_found'] += 1
        
        logger.warning(
            f"Element not found for action: {action_description}. "
            f"Trying alternative selectors..."
        )
        
        # Log error with context
        self._log_error(
            "ElementNotFound",
            {
                'action': action_description,
                'original_css': original_selector.css_selector,
                'original_xpath': original_selector.xpath,
                'page_url': page.url
            }
        )
        
        # Try alternative selectors
        alternative_strategies = [
            ('css_selector', original_selector.css_selector),
            ('xpath', original_selector.xpath),
            ('aria_label', original_selector.aria_label),
            ('text_content', original_selector.text_content)
        ]
        
        for retry_count in range(self.retry_config.element_not_found_retries):
            self.error_stats['total_retries'] += 1
            
            for strategy_name, selector_value in alternative_strategies:
                if not selector_value:
                    continue
                
                try:
                    logger.debug(
                        f"Retry {retry_count + 1}/{self.retry_config.element_not_found_retries}: "
                        f"Trying {strategy_name} = '{selector_value}'"
                    )
                    
                    # Try to find element with this selector
                    if strategy_name == 'css_selector':
                        element = await page.query_selector(selector_value)
                    elif strategy_name == 'xpath':
                        element = await page.query_selector(f"xpath={selector_value}")
                    elif strategy_name == 'aria_label':
                        element = await page.query_selector(f"[aria-label='{selector_value}']")
                    elif strategy_name == 'text_content':
                        element = await page.query_selector(f"text={selector_value}")
                    else:
                        continue
                    
                    if element and await element.is_visible():
                        logger.info(
                            f"Element found using {strategy_name}: '{selector_value}'"
                        )
                        self.error_stats['successful_recoveries'] += 1
                        
                        # Return working selector
                        return ElementSelectors(
                            css_selector=selector_value if strategy_name == 'css_selector' else "",
                            xpath=selector_value if strategy_name == 'xpath' else "",
                            aria_label=selector_value if strategy_name == 'aria_label' else None,
                            text_content=selector_value if strategy_name == 'text_content' else None
                        )
                
                except Exception as e:
                    logger.debug(f"Selector {strategy_name} failed: {e}")
                    continue
            
            # Wait before next retry with exponential backoff
            if retry_count < self.retry_config.element_not_found_retries - 1:
                await self._exponential_backoff(retry_count)
        
        # All retries failed
        self.error_stats['failed_recoveries'] += 1
        
        raise ElementNotFoundError(
            f"Element not found after {self.retry_config.element_not_found_retries} retries "
            f"for action: {action_description}",
            selector=original_selector.css_selector,
            page_url=page.url
        )
    
    async def handle_page_load_timeout(
        self,
        page: Page,
        url: str,
        timeout_seconds: float = 30.0
    ) -> bool:
        """
        Handle page load timeout with navigation retry.
        
        Retries navigation up to 2 times with increasing timeout.
        
        Args:
            page: Playwright Page object
            url: URL that failed to load
            timeout_seconds: Timeout in seconds for each retry
        
        Returns:
            True if page loaded successfully, False otherwise
        
        Raises:
            PageLoadTimeoutError: If all retries fail
        
        **Validates: Requirement 9.2**
        
        Example:
            >>> try:
            ...     await page.goto(url, timeout=30000)
            ... except TimeoutError:
            ...     success = await handler.handle_page_load_timeout(page, url)
        """
        self.error_stats['page_load_timeout'] += 1
        
        logger.warning(f"Page load timeout for URL: {url}. Retrying...")
        
        # Log error with context
        self._log_error(
            "PageLoadTimeout",
            {
                'url': url,
                'timeout_seconds': timeout_seconds,
                'current_url': page.url
            }
        )
        
        for retry_count in range(self.retry_config.page_load_retries):
            self.error_stats['total_retries'] += 1
            
            # Increase timeout for each retry
            retry_timeout = timeout_seconds * (retry_count + 1)
            
            try:
                logger.info(
                    f"Retry {retry_count + 1}/{self.retry_config.page_load_retries}: "
                    f"Loading {url} with timeout {retry_timeout}s"
                )
                
                await page.goto(
                    url,
                    timeout=int(retry_timeout * 1000),  # Convert to milliseconds
                    wait_until='networkidle'
                )
                
                logger.info(f"Page loaded successfully on retry {retry_count + 1}")
                self.error_stats['successful_recoveries'] += 1
                return True
                
            except PlaywrightTimeoutError as e:
                logger.warning(f"Retry {retry_count + 1} failed: {e}")
                
                # Wait before next retry with exponential backoff
                if retry_count < self.retry_config.page_load_retries - 1:
                    await self._exponential_backoff(retry_count)
            
            except Exception as e:
                logger.error(f"Unexpected error during page load retry: {e}")
                break
        
        # All retries failed
        self.error_stats['failed_recoveries'] += 1
        
        raise PageLoadTimeoutError(
            f"Page load timeout after {self.retry_config.page_load_retries} retries",
            url=url,
            timeout_seconds=timeout_seconds
        )
    
    async def handle_invalid_action(
        self,
        invalid_json: str,
        validation_error: str,
        context: dict
    ) -> Optional[BrowserAction]:
        """
        Handle invalid action with corrected prompt retry.
        
        Requests corrected action from Qwen model with error context.
        
        Args:
            invalid_json: The invalid JSON that was generated
            validation_error: The validation error message
            context: Context for action generation (task, DOM, etc.)
        
        Returns:
            Corrected BrowserAction if successful, None otherwise
        
        Raises:
            InvalidActionError: If all correction attempts fail
        
        **Validates: Requirement 9.3**
        
        Example:
            >>> try:
            ...     action = parse_action(json_str)
            ... except ValidationError as e:
            ...     action = await handler.handle_invalid_action(
            ...         json_str, str(e), context
            ...     )
        """
        self.error_stats['invalid_action'] += 1
        
        logger.warning(
            f"Invalid action generated. Validation error: {validation_error}"
        )
        
        # Log error with context (but not the invalid JSON to avoid clutter)
        self._log_error(
            "InvalidAction",
            {
                'validation_error': validation_error,
                'context_keys': list(context.keys())
            }
        )
        
        if not self.qwen_client:
            logger.error("QwenModelClient not available for action correction")
            raise InvalidActionError(
                "Cannot correct invalid action: QwenModelClient not available",
                invalid_json=invalid_json,
                validation_error=validation_error
            )
        
        for retry_count in range(self.retry_config.invalid_action_retries):
            self.error_stats['total_retries'] += 1
            
            try:
                logger.info(
                    f"Retry {retry_count + 1}/{self.retry_config.invalid_action_retries}: "
                    f"Requesting corrected action from Qwen"
                )
                
                # Build correction prompt with error context
                correction_prompt = self._build_correction_prompt(
                    invalid_json,
                    validation_error,
                    context
                )
                
                # Request corrected action from Qwen
                # (This would call qwen_client.generate_json_response)
                # For now, we'll raise an error since Qwen integration is in Task 12
                logger.warning("Qwen correction not yet implemented (Task 12)")
                
                # Wait before next retry
                if retry_count < self.retry_config.invalid_action_retries - 1:
                    await self._exponential_backoff(retry_count)
                
            except Exception as e:
                logger.error(f"Error during action correction: {e}")
                continue
        
        # All retries failed
        self.error_stats['failed_recoveries'] += 1
        
        raise InvalidActionError(
            f"Invalid action after {self.retry_config.invalid_action_retries} correction attempts",
            invalid_json=invalid_json,
            validation_error=validation_error
        )
    
    async def handle_session_crashed(
        self,
        session: BrowserSession
    ) -> BrowserSession:
        """
        Handle session crash with restart and state restoration.
        
        Restarts the crashed session using SessionManager and attempts
        to restore the previous state (URL, profile).
        
        Args:
            session: Crashed BrowserSession
        
        Returns:
            New BrowserSession after restart
        
        Raises:
            SessionCrashedError: If session restart fails
        
        **Validates: Requirement 9.6**
        
        Example:
            >>> try:
            ...     await page.click(selector)
            ... except Exception as e:
            ...     if is_crash(e):
            ...         session = await handler.handle_session_crashed(session)
        """
        self.error_stats['session_crashed'] += 1
        
        logger.error(f"Session crashed: {session.session_id}")
        
        # Log error with context
        self._log_error(
            "SessionCrashed",
            {
                'session_id': session.session_id,
                'profile_name': session.profile_name,
                'domain': session.domain,
                'last_url': session.playwright_page.url if session.playwright_page else None
            }
        )
        
        if not self.session_manager:
            raise SessionCrashedError(
                "Cannot restart session: SessionManager not available",
                session_id=session.session_id
            )
        
        try:
            logger.info(f"Attempting to restart session: {session.session_id}")
            
            # Mark session as crashed
            self.session_manager.mark_session_crashed(session.session_id)
            
            # Restart session
            new_session = await self.session_manager.restart_crashed_session(
                session.session_id
            )
            
            logger.info(
                f"Session restarted successfully: old={session.session_id}, "
                f"new={new_session.session_id}"
            )
            
            self.error_stats['successful_recoveries'] += 1
            return new_session
            
        except Exception as e:
            self.error_stats['failed_recoveries'] += 1
            
            raise SessionCrashedError(
                f"Failed to restart crashed session: {str(e)}",
                session_id=session.session_id,
                last_url=session.playwright_page.url if session.playwright_page else None
            ) from e
    
    async def handle_network_error(
        self,
        operation: str,
        original_error: Exception,
        retry_callback: Optional[Callable] = None
    ) -> Any:
        """
        Handle network error with connectivity check and retry.
        
        Checks network connectivity and retries the operation with
        exponential backoff.
        
        Args:
            operation: Description of the operation that failed
            original_error: The original network error
            retry_callback: Optional callback to retry the operation.
                          If None, just checks connectivity.
        
        Returns:
            Result of retry_callback if successful
        
        Raises:
            NetworkError: If all retries fail or connectivity check fails
        
        **Validates: Requirement 9.4**
        
        Example:
            >>> try:
            ...     result = await some_network_operation()
            ... except Exception as e:
            ...     result = await handler.handle_network_error(
            ...         "fetch data",
            ...         e,
            ...         lambda: some_network_operation()
            ...     )
        """
        self.error_stats['network_error'] += 1
        
        logger.warning(f"Network error during operation: {operation}")
        
        # Log error with context
        self._log_error(
            "NetworkError",
            {
                'operation': operation,
                'error_type': type(original_error).__name__,
                'error_message': str(original_error)
            }
        )
        
        # Check network connectivity
        is_connected = await self._check_connectivity()
        
        if not is_connected:
            self.error_stats['failed_recoveries'] += 1
            
            raise NetworkError(
                f"Network connectivity check failed during operation: {operation}",
                operation=operation,
                original_error=original_error
            )
        
        # If no retry callback, just report the error
        if not retry_callback:
            raise NetworkError(
                f"Network error during operation: {operation}",
                operation=operation,
                original_error=original_error
            )
        
        # Retry operation with exponential backoff
        for retry_count in range(self.retry_config.network_error_retries):
            self.error_stats['total_retries'] += 1
            
            try:
                logger.info(
                    f"Retry {retry_count + 1}/{self.retry_config.network_error_retries}: "
                    f"Retrying operation: {operation}"
                )
                
                # Wait before retry with exponential backoff
                if retry_count > 0:
                    await self._exponential_backoff(retry_count - 1)
                
                # Retry operation
                if asyncio.iscoroutinefunction(retry_callback):
                    result = await retry_callback()
                else:
                    result = retry_callback()
                
                logger.info(f"Operation succeeded on retry {retry_count + 1}")
                self.error_stats['successful_recoveries'] += 1
                return result
                
            except Exception as e:
                logger.warning(f"Retry {retry_count + 1} failed: {e}")
                
                if retry_count == self.retry_config.network_error_retries - 1:
                    # Last retry failed
                    self.error_stats['failed_recoveries'] += 1
                    
                    raise NetworkError(
                        f"Network error after {self.retry_config.network_error_retries} retries: {operation}",
                        operation=operation,
                        original_error=original_error
                    ) from e
    
    async def _exponential_backoff(self, retry_count: int) -> None:
        """
        Wait with exponential backoff.
        
        Args:
            retry_count: Current retry count (0-indexed)
        
        **Validates: Requirement 9.5**
        """
        if not self.retry_config.exponential_backoff:
            # Fixed delay
            await asyncio.sleep(self.retry_config.retry_delay_seconds)
            return
        
        # Exponential backoff: delay * (multiplier ^ retry_count)
        delay = self.retry_config.retry_delay_seconds * (
            self.retry_config.backoff_multiplier ** retry_count
        )
        
        # Cap maximum delay at 30 seconds
        delay = min(delay, 30.0)
        
        logger.debug(f"Waiting {delay:.2f}s before retry (exponential backoff)")
        await asyncio.sleep(delay)
    
    async def _check_connectivity(self) -> bool:
        """
        Check network connectivity.
        
        Attempts to connect to a reliable host (e.g., Google DNS).
        
        Returns:
            True if connected, False otherwise
        """
        try:
            # Try to resolve a reliable domain
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            logger.debug("Network connectivity check: OK")
            return True
        except Exception as e:
            logger.warning(f"Network connectivity check failed: {e}")
            return False
    
    def _build_correction_prompt(
        self,
        invalid_json: str,
        validation_error: str,
        context: dict
    ) -> str:
        """
        Build correction prompt for Qwen model.
        
        Args:
            invalid_json: The invalid JSON
            validation_error: The validation error
            context: Context for action generation
        
        Returns:
            Correction prompt string
        """
        prompt = f"""The previous action generation produced invalid JSON.

Error: {validation_error}

Invalid JSON:
{invalid_json}

Please generate a corrected action in valid JSON format following the schema.

Context:
{context.get('task_description', 'N/A')}

Current DOM:
{context.get('dom_summary', 'N/A')}

Generate a valid browser action in JSON format.
"""
        return prompt
    
    def _log_error(
        self,
        error_type: str,
        context: dict
    ) -> None:
        """
        Log error with timestamp and context.
        
        Args:
            error_type: Type of error
            context: Error context dictionary
        
        **Validates: Requirement 9.5**
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type,
            'context': context
        }
        
        logger.error(f"Error logged: {log_entry}")
    
    def get_error_stats(self) -> dict:
        """
        Get error statistics for monitoring.
        
        Returns:
            Dictionary of error statistics
        """
        return self.error_stats.copy()
    
    def reset_error_stats(self) -> None:
        """Reset error statistics."""
        for key in self.error_stats:
            self.error_stats[key] = 0
        logger.info("Error statistics reset")
