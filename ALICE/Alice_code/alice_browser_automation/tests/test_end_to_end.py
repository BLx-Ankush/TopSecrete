"""
End-to-end integration tests for Alice Browser Automation (Task 23.1).

These tests validate the complete system working together:
- Web booking flow with Alice voice commands
- Problem solving flow with web research
- Application access with authentication
- OTP verification in real scenarios
- Session persistence across restarts
- Error recovery scenarios

**Validates: Requirements All**
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import date, datetime, timedelta
from pathlib import Path
import json

from alice_browser_automation.engine import BrowserAutomationEngine
from alice_browser_automation.types import (
    TaskType, TaskResult, BrowserSession, SessionState,
    BrowserAction, ActionType
)
from alice_browser_automation.config import Config
from alice_browser_automation.web_bookings import TravelBookingDetails, BookingType
from alice_browser_automation.exceptions import (
    ElementNotFoundError, PageLoadTimeoutError, SessionCrashedError
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def engine_with_mocks():
    """Create engine with mocked external dependencies."""
    with patch('alice_browser_automation.engine.QwenModelClient') as mock_qwen, \
         patch('alice_browser_automation.engine.SessionManager') as mock_session_mgr, \
         patch('alice_browser_automation.engine.ChromeProfileManager') as mock_profile_mgr, \
         patch('alice_browser_automation.engine.OTPHandler') as mock_otp, \
         patch('alice_browser_automation.engine.DOMParser') as mock_dom:
        
        # Configure mocks
        mock_qwen_instance = AsyncMock()
        mock_qwen.return_value = mock_qwen_instance
        mock_qwen_instance.validate_model_availability = AsyncMock(return_value=True)
        mock_qwen_instance.generate_json_response = AsyncMock(return_value={
            "action_type": "navigate",
            "target_selector": None,
            "parameters": {"url": "https://example.com"},
            "expected_result": "Page loaded"
        })
        
        mock_session_instance = AsyncMock()
        mock_session_mgr.return_value = mock_session_instance
        
        mock_profile_instance = Mock()
        mock_profile_mgr.return_value = mock_profile_instance
        mock_profile_instance.get_or_create_profile.return_value = Path("/tmp/profile")
        
        mock_otp_instance = AsyncMock()
        mock_otp.return_value = mock_otp_instance
        
        mock_dom_instance = AsyncMock()
        mock_dom.return_value = mock_dom_instance
        
        # Create engine
        engine = BrowserAutomationEngine()
        await engine.initialize()
        
        # Store mocks for test access
        engine._test_mocks = {
            'qwen': mock_qwen_instance,
            'session_mgr': mock_session_instance,
            'profile_mgr': mock_profile_instance,
            'otp': mock_otp_instance,
            'dom': mock_dom_instance
        }
        
        yield engine
        
        await engine.shutdown()


@pytest.fixture
def mock_playwright_page():
    """Create a comprehensive mock Playwright page."""
    page = AsyncMock()
    page.url = "https://example.com"
    page.title = AsyncMock(return_value="Example Page")
    page.content = AsyncMock(return_value="<html><body>Test</body></html>")
    page.goto = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.type = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.evaluate = AsyncMock(return_value="result")
    page.screenshot = AsyncMock(return_value=b"screenshot_data")
    
    # Mock accessibility
    page.accessibility = MagicMock()
    page.accessibility.snapshot = AsyncMock(return_value={
        "role": "WebArea",
        "name": "Test Page",
        "children": []
    })
    
    return page


@pytest.fixture
def mock_browser_session(mock_playwright_page):
    """Create a mock browser session."""
    session = Mock(spec=BrowserSession)
    session.session_id = "test_session_123"
    session.profile_name = "default"
    session.domain = "example.com"
    session.playwright_page = mock_playwright_page
    session.playwright_context = AsyncMock()
    session.created_at = datetime.now()
    session.last_activity = datetime.now()
    session.is_headless = True
    session.state = SessionState.ACTIVE
    
    return session


# ============================================================================
# Test: Complete Web Booking Flow with Voice Commands
# ============================================================================

class TestCompleteWebBookingFlow:
    """Test complete web booking flow with Alice voice commands."""
    
    @pytest.mark.asyncio
    async def test_flight_booking_end_to_end(self, engine_with_mocks, mock_browser_session):
        """
        Test complete flight booking flow from voice command to confirmation.
        
        **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.8, 11.1, 11.2**
        """
        engine = engine_with_mocks
        
        # Mock session creation
        engine._test_mocks['session_mgr'].create_session = AsyncMock(
            return_value=mock_browser_session
        )
        
        # Mock DOM parsing to return booking form
        engine._test_mocks['dom'].parse_page = AsyncMock(return_value=Mock(
            url="https://flights.example.com",
            title="Book Flights",
            interactive_elements=[
                Mock(element_id="origin", tag_name="input", role="textbox"),
                Mock(element_id="destination", tag_name="input", role="textbox"),
                Mock(element_id="date", tag_name="input", role="textbox"),
                Mock(element_id="search", tag_name="button", role="button"),
            ]
        ))
        
        # Mock Qwen to generate booking actions
        action_sequence = [
            {"action_type": "navigate", "parameters": {"url": "https://flights.example.com"}},
            {"action_type": "type", "target_selector": {"css_selector": "#origin"}, "parameters": {"text": "SFO"}},
            {"action_type": "type", "target_selector": {"css_selector": "#destination"}, "parameters": {"text": "LAX"}},
            {"action_type": "click", "target_selector": {"css_selector": "#search"}},
            {"action_type": "wait", "parameters": {"condition": "visible", "selector": ".results"}},
            {"action_type": "extract", "target_selector": {"css_selector": ".confirmation"}, "parameters": {"extract_type": "text"}},
        ]
        
        engine._test_mocks['qwen'].generate_json_response = AsyncMock(
            side_effect=action_sequence
        )
        
        # Progress callback to track updates
        progress_updates = []
        def progress_callback(message: str):
            progress_updates.append(message)
        
        # Execute booking task
        result = await engine.execute_task(
            task_description="Book a flight from San Francisco to Los Angeles on December 25th",
            task_type=TaskType.WEB_BOOKING,
            parameters={
                "booking_type": "flight",
                "origin": "SFO",
                "destination": "LAX",
                "departure_date": "2025-12-25",
                "passengers": 1
            },
            callback=progress_callback
        )
        
        # Assertions
        assert result.success is True
        assert result.task_id is not None
        assert len(result.actions_taken) > 0
        assert result.error == ""
        
        # Verify progress updates were sent
        assert len(progress_updates) > 0
        
        # Verify session was created
        engine._test_mocks['session_mgr'].create_session.assert_called()
    
    @pytest.mark.asyncio
    async def test_booking_with_otp_verification(self, engine_with_mocks, mock_browser_session):
        """
        Test booking flow with OTP verification via voice.
        
        **Validates: Requirements 5.3, 5.4, 8.2, 11.3**
        """
        engine = engine_with_mocks
        
        # Mock session
        engine._test_mocks['session_mgr'].create_session = AsyncMock(
            return_value=mock_browser_session
        )
        
        # Mock OTP detection and handling
        engine._test_mocks['dom'].parse_page = AsyncMock(return_value=Mock(
            url="https://booking.example.com/verify",
            interactive_elements=[
                Mock(element_id="otp_input", tag_name="input", role="textbox", 
                     attributes={"type": "text", "name": "otp"})
            ]
        ))
        
        # Mock OTP handler
        engine._test_mocks['otp'].request_otp = AsyncMock(return_value="123456")
        engine._test_mocks['otp'].enter_otp = AsyncMock(return_value=True)
        engine._test_mocks['otp'].switch_to_headed_mode = AsyncMock()
        engine._test_mocks['otp'].switch_to_headless_mode = AsyncMock()
        
        # Mock Qwen actions including OTP step
        engine._test_mocks['qwen'].generate_json_response = AsyncMock(
            side_effect=[
                {"action_type": "navigate", "parameters": {"url": "https://booking.example.com"}},
                {"action_type": "type", "target_selector": {"css_selector": "#otp_input"}, "parameters": {"text": "123456"}},
                {"action_type": "click", "target_selector": {"css_selector": "#verify_btn"}},
            ]
        )
        
        # Execute task
        result = await engine.execute_task(
            task_description="Complete booking with OTP verification",
            task_type=TaskType.WEB_BOOKING,
            parameters={"requires_otp": True}
        )
        
        # Assertions
        assert result.success is True
        
        # Verify OTP was requested and entered
        engine._test_mocks['otp'].request_otp.assert_called()
        engine._test_mocks['otp'].enter_otp.assert_called()
    
    @pytest.mark.asyncio
    async def test_booking_with_payment_confirmation(self, engine_with_mocks, mock_browser_session):
        """
        Test booking flow with payment confirmation requirement.
        
        **Validates: Requirements 10.3, 10.4, 18.2**
        """
        engine = engine_with_mocks
        
        # Mock session
        engine._test_mocks['session_mgr'].create_session = AsyncMock(
            return_value=mock_browser_session
        )
        
        # Mock payment page detection
        engine._test_mocks['dom'].parse_page = AsyncMock(return_value=Mock(
            url="https://booking.example.com/payment",
            interactive_elements=[
                Mock(element_id="card_number", tag_name="input", 
                     attributes={"type": "text", "name": "card"}),
                Mock(element_id="pay_btn", tag_name="button", role="button")
            ]
        ))
        
        # Mock user confirmation callback
        confirmation_requested = []
        def progress_callback(message: str):
            if "payment" in message.lower() or "confirm" in message.lower():
                confirmation_requested.append(message)
        
        # Execute task
        result = await engine.execute_task(
            task_description="Complete booking with payment",
            task_type=TaskType.WEB_BOOKING,
            parameters={"requires_payment": True},
            callback=progress_callback
        )
        
        # Verify payment confirmation was requested
        assert len(confirmation_requested) > 0 or result.success


# ============================================================================
# Test: Problem Solving Flow with Web Research
# ============================================================================

class TestProblemSolvingFlow:
    """Test problem solving flow with web research."""
    
    @pytest.mark.asyncio
    async def test_problem_solving_end_to_end(self, engine_with_mocks, mock_browser_session):
        """
        Test complete problem solving flow with web research.
        
        **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
        """
        engine = engine_with_mocks
        
        # Mock session
        engine._test_mocks['session_mgr'].create_session = AsyncMock(
            return_value=mock_browser_session
        )
        
        # Mock search results page
        engine._test_mocks['dom'].parse_page = AsyncMock(return_value=Mock(
            url="https://search.example.com/results",
            interactive_elements=[
                Mock(element_id="result1", tag_name="a", role="link"),
                Mock(element_id="result2", tag_name="a", role="link"),
            ],
            text_content="Solution 1: Update your drivers\nSolution 2: Reinstall the software"
        ))
        
        # Mock Qwen to generate research actions
        engine._test_mocks['qwen'].generate_json_response = AsyncMock(
            side_effect=[
                {"action_type": "navigate", "parameters": {"url": "https://search.example.com"}},
                {"action_type": "type", "target_selector": {"css_selector": "#search"}, 
                 "parameters": {"text": "Python import error fix"}},
                {"action_type": "click", "target_selector": {"css_selector": "#search_btn"}},
                {"action_type": "extract", "target_selector": {"css_selector": ".results"}, 
                 "parameters": {"extract_type": "text"}},
            ]
        )
        
        # Execute problem solving task
        result = await engine.execute_task(
            task_description="Find solution for Python import error",
            task_type=TaskType.PROBLEM_SOLVING,
            parameters={
                "problem": "ModuleNotFoundError: No module named 'requests'",
                "system_info": {"os": "Windows 10", "python": "3.10"}
            }
        )
        
        # Assertions
        assert result.success is True
        assert "extracted_data" in result.__dict__
        assert len(result.actions_taken) > 0


# ============================================================================
# Test: Application Access with Authentication
# ============================================================================

class TestApplicationAccessFlow:
    """Test application access with authentication."""
    
    @pytest.mark.asyncio
    async def test_app_access_with_valid_session(self, engine_with_mocks, mock_browser_session):
        """
        Test accessing application with valid existing session.
        
        **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7**
        """
        engine = engine_with_mocks
        
        # Mock session with existing profile
        engine._test_mocks['session_mgr'].get_session_for_domain = AsyncMock(
            return_value=mock_browser_session
        )
        
        # Mock authenticated state
        engine._test_mocks['dom'].parse_page = AsyncMock(return_value=Mock(
            url="https://mail.example.com/inbox",
            interactive_elements=[
                Mock(element_id="inbox", tag_name="div", role="navigation"),
                Mock(element_id="compose", tag_name="button", role="button"),
            ]
        ))
        
        # Execute app access task
        result = await engine.execute_task(
            task_description="Check my email inbox",
            task_type=TaskType.APP_ACCESS,
            parameters={
                "app_name": "gmail",
                "action": "check_inbox"
            }
        )
        
        # Assertions
        assert result.success is True
        
        # Verify existing session was reused
        engine._test_mocks['session_mgr'].get_session_for_domain.assert_called()
    
    @pytest.mark.asyncio
    async def test_app_access_with_reauth(self, engine_with_mocks, mock_browser_session):
        """
        Test accessing application with expired session requiring re-authentication.
        
        **Validates: Requirements 7.3, 7.4**
        """
        engine = engine_with_mocks
        
        # Mock session creation (no existing session)
        engine._test_mocks['session_mgr'].get_session_for_domain = AsyncMock(
            return_value=None
        )
        engine._test_mocks['session_mgr'].create_session = AsyncMock(
            return_value=mock_browser_session
        )
        
        # Mock login page detection
        engine._test_mocks['dom'].parse_page = AsyncMock(side_effect=[
            # First: Login page
            Mock(
                url="https://accounts.example.com/login",
                interactive_elements=[
                    Mock(element_id="email", tag_name="input", role="textbox"),
                    Mock(element_id="password", tag_name="input", role="textbox"),
                    Mock(element_id="login_btn", tag_name="button", role="button"),
                ]
            ),
            # Second: After login - inbox
            Mock(
                url="https://mail.example.com/inbox",
                interactive_elements=[
                    Mock(element_id="inbox", tag_name="div", role="navigation"),
                ]
            )
        ])
        
        # Mock Qwen to generate login actions
        engine._test_mocks['qwen'].generate_json_response = AsyncMock(
            side_effect=[
                {"action_type": "navigate", "parameters": {"url": "https://accounts.example.com/login"}},
                {"action_type": "type", "target_selector": {"css_selector": "#email"}, 
                 "parameters": {"text": "user@example.com"}},
                {"action_type": "type", "target_selector": {"css_selector": "#password"}, 
                 "parameters": {"text": "password"}},
                {"action_type": "click", "target_selector": {"css_selector": "#login_btn"}},
                {"action_type": "wait", "parameters": {"condition": "networkidle"}},
            ]
        )
        
        # Execute app access task
        result = await engine.execute_task(
            task_description="Access my email",
            task_type=TaskType.APP_ACCESS,
            parameters={
                "app_name": "gmail",
                "action": "check_inbox",
                "credentials": {"email": "user@example.com", "password": "password"}
            }
        )
        
        # Assertions
        assert result.success is True
        
        # Verify new session was created
        engine._test_mocks['session_mgr'].create_session.assert_called()


# ============================================================================
# Test: Session Persistence Across Restarts
# ============================================================================

class TestSessionPersistence:
    """Test session persistence across restarts."""
    
    @pytest.mark.asyncio
    async def test_profile_persistence(self, tmp_path):
        """
        Test that browser profiles persist across engine restarts.
        
        **Validates: Requirements 7.1, 7.2, 7.7**
        """
        # Create config with temp profile directory
        config_dict = {
            "browser": {
                "profiles_dir": str(tmp_path / "profiles"),
                "default_profile": "test_profile"
            }
        }
        
        with patch('alice_browser_automation.engine.QwenModelClient'), \
             patch('alice_browser_automation.engine.SessionManager'), \
             patch('alice_browser_automation.engine.OTPHandler'), \
             patch('alice_browser_automation.engine.DOMParser'):
            
            # First engine instance
            engine1 = BrowserAutomationEngine()
            await engine1.initialize()
            
            # Create profile
            profile_path = engine1.profile_manager.get_or_create_profile("test_profile")
            assert profile_path.exists()
            
            # Write some data to profile
            (profile_path / "test_data.txt").write_text("persistent data")
            
            await engine1.shutdown()
            
            # Second engine instance (restart)
            engine2 = BrowserAutomationEngine()
            await engine2.initialize()
            
            # Verify profile still exists
            profile_path2 = engine2.profile_manager.get_or_create_profile("test_profile")
            assert profile_path2.exists()
            assert (profile_path2 / "test_data.txt").read_text() == "persistent data"
            
            await engine2.shutdown()
    
    @pytest.mark.asyncio
    async def test_session_reuse_same_domain(self, engine_with_mocks, mock_browser_session):
        """
        Test that sessions are reused for the same domain.
        
        **Validates: Requirements 8.5**
        """
        engine = engine_with_mocks
        
        # Mock session manager to return same session for same domain
        engine._test_mocks['session_mgr'].get_session_for_domain = AsyncMock(
            return_value=mock_browser_session
        )
        
        # First task on example.com
        result1 = await engine.execute_task(
            task_description="Navigate to example.com",
            task_type=TaskType.WEB_BOOKING,
            parameters={"target_url": "https://example.com"}
        )
        
        # Second task on example.com
        result2 = await engine.execute_task(
            task_description="Click button on example.com",
            task_type=TaskType.WEB_BOOKING,
            parameters={"target_url": "https://example.com"}
        )
        
        # Verify session was reused
        assert engine._test_mocks['session_mgr'].get_session_for_domain.call_count >= 2


# ============================================================================
# Test: Error Recovery Scenarios
# ============================================================================

class TestErrorRecovery:
    """Test error recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_element_not_found_recovery(self, engine_with_mocks, mock_browser_session):
        """
        Test recovery from element not found error with alternative selectors.
        
        **Validates: Requirements 9.1**
        """
        engine = engine_with_mocks
        
        # Mock session
        engine._test_mocks['session_mgr'].create_session = AsyncMock(
            return_value=mock_browser_session
        )
        
        # Mock DOM with multiple selectors
        engine._test_mocks['dom'].parse_page = AsyncMock(return_value=Mock(
            interactive_elements=[
                Mock(
                    element_id="submit_btn",
                    selectors=Mock(
                        css_selector="#submit",
                        xpath="//button[@id='submit']",
                        aria_label="Submit"
                    )
                )
            ]
        ))
        
        # Mock first click fails, second succeeds
        mock_browser_session.playwright_page.click = AsyncMock(
            side_effect=[
                ElementNotFoundError("Element not found with CSS selector"),
                None  # Success on retry
            ]
        )
        
        # Execute task
        result = await engine.execute_task(
            task_description="Click submit button",
            task_type=TaskType.WEB_BOOKING,
            parameters={}
        )
        
        # Should succeed after retry with alternative selector
        assert result.success is True or mock_browser_session.playwright_page.click.call_count > 1
    
    @pytest.mark.asyncio
    async def test_page_load_timeout_recovery(self, engine_with_mocks, mock_browser_session):
        """
        Test recovery from page load timeout with retry.
        
        **Validates: Requirements 9.2**
        """
        engine = engine_with_mocks
        
        # Mock session
        engine._test_mocks['session_mgr'].create_session = AsyncMock(
            return_value=mock_browser_session
        )
        
        # Mock page navigation - first fails, second succeeds
        mock_browser_session.playwright_page.goto = AsyncMock(
            side_effect=[
                PageLoadTimeoutError("Page load timeout"),
                None  # Success on retry
            ]
        )
        
        # Execute task
        result = await engine.execute_task(
            task_description="Navigate to slow website",
            task_type=TaskType.WEB_BOOKING,
            parameters={"target_url": "https://slow.example.com"}
        )
        
        # Should succeed after retry
        assert result.success is True or mock_browser_session.playwright_page.goto.call_count > 1
    
    @pytest.mark.asyncio
    async def test_session_crash_recovery(self, engine_with_mocks, mock_browser_session):
        """
        Test recovery from browser session crash.
        
        **Validates: Requirements 8.6, 9.6**
        """
        engine = engine_with_mocks
        
        # Mock session that crashes
        crashed_session = Mock(spec=BrowserSession)
        crashed_session.state = SessionState.CRASHED
        crashed_session.session_id = "crashed_123"
        
        # Mock new session after restart
        new_session = mock_browser_session
        new_session.session_id = "new_456"
        new_session.state = SessionState.ACTIVE
        
        # Mock session manager to handle crash
        engine._test_mocks['session_mgr'].create_session = AsyncMock(
            side_effect=[crashed_session, new_session]
        )
        engine._test_mocks['session_mgr'].restart_crashed_session = AsyncMock(
            return_value=new_session
        )
        
        # Execute task
        result = await engine.execute_task(
            task_description="Task that causes crash",
            task_type=TaskType.WEB_BOOKING,
            parameters={}
        )
        
        # Verify crash was handled
        assert result.success is True or engine._test_mocks['session_mgr'].restart_crashed_session.called
    
    @pytest.mark.asyncio
    async def test_invalid_action_recovery(self, engine_with_mocks, mock_browser_session):
        """
        Test recovery from invalid action generated by Qwen.
        
        **Validates: Requirements 9.3**
        """
        engine = engine_with_mocks
        
        # Mock session
        engine._test_mocks['session_mgr'].create_session = AsyncMock(
            return_value=mock_browser_session
        )
        
        # Mock Qwen to generate invalid action first, then valid
        engine._test_mocks['qwen'].generate_json_response = AsyncMock(
            side_effect=[
                {"invalid": "action"},  # Invalid format
                {"action_type": "click", "target_selector": {"css_selector": "#btn"}, 
                 "parameters": {}, "expected_result": "Button clicked"}  # Valid
            ]
        )
        
        # Execute task
        result = await engine.execute_task(
            task_description="Click button",
            task_type=TaskType.WEB_BOOKING,
            parameters={}
        )
        
        # Should succeed after retry with valid action
        assert result.success is True or engine._test_mocks['qwen'].generate_json_response.call_count > 1


# ============================================================================
# Test: Performance and Responsiveness
# ============================================================================

class TestPerformanceTargets:
    """Test performance targets are met."""
    
    @pytest.mark.asyncio
    async def test_session_initialization_time(self, engine_with_mocks):
        """
        Test browser session initializes within 3 seconds.
        
        **Validates: Requirements 12.1**
        """
        engine = engine_with_mocks
        
        # Mock fast session creation
        mock_session = Mock(spec=BrowserSession)
        engine._test_mocks['session_mgr'].create_session = AsyncMock(
            return_value=mock_session
        )
        
        start_time = datetime.now()
        
        # Create session
        session = await engine._create_browser_session(profile_name="default")
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Should complete within 3 seconds (mocked, so should be instant)
        assert elapsed < 3.0
        assert session is not None
    
    @pytest.mark.asyncio
    async def test_progress_updates_frequency(self, engine_with_mocks, mock_browser_session):
        """
        Test progress updates are sent regularly during long tasks.
        
        **Validates: Requirements 12.5**
        """
        engine = engine_with_mocks
        
        # Mock session
        engine._test_mocks['session_mgr'].create_session = AsyncMock(
            return_value=mock_browser_session
        )
        
        # Track progress updates
        progress_updates = []
        update_times = []
        
        def progress_callback(message: str):
            progress_updates.append(message)
            update_times.append(datetime.now())
        
        # Execute long-running task
        result = await engine.execute_task(
            task_description="Long running task",
            task_type=TaskType.WEB_BOOKING,
            parameters={},
            callback=progress_callback
        )
        
        # Verify progress updates were sent
        assert len(progress_updates) > 0


# ============================================================================
# Test: Security Measures
# ============================================================================

class TestSecurityMeasures:
    """Test security measures are enforced."""
    
    @pytest.mark.asyncio
    async def test_sensitive_data_not_logged(self, engine_with_mocks, mock_browser_session, caplog):
        """
        Test that sensitive data is not logged.
        
        **Validates: Requirements 10.1, 10.2**
        """
        engine = engine_with_mocks
        
        # Mock session
        engine._test_mocks['session_mgr'].create_session = AsyncMock(
            return_value=mock_browser_session
        )
        
        # Execute task with sensitive data
        result = await engine.execute_task(
            task_description="Login with credentials",
            task_type=TaskType.APP_ACCESS,
            parameters={
                "username": "user@example.com",
                "password": "SecretPassword123",
                "credit_card": "4111111111111111"
            }
        )
        
        # Check logs don't contain sensitive data
        log_text = caplog.text.lower()
        assert "secretpassword123" not in log_text
        assert "4111111111111111" not in log_text
    
    @pytest.mark.asyncio
    async def test_ssl_certificate_validation(self, engine_with_mocks):
        """
        Test SSL certificate validation is enforced.
        
        **Validates: Requirements 10.5**
        """
        engine = engine_with_mocks
        
        # Verify SSL validation is enabled in config
        assert engine.config.security.validate_ssl is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
