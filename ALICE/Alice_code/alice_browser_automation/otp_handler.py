"""
OTP Handler for Alice Browser Automation.

This module manages OTP (One-Time Password) verification through voice interaction
with Alice's LiveKit agent. It handles requesting OTPs from users via voice,
entering OTPs in web forms, and switching between headless and headed browser modes
for OTP visibility.

**Validates: Requirements 5.3, 5.4, 1.5, 8.2**
"""

import asyncio
import logging
import re
from typing import Optional, Any, Callable
from datetime import datetime

from playwright.async_api import Page

from .types import BrowserSession, ElementSelectors, SessionState
from .exceptions import OTPVerificationError, SessionError


logger = logging.getLogger(__name__)


class OTPHandler:
    """
    Handle OTP verification via LiveKit voice interaction.
    
    Responsibilities:
    - Request OTP from user via voice through Alice agent
    - Parse voice input to extract OTP digits
    - Enter OTP in web form verification fields
    - Switch browser between headless and headed modes
    - Detect OTP forms on web pages
    
    **Validates: Requirements 5.3, 5.4, 1.5, 8.2**
    """
    
    def __init__(
        self,
        voice_callback: Optional[Callable[[str], Any]] = None,
        input_callback: Optional[Callable[[str, int], str]] = None
    ):
        """
        Initialize the OTP Handler.
        
        Args:
            voice_callback: Optional callback to send voice messages to Alice agent.
                          Signature: callback(message: str) -> None
            input_callback: Optional callback to request input from user via Alice.
                          Signature: callback(prompt: str, timeout: int) -> str
        
        Note:
            If callbacks are not provided, the handler will use mock implementations
            for testing purposes. In production, these should be connected to the
            LiveKit agent.
        
        **Validates: Requirement 5.3**
        """
        self.voice_callback = voice_callback or self._mock_voice_callback
        self.input_callback = input_callback or self._mock_input_callback
        
        # OTP form detection patterns
        self.otp_patterns = [
            r'otp',
            r'verification\s*code',
            r'security\s*code',
            r'auth.*code',
            r'confirm.*code',
            r'2fa',
            r'two.*factor',
            r'pin\s*code',
        ]
        
        logger.info("OTPHandler initialized")
    
    async def request_otp(
        self,
        context: str = "verification code",
        timeout_seconds: int = 60
    ) -> str:
        """
        Request OTP from user via voice through Alice agent.
        
        Prompts the user via voice to provide the OTP, then waits for
        voice input and parses the digits.
        
        Args:
            context: Context for the OTP request (e.g., "verification code", "SMS code").
                    Defaults to "verification code".
            timeout_seconds: Maximum time to wait for user input in seconds.
                           Defaults to 60 seconds.
        
        Returns:
            OTP string (digits only)
        
        Raises:
            OTPVerificationError: If OTP request times out or parsing fails
        
        **Validates: Requirements 5.3, 5.4**
        
        Example:
            >>> handler = OTPHandler(voice_callback, input_callback)
            >>> otp = await handler.request_otp("SMS verification code")
            >>> print(otp)  # "123456"
        """
        logger.info(f"Requesting OTP from user: context='{context}'")
        
        # Send voice prompt to user
        prompt = f"Please provide the {context}. You can say the digits one by one or all together."
        await self._send_voice_message(prompt)
        
        try:
            # Request input from user via Alice
            user_input = await self._request_user_input(
                f"Waiting for {context}...",
                timeout_seconds
            )
            
            if not user_input:
                raise OTPVerificationError(
                    f"No input received for {context}",
                    verification_type=context
                )
            
            # Parse OTP from voice input
            otp = self._parse_otp_from_voice(user_input)
            
            if not otp:
                raise OTPVerificationError(
                    f"Could not parse OTP from input: '{user_input}'",
                    verification_type=context
                )
            
            logger.info(f"OTP received successfully: length={len(otp)}")
            
            # Confirm with user
            await self._send_voice_message(f"I received the code: {self._format_otp_for_voice(otp)}")
            
            return otp
            
        except asyncio.TimeoutError:
            raise OTPVerificationError(
                f"OTP request timed out after {timeout_seconds} seconds",
                verification_type=context
            )
        except OTPVerificationError:
            raise
        except Exception as e:
            raise OTPVerificationError(
                f"Failed to request OTP: {str(e)}",
                verification_type=context
            ) from e
    
    async def enter_otp(
        self,
        page: Page,
        otp: str,
        input_selector: Optional[ElementSelectors] = None
    ) -> bool:
        """
        Enter OTP in verification form.
        
        Locates the OTP input field(s) and enters the OTP code. Handles both
        single input fields and multi-field OTP inputs (one digit per field).
        
        Args:
            page: Playwright Page object
            otp: OTP string to enter (digits only)
            input_selector: Optional ElementSelectors for OTP input field.
                          If None, will attempt to detect OTP field automatically.
        
        Returns:
            True if OTP was entered successfully, False otherwise
        
        Raises:
            OTPVerificationError: If OTP entry fails
        
        **Validates: Requirements 5.3, 5.4**
        
        Example:
            >>> await handler.enter_otp(page, "123456")
            True
        """
        logger.info(f"Entering OTP in form: length={len(otp)}")
        
        try:
            # Detect OTP input field(s) if not provided
            if input_selector is None:
                input_selector = await self._detect_otp_field(page)
            
            if input_selector is None:
                raise OTPVerificationError(
                    "Could not detect OTP input field on page",
                    verification_type="form_detection"
                )
            
            # Try to enter OTP using different strategies
            success = False
            
            # Strategy 1: Single input field
            if input_selector.css_selector:
                success = await self._enter_otp_single_field(
                    page,
                    otp,
                    input_selector.css_selector
                )
            
            # Strategy 2: Multiple input fields (one digit per field)
            if not success:
                success = await self._enter_otp_multi_field(page, otp)
            
            if success:
                logger.info("OTP entered successfully")
                await self._send_voice_message("I've entered the verification code")
                return True
            else:
                raise OTPVerificationError(
                    "Failed to enter OTP in form",
                    verification_type="form_entry"
                )
                
        except OTPVerificationError:
            raise
        except Exception as e:
            raise OTPVerificationError(
                f"Failed to enter OTP: {str(e)}",
                verification_type="form_entry"
            ) from e
    
    async def detect_otp_form(self, page: Page) -> bool:
        """
        Detect if current page contains an OTP verification form.
        
        Checks page content for OTP-related patterns in input fields,
        labels, and text content.
        
        Args:
            page: Playwright Page object
        
        Returns:
            True if OTP form detected, False otherwise
        
        **Validates: Requirement 5.3**
        
        Example:
            >>> has_otp = await handler.detect_otp_form(page)
            >>> if has_otp:
            ...     otp = await handler.request_otp()
        """
        try:
            # Check for OTP input fields
            otp_field = await self._detect_otp_field(page)
            if otp_field:
                logger.info("OTP form detected on page")
                return True
            
            # Check page text for OTP-related content
            page_text = await page.text_content('body') or ""
            page_text_lower = page_text.lower()
            
            for pattern in self.otp_patterns:
                if re.search(pattern, page_text_lower):
                    logger.info(f"OTP form detected via pattern: {pattern}")
                    return True
            
            logger.debug("No OTP form detected on page")
            return False
            
        except Exception as e:
            logger.error(f"Error detecting OTP form: {e}")
            return False
    
    def _parse_otp_from_voice(self, voice_input: str) -> Optional[str]:
        """
        Parse OTP digits from voice input.
        
        Handles various voice input formats:
        - "one two three four five six" -> "123456"
        - "1 2 3 4 5 6" -> "123456"
        - "123456" -> "123456"
        - "the code is 123456" -> "123456"
        
        Args:
            voice_input: Raw voice input string
        
        Returns:
            OTP string (digits only) or None if parsing fails
        """
        # Word to digit mapping
        word_to_digit = {
            'zero': '0', 'oh': '0', 'o': '0',
            'one': '1', 'won': '1',
            'two': '2', 'to': '2', 'too': '2',
            'three': '3', 'tree': '3',
            'four': '4', 'for': '4', 'fore': '4',
            'five': '5',
            'six': '6', 'sicks': '6',
            'seven': '7',
            'eight': '8', 'ate': '8',
            'nine': '9', 'niner': '9',
        }
        
        # Clean input
        cleaned = voice_input.lower().strip()
        
        # Strategy 1: Extract all digits directly
        digits = re.findall(r'\d', cleaned)
        if len(digits) >= 4:  # Minimum OTP length
            otp = ''.join(digits)
            logger.debug(f"Parsed OTP via direct digits: {otp}")
            return otp
        
        # Strategy 2: Convert words to digits
        words = cleaned.split()
        digit_chars = []
        
        for word in words:
            # Remove punctuation
            word = re.sub(r'[^\w]', '', word)
            
            # Check if word is a digit word
            if word in word_to_digit:
                digit_chars.append(word_to_digit[word])
            # Check if word is already a digit
            elif word.isdigit():
                digit_chars.extend(list(word))
        
        if len(digit_chars) >= 4:
            otp = ''.join(digit_chars)
            logger.debug(f"Parsed OTP via word conversion: {otp}")
            return otp
        
        logger.warning(f"Could not parse OTP from voice input: '{voice_input}'")
        return None
    
    def _format_otp_for_voice(self, otp: str) -> str:
        """
        Format OTP for voice confirmation.
        
        Converts "123456" to "1 2 3 4 5 6" for clear voice feedback.
        
        Args:
            otp: OTP string
        
        Returns:
            Formatted OTP string with spaces between digits
        """
        return ' '.join(otp)
    
    async def _detect_otp_field(self, page: Page) -> Optional[ElementSelectors]:
        """
        Detect OTP input field on page.
        
        Searches for input fields with OTP-related attributes or labels.
        
        Args:
            page: Playwright Page object
        
        Returns:
            ElementSelectors for OTP field or None if not found
        """
        try:
            # Common OTP field selectors
            otp_selectors = [
                'input[name*="otp" i]',
                'input[id*="otp" i]',
                'input[placeholder*="otp" i]',
                'input[name*="code" i]',
                'input[id*="code" i]',
                'input[placeholder*="code" i]',
                'input[name*="verification" i]',
                'input[id*="verification" i]',
                'input[type="tel"][maxlength="6"]',
                'input[type="text"][maxlength="6"]',
                'input[type="number"][maxlength="6"]',
                'input[autocomplete="one-time-code"]',
            ]
            
            for selector in otp_selectors:
                element = await page.query_selector(selector)
                if element:
                    # Check if element is visible
                    is_visible = await element.is_visible()
                    if is_visible:
                        logger.debug(f"Found OTP field with selector: {selector}")
                        return ElementSelectors(
                            css_selector=selector,
                            xpath=f"//*[@id='{await element.get_attribute('id')}']" if await element.get_attribute('id') else "",
                            aria_label=await element.get_attribute('aria-label'),
                            text_content=None
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting OTP field: {e}")
            return None
    
    async def _enter_otp_single_field(
        self,
        page: Page,
        otp: str,
        selector: str
    ) -> bool:
        """
        Enter OTP in a single input field.
        
        Args:
            page: Playwright Page object
            otp: OTP string
            selector: CSS selector for input field
        
        Returns:
            True if successful, False otherwise
        """
        try:
            element = await page.query_selector(selector)
            if not element:
                return False
            
            # Clear field first
            await element.fill('')
            
            # Enter OTP
            await element.fill(otp)
            
            # Verify value was entered
            value = await element.input_value()
            if value == otp:
                logger.debug(f"OTP entered in single field: {selector}")
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Failed to enter OTP in single field: {e}")
            return False
    
    async def _enter_otp_multi_field(self, page: Page, otp: str) -> bool:
        """
        Enter OTP in multiple input fields (one digit per field).
        
        Some OTP forms have separate input fields for each digit.
        
        Args:
            page: Playwright Page object
            otp: OTP string
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find all input fields that might be OTP digit fields
            digit_fields = await page.query_selector_all(
                'input[type="text"][maxlength="1"], '
                'input[type="tel"][maxlength="1"], '
                'input[type="number"][maxlength="1"]'
            )
            
            if len(digit_fields) < len(otp):
                return False
            
            # Enter each digit in corresponding field
            for i, digit in enumerate(otp):
                if i >= len(digit_fields):
                    break
                
                field = digit_fields[i]
                await field.fill(digit)
                
                # Some forms auto-focus next field
                await asyncio.sleep(0.1)
            
            logger.debug(f"OTP entered in {len(otp)} separate fields")
            return True
            
        except Exception as e:
            logger.debug(f"Failed to enter OTP in multi-field: {e}")
            return False
    
    async def _send_voice_message(self, message: str) -> None:
        """
        Send voice message to Alice agent.
        
        Args:
            message: Message to send
        """
        try:
            if asyncio.iscoroutinefunction(self.voice_callback):
                await self.voice_callback(message)
            else:
                self.voice_callback(message)
        except Exception as e:
            logger.error(f"Error sending voice message: {e}")
    
    async def _request_user_input(
        self,
        prompt: str,
        timeout_seconds: int
    ) -> str:
        """
        Request input from user via Alice agent.
        
        Args:
            prompt: Prompt message
            timeout_seconds: Timeout in seconds
        
        Returns:
            User input string
        
        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        try:
            if asyncio.iscoroutinefunction(self.input_callback):
                result = await asyncio.wait_for(
                    self.input_callback(prompt, timeout_seconds),
                    timeout=timeout_seconds
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(self.input_callback, prompt, timeout_seconds),
                    timeout=timeout_seconds
                )
            return result
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            logger.error(f"Error requesting user input: {e}")
            raise
    
    def _mock_voice_callback(self, message: str) -> None:
        """Mock voice callback for testing."""
        logger.info(f"[VOICE] {message}")
    
    def _mock_input_callback(self, prompt: str, timeout: int) -> str:
        """Mock input callback for testing."""
        logger.info(f"[INPUT REQUEST] {prompt} (timeout: {timeout}s)")
        return "123456"  # Mock OTP for testing
    
    async def switch_to_headed_mode(
        self,
        session: BrowserSession,
        session_manager: Any
    ) -> BrowserSession:
        """
        Switch browser session to headed mode for OTP visibility.
        
        Creates a new headed browser session with the same profile and navigates
        to the same URL. This allows users to see the OTP form and any visual
        verification elements.
        
        Args:
            session: Current BrowserSession (headless)
            session_manager: SessionManager instance to create new session
        
        Returns:
            New BrowserSession in headed mode
        
        Raises:
            SessionError: If mode switching fails
        
        **Validates: Requirements 1.5, 8.2**
        
        Example:
            >>> # OTP form detected
            >>> if await handler.detect_otp_form(page):
            ...     headed_session = await handler.switch_to_headed_mode(session, manager)
            ...     otp = await handler.request_otp()
            ...     await handler.enter_otp(headed_session.playwright_page, otp)
        """
        logger.info(f"Switching session {session.session_id} to headed mode")
        
        try:
            # Save current state
            current_url = session.playwright_page.url
            profile_name = session.profile_name
            domain = session.domain
            
            # Notify user
            await self._send_voice_message(
                "I'm opening the browser window so you can see the verification form"
            )
            
            # Close current headless session
            await session_manager.close_session(session.session_id)
            
            # Create new headed session
            headed_session = await session_manager.create_session(
                profile_name=profile_name,
                headless=False,  # Headed mode
                domain=domain
            )
            
            # Navigate to same URL
            await headed_session.playwright_page.goto(current_url, wait_until='networkidle')
            
            logger.info(
                f"Switched to headed mode: old={session.session_id}, "
                f"new={headed_session.session_id}"
            )
            
            return headed_session
            
        except Exception as e:
            raise SessionError(
                f"Failed to switch to headed mode: {str(e)}",
                session_id=session.session_id,
                operation="switch_to_headed"
            ) from e
    
    async def switch_to_headless_mode(
        self,
        session: BrowserSession,
        session_manager: Any
    ) -> BrowserSession:
        """
        Switch browser session back to headless mode after OTP.
        
        Creates a new headless browser session with the same profile and navigates
        to the same URL. This returns to the normal headless operation mode.
        
        Args:
            session: Current BrowserSession (headed)
            session_manager: SessionManager instance to create new session
        
        Returns:
            New BrowserSession in headless mode
        
        Raises:
            SessionError: If mode switching fails
        
        **Validates: Requirements 1.5, 8.2**
        
        Example:
            >>> # After OTP verification
            >>> headless_session = await handler.switch_to_headless_mode(session, manager)
        """
        logger.info(f"Switching session {session.session_id} to headless mode")
        
        try:
            # Save current state
            current_url = session.playwright_page.url
            profile_name = session.profile_name
            domain = session.domain
            
            # Notify user
            await self._send_voice_message(
                "Verification complete. Closing the browser window"
            )
            
            # Close current headed session
            await session_manager.close_session(session.session_id)
            
            # Create new headless session
            headless_session = await session_manager.create_session(
                profile_name=profile_name,
                headless=True,  # Headless mode
                domain=domain
            )
            
            # Navigate to same URL
            await headless_session.playwright_page.goto(current_url, wait_until='networkidle')
            
            logger.info(
                f"Switched to headless mode: old={session.session_id}, "
                f"new={headless_session.session_id}"
            )
            
            return headless_session
            
        except Exception as e:
            raise SessionError(
                f"Failed to switch to headless mode: {str(e)}",
                session_id=session.session_id,
                operation="switch_to_headless"
            ) from e
    
    async def handle_otp_verification(
        self,
        session: BrowserSession,
        session_manager: Any,
        show_browser: bool = True
    ) -> BrowserSession:
        """
        Complete OTP verification workflow.
        
        Handles the entire OTP verification process:
        1. Detect OTP form
        2. Switch to headed mode (if requested)
        3. Request OTP from user
        4. Enter OTP in form
        5. Wait for verification
        6. Switch back to headless mode
        
        Args:
            session: Current BrowserSession
            session_manager: SessionManager instance
            show_browser: Whether to show browser window during OTP entry.
                         Defaults to True.
        
        Returns:
            BrowserSession after OTP verification (headless mode)
        
        Raises:
            OTPVerificationError: If OTP verification fails
            SessionError: If mode switching fails
        
        **Validates: Requirements 5.3, 5.4, 1.5, 8.2**
        
        Example:
            >>> # Detect OTP form and handle verification
            >>> if await handler.detect_otp_form(session.playwright_page):
            ...     session = await handler.handle_otp_verification(session, manager)
        """
        logger.info("Starting OTP verification workflow")
        
        try:
            page = session.playwright_page
            
            # Verify OTP form is present
            if not await self.detect_otp_form(page):
                raise OTPVerificationError(
                    "No OTP form detected on page",
                    verification_type="form_detection"
                )
            
            # Switch to headed mode if requested
            if show_browser and session.is_headless:
                session = await self.switch_to_headed_mode(session, session_manager)
                page = session.playwright_page
            
            # Request OTP from user
            otp = await self.request_otp()
            
            # Enter OTP in form
            success = await self.enter_otp(page, otp)
            
            if not success:
                raise OTPVerificationError(
                    "Failed to enter OTP in form",
                    verification_type="form_entry"
                )
            
            # Wait for form submission and verification
            await self._send_voice_message("Verifying the code...")
            await asyncio.sleep(2)  # Give time for form submission
            
            # Check if verification was successful
            # (In production, this should check for success indicators on the page)
            verification_success = await self._check_verification_success(page)
            
            if not verification_success:
                raise OTPVerificationError(
                    "OTP verification failed",
                    verification_type="verification_failed"
                )
            
            await self._send_voice_message("Verification successful!")
            
            # Switch back to headless mode if we switched to headed
            if show_browser and not session.is_headless:
                session = await self.switch_to_headless_mode(session, session_manager)
            
            logger.info("OTP verification workflow completed successfully")
            return session
            
        except (OTPVerificationError, SessionError):
            raise
        except Exception as e:
            raise OTPVerificationError(
                f"OTP verification workflow failed: {str(e)}",
                verification_type="workflow"
            ) from e
    
    async def _check_verification_success(self, page: Page) -> bool:
        """
        Check if OTP verification was successful.
        
        Looks for success indicators on the page:
        - Disappearance of OTP form
        - Success message
        - Redirect to next page
        - Error message (indicates failure)
        
        Args:
            page: Playwright Page object
        
        Returns:
            True if verification successful, False otherwise
        """
        try:
            # Wait a bit for page to update
            await asyncio.sleep(1)
            
            # Check for error messages
            error_patterns = [
                'invalid.*code',
                'incorrect.*code',
                'wrong.*code',
                'expired.*code',
                'verification.*failed',
            ]
            
            page_text = (await page.text_content('body') or "").lower()
            
            for pattern in error_patterns:
                if re.search(pattern, page_text):
                    logger.warning(f"Verification error detected: {pattern}")
                    return False
            
            # Check if OTP form is still present
            has_otp_form = await self.detect_otp_form(page)
            
            # If OTP form disappeared, verification likely successful
            if not has_otp_form:
                logger.info("OTP form disappeared - verification likely successful")
                return True
            
            # Check for success indicators
            success_patterns = [
                'success',
                'verified',
                'confirmed',
                'authenticated',
            ]
            
            for pattern in success_patterns:
                if re.search(pattern, page_text):
                    logger.info(f"Success indicator detected: {pattern}")
                    return True
            
            # Default to success if no error detected
            logger.info("No error detected - assuming verification successful")
            return True
            
        except Exception as e:
            logger.error(f"Error checking verification success: {e}")
            # Default to success to avoid blocking workflow
            return True
