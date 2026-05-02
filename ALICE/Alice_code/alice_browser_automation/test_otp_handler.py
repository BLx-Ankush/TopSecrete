"""
Unit tests for OTPHandler.

Tests OTP request via voice, OTP entry in forms, mode switching,
and OTP form detection.

**Validates: Requirements 5.3, 5.4, 1.5, 8.2**
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from alice_browser_automation.otp_handler import OTPHandler
from alice_browser_automation.types import BrowserSession, SessionState
from alice_browser_automation.exceptions import OTPVerificationError, SessionError


class TestOTPHandlerInitialization:
    """Test OTPHandler initialization."""
    
    def test_init_with_callbacks(self):
        """Test initialization with custom callbacks."""
        voice_callback = Mock()
        input_callback = Mock()
        
        handler = OTPHandler(voice_callback, input_callback)
        
        assert handler.voice_callback == voice_callback
        assert handler.input_callback == input_callback
        assert len(handler.otp_patterns) > 0
    
    def test_init_without_callbacks(self):
        """Test initialization with default mock callbacks."""
        handler = OTPHandler()
        
        assert handler.voice_callback is not None
        assert handler.input_callback is not None


class TestOTPParsing:
    """Test OTP parsing from voice input."""
    
    @pytest.fixture
    def handler(self):
        """Create OTPHandler instance."""
        return OTPHandler()
    
    def test_parse_otp_direct_digits(self, handler):
        """Test parsing OTP from direct digit input."""
        assert handler._parse_otp_from_voice("123456") == "123456"
        assert handler._parse_otp_from_voice("1 2 3 4 5 6") == "123456"
        assert handler._parse_otp_from_voice("the code is 123456") == "123456"
    
    def test_parse_otp_word_digits(self, handler):
        """Test parsing OTP from word digits."""
        assert handler._parse_otp_from_voice("one two three four five six") == "123456"
        assert handler._parse_otp_from_voice("zero one two three") == "0123"
    
    def test_parse_otp_mixed_format(self, handler):
        """Test parsing OTP from mixed format."""
        assert handler._parse_otp_from_voice("one 2 three 4 five 6") == "123456"
        assert handler._parse_otp_from_voice("the code is one two three four") == "1234"
    
    def test_parse_otp_alternative_words(self, handler):
        """Test parsing OTP with alternative word pronunciations."""
        assert handler._parse_otp_from_voice("oh one two three") == "0123"
        # Test with actual digit words that are in the mapping (need at least 4 digits)
        assert handler._parse_otp_from_voice("zero one two three four") == "01234"
    
    def test_parse_otp_invalid_input(self, handler):
        """Test parsing OTP from invalid input."""
        assert handler._parse_otp_from_voice("") is None
        assert handler._parse_otp_from_voice("abc def") is None
        assert handler._parse_otp_from_voice("no digits here") is None
    
    def test_format_otp_for_voice(self, handler):
        """Test formatting OTP for voice confirmation."""
        assert handler._format_otp_for_voice("123456") == "1 2 3 4 5 6"
        assert handler._format_otp_for_voice("0000") == "0 0 0 0"


class TestOTPRequest:
    """Test OTP request via voice."""
    
    @pytest.fixture
    def handler(self):
        """Create OTPHandler with mock callbacks."""
        voice_callback = AsyncMock()
        input_callback = AsyncMock(return_value="123456")
        return OTPHandler(voice_callback, input_callback)
    
    @pytest.mark.asyncio
    async def test_request_otp_success(self, handler):
        """Test successful OTP request."""
        otp = await handler.request_otp("SMS code")
        
        assert otp == "123456"
        assert handler.voice_callback.call_count >= 2  # Prompt + confirmation
    
    @pytest.mark.asyncio
    async def test_request_otp_with_word_input(self, handler):
        """Test OTP request with word digit input."""
        handler.input_callback = AsyncMock(return_value="one two three four five six")
        
        otp = await handler.request_otp()
        
        assert otp == "123456"
    
    @pytest.mark.asyncio
    async def test_request_otp_timeout(self, handler):
        """Test OTP request timeout."""
        async def timeout_callback(prompt, timeout):
            await asyncio.sleep(timeout + 1)
            return "123456"
        
        handler.input_callback = timeout_callback
        
        with pytest.raises(OTPVerificationError, match="timed out"):
            await handler.request_otp(timeout_seconds=1)
    
    @pytest.mark.asyncio
    async def test_request_otp_no_input(self, handler):
        """Test OTP request with no input."""
        handler.input_callback = AsyncMock(return_value="")
        
        with pytest.raises(OTPVerificationError, match="No input received"):
            await handler.request_otp()
    
    @pytest.mark.asyncio
    async def test_request_otp_invalid_input(self, handler):
        """Test OTP request with invalid input."""
        handler.input_callback = AsyncMock(return_value="invalid input")
        
        with pytest.raises(OTPVerificationError, match="Could not parse OTP"):
            await handler.request_otp()


class TestOTPFormDetection:
    """Test OTP form detection."""
    
    @pytest.fixture
    def handler(self):
        """Create OTPHandler instance."""
        return OTPHandler()
    
    @pytest.mark.asyncio
    async def test_detect_otp_form_with_otp_field(self, handler):
        """Test detecting OTP form with OTP input field."""
        # Mock page with OTP field
        mock_page = AsyncMock()
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_element.get_attribute = AsyncMock(side_effect=lambda attr: {
            'id': 'otp-input',
            'aria-label': 'Enter OTP'
        }.get(attr))
        
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        result = await handler.detect_otp_form(mock_page)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_detect_otp_form_with_text_pattern(self, handler):
        """Test detecting OTP form via text pattern."""
        # Mock page without OTP field but with OTP text
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.text_content = AsyncMock(return_value="Please enter your verification code")
        
        result = await handler.detect_otp_form(mock_page)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_detect_otp_form_not_found(self, handler):
        """Test OTP form not detected."""
        # Mock page without OTP indicators
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.text_content = AsyncMock(return_value="Regular page content")
        
        result = await handler.detect_otp_form(mock_page)
        
        assert result is False


class TestOTPEntry:
    """Test OTP entry in forms."""
    
    @pytest.fixture
    def handler(self):
        """Create OTPHandler instance."""
        voice_callback = AsyncMock()
        return OTPHandler(voice_callback)
    
    @pytest.mark.asyncio
    async def test_enter_otp_single_field_success(self, handler):
        """Test entering OTP in single input field."""
        # Mock page with single OTP field
        mock_page = AsyncMock()
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_element.get_attribute = AsyncMock(return_value='otp-input')
        mock_element.fill = AsyncMock()
        mock_element.input_value = AsyncMock(return_value="123456")
        
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        
        result = await handler.enter_otp(mock_page, "123456")
        
        assert result is True
        mock_element.fill.assert_called()
    
    @pytest.mark.asyncio
    async def test_enter_otp_multi_field_success(self, handler):
        """Test entering OTP in multiple input fields."""
        # Mock page with multiple digit fields
        mock_page = AsyncMock()
        
        # Mock digit fields
        digit_fields = []
        for i in range(6):
            field = AsyncMock()
            field.fill = AsyncMock()
            digit_fields.append(field)
        
        # Mock query_selector_all to return digit fields
        mock_page.query_selector_all = AsyncMock(return_value=digit_fields)
        
        # Create a mock ElementSelectors that will fail single-field entry
        mock_selector = Mock()
        mock_selector.css_selector = "input[name='otp']"
        
        # Patch _detect_otp_field to return a selector
        with patch.object(handler, '_detect_otp_field', return_value=AsyncMock(return_value=mock_selector)):
            # Patch _enter_otp_single_field to return False (will trigger multi-field)
            async def mock_single_field(*args):
                return False
            
            with patch.object(handler, '_enter_otp_single_field', side_effect=mock_single_field):
                result = await handler.enter_otp(mock_page, "123456")
        
        assert result is True
        # Verify each digit was entered
        for i, field in enumerate(digit_fields):
            field.fill.assert_called_with(str(i + 1))
    
    @pytest.mark.asyncio
    async def test_enter_otp_no_field_detected(self, handler):
        """Test OTP entry when no field detected."""
        # Mock page with no OTP fields
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.query_selector_all = AsyncMock(return_value=[])
        mock_page.text_content = AsyncMock(return_value="No OTP form")
        
        with pytest.raises(OTPVerificationError, match="Could not detect OTP input field"):
            await handler.enter_otp(mock_page, "123456")


class TestModeSwitching:
    """Test headless/headed mode switching."""
    
    @pytest.fixture
    def handler(self):
        """Create OTPHandler instance."""
        voice_callback = AsyncMock()
        return OTPHandler(voice_callback)
    
    @pytest.fixture
    def mock_session(self):
        """Create mock BrowserSession."""
        session = Mock()
        session.session_id = "test-session-id"
        session.profile_name = "test-profile"
        session.domain = "example.com"
        session.is_headless = True
        session.state = SessionState.ACTIVE
        
        # Mock page
        mock_page = AsyncMock()
        mock_page.url = "https://example.com/otp"
        mock_page.goto = AsyncMock()
        session.playwright_page = mock_page
        
        return session
    
    @pytest.fixture
    def mock_session_manager(self):
        """Create mock SessionManager."""
        manager = AsyncMock()
        manager.close_session = AsyncMock()
        manager.create_session = AsyncMock()
        return manager
    
    @pytest.mark.asyncio
    async def test_switch_to_headed_mode(self, handler, mock_session, mock_session_manager):
        """Test switching to headed mode."""
        # Mock new headed session
        headed_session = Mock()
        headed_session.session_id = "headed-session-id"
        headed_session.profile_name = "test-profile"
        headed_session.domain = "example.com"
        headed_session.is_headless = False
        headed_session.playwright_page = AsyncMock()
        headed_session.playwright_page.goto = AsyncMock()
        
        mock_session_manager.create_session.return_value = headed_session
        
        result = await handler.switch_to_headed_mode(mock_session, mock_session_manager)
        
        assert result == headed_session
        assert result.is_headless is False
        mock_session_manager.close_session.assert_called_once_with(mock_session.session_id)
        mock_session_manager.create_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_switch_to_headless_mode(self, handler, mock_session, mock_session_manager):
        """Test switching to headless mode."""
        # Set session to headed
        mock_session.is_headless = False
        
        # Mock new headless session
        headless_session = Mock()
        headless_session.session_id = "headless-session-id"
        headless_session.profile_name = "test-profile"
        headless_session.domain = "example.com"
        headless_session.is_headless = True
        headless_session.playwright_page = AsyncMock()
        headless_session.playwright_page.goto = AsyncMock()
        
        mock_session_manager.create_session.return_value = headless_session
        
        result = await handler.switch_to_headless_mode(mock_session, mock_session_manager)
        
        assert result == headless_session
        assert result.is_headless is True
        mock_session_manager.close_session.assert_called_once_with(mock_session.session_id)
        mock_session_manager.create_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_switch_mode_preserves_url(self, handler, mock_session, mock_session_manager):
        """Test that mode switching preserves current URL."""
        original_url = "https://example.com/otp"
        mock_session.playwright_page.url = original_url
        
        # Mock new session
        new_session = Mock()
        new_session.session_id = "new-session-id"
        new_session.profile_name = "test-profile"
        new_session.domain = "example.com"
        new_session.is_headless = False
        new_session.playwright_page = AsyncMock()
        new_session.playwright_page.goto = AsyncMock()
        
        mock_session_manager.create_session.return_value = new_session
        
        await handler.switch_to_headed_mode(mock_session, mock_session_manager)
        
        # Verify navigation to original URL
        new_session.playwright_page.goto.assert_called_once()
        call_args = new_session.playwright_page.goto.call_args
        assert call_args[0][0] == original_url


class TestOTPVerificationWorkflow:
    """Test complete OTP verification workflow."""
    
    @pytest.fixture
    def handler(self):
        """Create OTPHandler instance."""
        voice_callback = AsyncMock()
        input_callback = AsyncMock(return_value="123456")
        return OTPHandler(voice_callback, input_callback)
    
    @pytest.fixture
    def mock_session(self):
        """Create mock BrowserSession."""
        session = Mock()
        session.session_id = "test-session-id"
        session.profile_name = "test-profile"
        session.domain = "example.com"
        session.is_headless = True
        session.state = SessionState.ACTIVE
        
        # Mock page with OTP form
        mock_page = AsyncMock()
        mock_page.url = "https://example.com/otp"
        mock_page.text_content = AsyncMock(return_value="Enter verification code")
        
        # Mock OTP field
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_element.get_attribute = AsyncMock(return_value='otp-input')
        mock_element.fill = AsyncMock()
        mock_element.input_value = AsyncMock(return_value="123456")
        
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        session.playwright_page = mock_page
        
        return session
    
    @pytest.fixture
    def mock_session_manager(self):
        """Create mock SessionManager."""
        manager = AsyncMock()
        manager.close_session = AsyncMock()
        manager.create_session = AsyncMock()
        return manager
    
    @pytest.mark.asyncio
    async def test_handle_otp_verification_success(self, handler, mock_session, mock_session_manager):
        """Test successful OTP verification workflow."""
        # Mock headed session
        headed_session = Mock()
        headed_session.session_id = "headed-session-id"
        headed_session.profile_name = "test-profile"
        headed_session.domain = "example.com"
        headed_session.is_headless = False
        headed_session.playwright_page = mock_session.playwright_page
        
        # Mock headless session (after verification)
        headless_session = Mock()
        headless_session.session_id = "headless-session-id"
        headless_session.profile_name = "test-profile"
        headless_session.domain = "example.com"
        headless_session.is_headless = True
        headless_session.playwright_page = mock_session.playwright_page
        
        mock_session_manager.create_session.side_effect = [headed_session, headless_session]
        
        result = await handler.handle_otp_verification(
            mock_session,
            mock_session_manager,
            show_browser=True
        )
        
        assert result == headless_session
        assert result.is_headless is True
    
    @pytest.mark.asyncio
    async def test_handle_otp_verification_no_form(self, handler, mock_session, mock_session_manager):
        """Test OTP verification when no form detected."""
        # Mock page without OTP form
        mock_session.playwright_page.text_content = AsyncMock(return_value="Regular page")
        mock_session.playwright_page.query_selector = AsyncMock(return_value=None)
        
        with pytest.raises(OTPVerificationError, match="No OTP form detected"):
            await handler.handle_otp_verification(mock_session, mock_session_manager)


class TestVerificationSuccess:
    """Test verification success checking."""
    
    @pytest.fixture
    def handler(self):
        """Create OTPHandler instance."""
        return OTPHandler()
    
    @pytest.mark.asyncio
    async def test_check_verification_success_form_disappeared(self, handler):
        """Test verification success when OTP form disappears."""
        # Mock page without OTP form (verification successful)
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.text_content = AsyncMock(return_value="Welcome! You are logged in.")
        
        result = await handler._check_verification_success(mock_page)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_verification_success_with_success_message(self, handler):
        """Test verification success with success message."""
        # Mock page with success message
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.text_content = AsyncMock(return_value="Verification successful! Redirecting...")
        
        result = await handler._check_verification_success(mock_page)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_verification_failure_with_error(self, handler):
        """Test verification failure with error message."""
        # Mock page with error message
        mock_page = AsyncMock()
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        mock_page.text_content = AsyncMock(return_value="Invalid verification code. Please try again.")
        
        result = await handler._check_verification_success(mock_page)
        
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
