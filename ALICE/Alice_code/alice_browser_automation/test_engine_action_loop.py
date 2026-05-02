"""
Unit tests for Browser Automation Engine Action Execution Loop (Task 13.4).

Tests the action execution loop including action processing, DOM re-parsing,
action verification, error handling integration, and various action types.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime

from alice_browser_automation.engine import BrowserAutomationEngine
from alice_browser_automation.config import Config
from alice_browser_automation.types import (
    BrowserTask, BrowserAction, BrowserSession, TaskType, ActionType,
    ElementSelectors, StructuredDOM, SessionState
)
from alice_browser_automation.exceptions import (
    BrowserAutomationError, ElementNotFoundError
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
    engine.dom_parser = AsyncMock()
    engine.livekit_bridge = AsyncMock()
    engine.error_handler = AsyncMock()
    
    return engine


@pytest.fixture
def mock_session():
    """Create a mock browser session."""
    mock_page = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.goto = AsyncMock()
    mock_page.query_selector = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.select_option = AsyncMock()
    mock_page.evaluate = AsyncMock()
    mock_page.text_content = AsyncMock(return_value="Page content")
    
    return BrowserSession(
        session_id="test-session-123",
        profile_name="default",
        domain="example.com",
        playwright_context=Mock(),
        playwright_page=mock_page,
        created_at=datetime.now(),
        last_activity=datetime.now(),
        is_headless=True,
        state=SessionState.ACTIVE
    )


@pytest.fixture
def mock_browser_task():
    """Create a mock browser task."""
    return BrowserTask(
        task_id="task-123",
        description="Test task",
        task_type=TaskType.WEB_BOOKING,
        parameters={"test": "param"},
        target_url="https://example.com",
        expected_outcome="Task completed"
    )


@pytest.fixture
def mock_dom():
    """Create a mock StructuredDOM."""
    return StructuredDOM(
        url="https://example.com",
        title="Test Page",
        interactive_elements=[],
        text_content="Test content",
        metadata={},
        timestamp=datetime.now()
    )


@pytest.fixture
def mock_element_selector():
    """Create a mock ElementSelectors."""
    return ElementSelectors(
        css_selector="button.submit",
        xpath="//button[@class='submit']",
        aria_label="Submit",
        test_id="submit-btn",
        text_content="Submit"
    )


# ============================================================================
# Test: _execute_action_loop
# ============================================================================

class TestExecuteActionLoop:
    """Test _execute_action_loop method."""
    
    @pytest.mark.asyncio
    async def test_execute_action_loop_success(
        self, initialized_engine, mock_browser_task, mock_session, mock_dom
    ):
        """Test successful action loop execution."""
        # Mock DOM parser
        initialized_engine.dom_parser.parse_page = AsyncMock(return_value=mock_dom)
        
        # Mock action plan generation
        mock_actions = [
            BrowserAction(
                action_type=ActionType.NAVIGATE,
                parameters={"url": "https://example.com"},
                expected_result="Page loaded"
            ),
            BrowserAction(
                action_type=ActionType.CLICK,
                target_selector=ElementSelectors(
                    css_selector="button.submit",
                    xpath="//button",
                    aria_label="Submit"
                ),
                expected_result="Form submitted"
            )
        ]
        initialized_engine.livekit_bridge.generate_action_plan = AsyncMock(
            return_value=mock_actions
        )
        
        # Mock action execution
        initialized_engine._execute_single_action = AsyncMock(
            return_value={"success": True, "extracted_data": {}}
        )
        
        # Mock action verification
        initialized_engine._verify_action_result = AsyncMock(return_value=True)
        
        # Execute action loop
        result = await initialized_engine._execute_action_loop(
            task=mock_browser_task,
            session=mock_session,
            progress_callback=Mock()
        )
        
        # Assertions
        assert result.success is True
        assert len(result.actions_taken) == 2
        assert initialized_engine.dom_parser.parse_page.call_count >= 2  # Initial + after each action
        initialized_engine.livekit_bridge.generate_action_plan.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_action_loop_with_target_url(
        self, initialized_engine, mock_browser_task, mock_session, mock_dom
    ):
        """Test action loop navigates to target URL."""
        initialized_engine.dom_parser.parse_page = AsyncMock(return_value=mock_dom)
        initialized_engine.livekit_bridge.generate_action_plan = AsyncMock(return_value=[])
        initialized_engine._execute_navigate_action = AsyncMock()
        
        # Execute action loop
        await initialized_engine._execute_action_loop(
            task=mock_browser_task,
            session=mock_session,
            progress_callback=Mock()
        )
        
        # Verify navigation was called (check call arguments without comparing Mock objects)
        assert initialized_engine._execute_navigate_action.call_count == 1
        call_args = initialized_engine._execute_navigate_action.call_args[0]
        assert call_args[0] == mock_session.playwright_page
        assert call_args[1] == mock_browser_task.target_url
    
    @pytest.mark.asyncio
    async def test_execute_action_loop_handles_cancellation(
        self, initialized_engine, mock_browser_task, mock_session, mock_dom
    ):
        """Test action loop handles task cancellation."""
        initialized_engine.dom_parser.parse_page = AsyncMock(return_value=mock_dom)
        
        # Mock action plan with multiple actions
        mock_actions = [
            BrowserAction(action_type=ActionType.CLICK, expected_result="Clicked"),
            BrowserAction(action_type=ActionType.TYPE, expected_result="Typed"),
        ]
        initialized_engine.livekit_bridge.generate_action_plan = AsyncMock(
            return_value=mock_actions
        )
        
        # Set cancellation flag
        initialized_engine._task_cancellation_flags[mock_browser_task.task_id] = True
        
        # Execute action loop
        result = await initialized_engine._execute_action_loop(
            task=mock_browser_task,
            session=mock_session,
            progress_callback=Mock()
        )
        
        # Assertions
        assert result.success is False
        assert "cancelled" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_action_loop_extracts_data(
        self, initialized_engine, mock_browser_task, mock_session, mock_dom
    ):
        """Test action loop extracts and aggregates data."""
        initialized_engine.dom_parser.parse_page = AsyncMock(return_value=mock_dom)
        
        mock_actions = [
            BrowserAction(action_type=ActionType.EXTRACT, expected_result="Extracted")
        ]
        initialized_engine.livekit_bridge.generate_action_plan = AsyncMock(
            return_value=mock_actions
        )
        
        # Mock action execution with extracted data
        initialized_engine._execute_single_action = AsyncMock(
            return_value={
                "success": True,
                "extracted_data": {"confirmation_number": "ABC123"}
            }
        )
        initialized_engine._verify_action_result = AsyncMock(return_value=True)
        
        # Execute action loop
        result = await initialized_engine._execute_action_loop(
            task=mock_browser_task,
            session=mock_session,
            progress_callback=Mock()
        )
        
        # Assertions
        assert result.success is True
        assert "confirmation_number" in result.extracted_data
        assert result.extracted_data["confirmation_number"] == "ABC123"
    
    @pytest.mark.asyncio
    async def test_execute_action_loop_handles_error(
        self, initialized_engine, mock_browser_task, mock_session, mock_dom
    ):
        """Test action loop handles execution errors."""
        initialized_engine.dom_parser.parse_page = AsyncMock(return_value=mock_dom)
        initialized_engine.livekit_bridge.generate_action_plan = AsyncMock(
            side_effect=Exception("Action plan generation failed")
        )
        
        # Execute action loop
        result = await initialized_engine._execute_action_loop(
            task=mock_browser_task,
            session=mock_session,
            progress_callback=Mock()
        )
        
        # Assertions
        assert result.success is False
        assert "failed" in result.error.lower()


# ============================================================================
# Test: _execute_single_action
# ============================================================================

class TestExecuteSingleAction:
    """Test _execute_single_action method."""
    
    @pytest.mark.asyncio
    async def test_execute_navigate_action(
        self, initialized_engine, mock_session
    ):
        """Test executing navigate action."""
        action = BrowserAction(
            action_type=ActionType.NAVIGATE,
            parameters={"url": "https://example.com"}
        )
        
        initialized_engine._execute_navigate_action = AsyncMock()
        
        result = await initialized_engine._execute_single_action(
            action=action,
            page=mock_session.playwright_page,
            session=mock_session,
            progress_callback=Mock()
        )
        
        assert result["success"] is True
        initialized_engine._execute_navigate_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_click_action(
        self, initialized_engine, mock_session, mock_element_selector
    ):
        """Test executing click action."""
        action = BrowserAction(
            action_type=ActionType.CLICK,
            target_selector=mock_element_selector
        )
        
        initialized_engine._execute_click_action = AsyncMock()
        
        result = await initialized_engine._execute_single_action(
            action=action,
            page=mock_session.playwright_page,
            session=mock_session,
            progress_callback=Mock()
        )
        
        assert result["success"] is True
        initialized_engine._execute_click_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_type_action(
        self, initialized_engine, mock_session, mock_element_selector
    ):
        """Test executing type action."""
        action = BrowserAction(
            action_type=ActionType.TYPE,
            target_selector=mock_element_selector,
            parameters={"text": "test input", "clear_first": True}
        )
        
        initialized_engine._execute_type_action = AsyncMock()
        
        result = await initialized_engine._execute_single_action(
            action=action,
            page=mock_session.playwright_page,
            session=mock_session,
            progress_callback=Mock()
        )
        
        assert result["success"] is True
        initialized_engine._execute_type_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_extract_action(
        self, initialized_engine, mock_session, mock_element_selector
    ):
        """Test executing extract action."""
        action = BrowserAction(
            action_type=ActionType.EXTRACT,
            target_selector=mock_element_selector,
            parameters={"extract_type": "text"}
        )
        
        initialized_engine._execute_extract_action = AsyncMock(
            return_value={"extracted_text": "Test data"}
        )
        
        result = await initialized_engine._execute_single_action(
            action=action,
            page=mock_session.playwright_page,
            session=mock_session,
            progress_callback=Mock()
        )
        
        assert result["success"] is True
        assert "extracted_text" in result["extracted_data"]
    
    @pytest.mark.asyncio
    async def test_execute_action_with_retry(
        self, initialized_engine, mock_session
    ):
        """Test action retry on failure."""
        action = BrowserAction(
            action_type=ActionType.CLICK,
            target_selector=ElementSelectors(
                css_selector="button",
                xpath="//button",
                aria_label="Click"
            )
        )
        
        # Mock to fail first time, succeed second time
        call_count = 0
        async def mock_click(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt failed")
            # Second attempt succeeds (no exception)
        
        initialized_engine._execute_click_action = mock_click
        
        result = await initialized_engine._execute_single_action(
            action=action,
            page=mock_session.playwright_page,
            session=mock_session,
            progress_callback=Mock()
        )
        
        assert result["success"] is True
        assert call_count == 2  # Failed once, succeeded on retry


# ============================================================================
# Test: Action-Specific Methods
# ============================================================================

class TestActionSpecificMethods:
    """Test individual action execution methods."""
    
    @pytest.mark.asyncio
    async def test_execute_navigate_action_success(
        self, initialized_engine, mock_session
    ):
        """Test successful navigation."""
        await initialized_engine._execute_navigate_action(
            page=mock_session.playwright_page,
            url="https://example.com",
            progress_callback=Mock()
        )
        
        mock_session.playwright_page.goto.assert_called_once_with(
            "https://example.com",
            wait_until='networkidle',
            timeout=30000
        )
    
    @pytest.mark.asyncio
    async def test_execute_navigate_action_with_error_handler(
        self, initialized_engine, mock_session
    ):
        """Test navigation with error handler fallback."""
        # Mock page.goto to fail
        mock_session.playwright_page.goto = AsyncMock(
            side_effect=Exception("Navigation failed")
        )
        
        # Mock error handler
        initialized_engine.error_handler.handle_page_load_timeout = AsyncMock()
        
        await initialized_engine._execute_navigate_action(
            page=mock_session.playwright_page,
            url="https://example.com",
            progress_callback=Mock()
        )
        
        # Verify error handler was called
        initialized_engine.error_handler.handle_page_load_timeout.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_click_action_success(
        self, initialized_engine, mock_session, mock_element_selector
    ):
        """Test successful click."""
        # Mock element
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_element.click = AsyncMock()
        
        mock_session.playwright_page.query_selector = AsyncMock(
            return_value=mock_element
        )
        
        await initialized_engine._execute_click_action(
            page=mock_session.playwright_page,
            selector=mock_element_selector,
            progress_callback=Mock()
        )
        
        mock_element.click.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_click_action_with_error_handler(
        self, initialized_engine, mock_session, mock_element_selector
    ):
        """Test click with error handler fallback."""
        # Mock element not found
        mock_session.playwright_page.query_selector = AsyncMock(return_value=None)
        
        # Mock error handler to return working selector
        working_selector = ElementSelectors(
            css_selector="button.alt",
            xpath="//button",
            aria_label="Submit"
        )
        initialized_engine.error_handler.handle_element_not_found = AsyncMock(
            return_value=working_selector
        )
        
        # Mock element found with working selector
        mock_element = AsyncMock()
        mock_element.click = AsyncMock()
        
        async def mock_query_selector(selector):
            if selector == working_selector.css_selector:
                return mock_element
            return None
        
        mock_session.playwright_page.query_selector = mock_query_selector
        
        await initialized_engine._execute_click_action(
            page=mock_session.playwright_page,
            selector=mock_element_selector,
            progress_callback=Mock()
        )
        
        # Verify error handler was called
        initialized_engine.error_handler.handle_element_not_found.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_type_action_success(
        self, initialized_engine, mock_session, mock_element_selector
    ):
        """Test successful type action."""
        # Mock element
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_element.fill = AsyncMock()
        
        mock_session.playwright_page.query_selector = AsyncMock(
            return_value=mock_element
        )
        
        await initialized_engine._execute_type_action(
            page=mock_session.playwright_page,
            selector=mock_element_selector,
            text="test input",
            clear_first=True,
            progress_callback=Mock()
        )
        
        # Verify fill was called twice (clear + type)
        assert mock_element.fill.call_count == 2
        mock_element.fill.assert_any_call('')  # Clear
        mock_element.fill.assert_any_call('test input')  # Type
    
    @pytest.mark.asyncio
    async def test_execute_wait_action_with_selector(
        self, initialized_engine, mock_session, mock_element_selector
    ):
        """Test wait action with selector."""
        await initialized_engine._execute_wait_action(
            page=mock_session.playwright_page,
            selector=mock_element_selector,
            parameters={"condition": "visible", "timeout_ms": 5000},
            progress_callback=Mock()
        )
        
        mock_session.playwright_page.wait_for_selector.assert_called_once_with(
            mock_element_selector.css_selector,
            state="visible",
            timeout=5000
        )
    
    @pytest.mark.asyncio
    async def test_execute_extract_action_text(
        self, initialized_engine, mock_session, mock_element_selector
    ):
        """Test extract action for text."""
        # Mock element
        mock_element = AsyncMock()
        mock_element.text_content = AsyncMock(return_value="Extracted text")
        
        mock_session.playwright_page.query_selector = AsyncMock(
            return_value=mock_element
        )
        
        result = await initialized_engine._execute_extract_action(
            page=mock_session.playwright_page,
            selector=mock_element_selector,
            parameters={"extract_type": "text"},
            progress_callback=Mock()
        )
        
        assert "extracted_text" in result
        assert result["extracted_text"] == "Extracted text"
    
    @pytest.mark.asyncio
    async def test_execute_scroll_action_down(
        self, initialized_engine, mock_session
    ):
        """Test scroll down action."""
        await initialized_engine._execute_scroll_action(
            page=mock_session.playwright_page,
            parameters={"direction": "down", "amount": 500},
            progress_callback=Mock()
        )
        
        mock_session.playwright_page.evaluate.assert_called_once_with(
            "window.scrollBy(0, 500)"
        )
    
    @pytest.mark.asyncio
    async def test_execute_select_action(
        self, initialized_engine, mock_session, mock_element_selector
    ):
        """Test select action."""
        await initialized_engine._execute_select_action(
            page=mock_session.playwright_page,
            selector=mock_element_selector,
            value="option1",
            progress_callback=Mock()
        )
        
        mock_session.playwright_page.select_option.assert_called_once_with(
            mock_element_selector.css_selector,
            "option1"
        )


# ============================================================================
# Test: _verify_action_result
# ============================================================================

class TestVerifyActionResult:
    """Test _verify_action_result method."""
    
    @pytest.mark.asyncio
    async def test_verify_action_result_success(
        self, initialized_engine, mock_dom
    ):
        """Test successful action verification."""
        action = BrowserAction(
            action_type=ActionType.CLICK,
            expected_result="Form submitted successfully"
        )
        
        mock_page = AsyncMock()
        mock_page.text_content = AsyncMock(
            return_value="The form was submitted successfully. Thank you!"
        )
        
        verified = await initialized_engine._verify_action_result(
            action=action,
            dom=mock_dom,
            page=mock_page
        )
        
        assert verified is True
    
    @pytest.mark.asyncio
    async def test_verify_action_result_no_expected(
        self, initialized_engine, mock_dom
    ):
        """Test verification with no expected result."""
        action = BrowserAction(
            action_type=ActionType.CLICK,
            expected_result=""  # No expected result
        )
        
        verified = await initialized_engine._verify_action_result(
            action=action,
            dom=mock_dom,
            page=AsyncMock()
        )
        
        assert verified is True  # Should pass when no verification needed
    
    @pytest.mark.asyncio
    async def test_verify_action_result_partial_match(
        self, initialized_engine, mock_dom
    ):
        """Test verification with partial keyword match."""
        action = BrowserAction(
            action_type=ActionType.CLICK,
            expected_result="Form submitted successfully"
        )
        
        mock_page = AsyncMock()
        mock_page.text_content = AsyncMock(
            return_value="Form was submitted"  # Only 2/3 keywords match
        )
        
        verified = await initialized_engine._verify_action_result(
            action=action,
            dom=mock_dom,
            page=mock_page
        )
        
        assert verified is True  # Should pass with >= 50% match


# ============================================================================
# Test: Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Test integration scenarios combining multiple components."""
    
    @pytest.mark.asyncio
    async def test_complete_action_loop_workflow(
        self, initialized_engine, mock_browser_task, mock_session, mock_dom
    ):
        """Test complete action loop workflow."""
        # Setup mocks
        initialized_engine.dom_parser.parse_page = AsyncMock(return_value=mock_dom)
        
        # Create action plan
        mock_actions = [
            BrowserAction(
                action_type=ActionType.NAVIGATE,
                parameters={"url": "https://example.com"}
            ),
            BrowserAction(
                action_type=ActionType.CLICK,
                target_selector=ElementSelectors(
                    css_selector="button.submit",
                    xpath="//button",
                    aria_label="Submit"
                )
            ),
            BrowserAction(
                action_type=ActionType.EXTRACT,
                target_selector=ElementSelectors(
                    css_selector="div.result",
                    xpath="//div",
                    aria_label="Result"
                ),
                parameters={"extract_type": "text"}
            )
        ]
        initialized_engine.livekit_bridge.generate_action_plan = AsyncMock(
            return_value=mock_actions
        )
        
        # Mock action executions
        initialized_engine._execute_navigate_action = AsyncMock()
        initialized_engine._execute_click_action = AsyncMock()
        initialized_engine._execute_extract_action = AsyncMock(
            return_value={"extracted_text": "Success!"}
        )
        initialized_engine._verify_action_result = AsyncMock(return_value=True)
        
        # Execute action loop
        result = await initialized_engine._execute_action_loop(
            task=mock_browser_task,
            session=mock_session,
            progress_callback=Mock()
        )
        
        # Verify complete workflow
        assert result.success is True
        assert len(result.actions_taken) == 3
        assert "extracted_text" in result.extracted_data
        # Note: _execute_navigate_action is called twice (once for target_url, once for NAVIGATE action)
        assert initialized_engine._execute_navigate_action.call_count == 2
        initialized_engine._execute_click_action.assert_called_once()
        initialized_engine._execute_extract_action.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
