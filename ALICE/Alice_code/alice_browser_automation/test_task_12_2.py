"""
Unit tests for Task 12.2: LiveKitQwenBridge action planning methods.

Tests the generate_action_plan() and get_next_action() methods, along with
context management for multi-step tasks.

**Validates: Requirements 3.3, 3.4, 4.6, 12.3**
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from alice_browser_automation.livekit_bridge import LiveKitQwenBridge
from alice_browser_automation.types import (
    BrowserTask,
    BrowserAction,
    BrowserState,
    StructuredDOM,
    InteractiveElement,
    ElementSelectors,
    TaskType,
    ActionType
)
from alice_browser_automation.exceptions import QwenModelUnavailableError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_qwen_client():
    """Create a mock QwenModelClient."""
    client = AsyncMock()
    client.validate_model_availability = AsyncMock(return_value=True)
    client.generate_json_response = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def sample_browser_task():
    """Create a sample BrowserTask."""
    return BrowserTask(
        task_id="test-task-123",
        description="Book a flight to Paris",
        task_type=TaskType.WEB_BOOKING,
        parameters={
            "booking_type": "flight",
            "destination": "Paris",
            "departure_date": "2025-12-25",
            "passengers": 2
        },
        target_url="https://example.com/flights",
        expected_outcome="Flight booking confirmed"
    )


@pytest.fixture
def sample_structured_dom():
    """Create a sample StructuredDOM."""
    elements = [
        InteractiveElement(
            element_id="search-btn",
            tag_name="button",
            role="button",
            label="Search Flights",
            selectors=ElementSelectors(
                css_selector="button#search-btn",
                xpath="//button[@id='search-btn']",
                aria_label="Search Flights"
            ),
            attributes={"type": "submit"},
            position=(100, 200),
            is_visible=True
        ),
        InteractiveElement(
            element_id="destination",
            tag_name="input",
            role="textbox",
            label="Destination",
            selectors=ElementSelectors(
                css_selector="input#destination",
                xpath="//input[@id='destination']",
                aria_label="Destination"
            ),
            attributes={"type": "text", "placeholder": "Enter destination"},
            position=(100, 150),
            is_visible=True
        ),
        InteractiveElement(
            element_id="date-picker",
            tag_name="input",
            role="textbox",
            label="Departure Date",
            selectors=ElementSelectors(
                css_selector="input#date-picker",
                xpath="//input[@id='date-picker']",
                aria_label="Departure Date"
            ),
            attributes={"type": "date"},
            position=(100, 180),
            is_visible=True
        )
    ]
    
    return StructuredDOM(
        url="https://example.com/flights",
        title="Flight Booking",
        interactive_elements=elements,
        text_content="Search for flights to your destination",
        metadata={"viewport_width": 1920, "viewport_height": 1080},
        timestamp=datetime.now()
    )


@pytest.fixture
def sample_browser_state(sample_structured_dom):
    """Create a sample BrowserState."""
    return BrowserState(
        url="https://example.com/flights",
        dom=sample_structured_dom,
        cookies=[],
        local_storage={},
        session_storage={},
        screenshot_path=None
    )


@pytest.fixture
def sample_previous_actions():
    """Create sample previous actions."""
    return [
        BrowserAction(
            action_type=ActionType.NAVIGATE,
            target_selector=None,
            parameters={"url": "https://example.com/flights", "wait_until": "networkidle"},
            expected_result="Page loaded with booking form",
            retry_count=0
        ),
        BrowserAction(
            action_type=ActionType.TYPE,
            target_selector=ElementSelectors(
                css_selector="input#destination",
                xpath="//input[@id='destination']",
                aria_label="Destination"
            ),
            parameters={"text": "Paris", "clear_first": True},
            expected_result="Destination field contains 'Paris'",
            retry_count=0
        )
    ]


# ============================================================================
# Test generate_action_plan()
# ============================================================================

@pytest.mark.asyncio
async def test_generate_action_plan_success(mock_qwen_client, sample_browser_task, sample_structured_dom):
    """Test successful action plan generation."""
    # Arrange
    bridge = LiveKitQwenBridge()
    bridge.qwen_client = mock_qwen_client
    
    # Mock Qwen response
    mock_qwen_client.generate_json_response.return_value = {
        "action_type": "type",
        "target_selector": {
            "css_selector": "input#destination",
            "xpath": "//input[@id='destination']",
            "aria_label": "Destination"
        },
        "parameters": {
            "text": "Paris",
            "clear_first": True
        },
        "expected_result": "Destination field contains 'Paris'"
    }
    
    # Act
    actions = await bridge.generate_action_plan(sample_browser_task, sample_structured_dom)
    
    # Assert
    assert len(actions) == 1
    assert actions[0].action_type == ActionType.TYPE
    assert actions[0].parameters["text"] == "Paris"
    assert actions[0].target_selector.aria_label == "Destination"
    
    # Verify Qwen client was called
    mock_qwen_client.generate_json_response.assert_called_once()
    call_args = mock_qwen_client.generate_json_response.call_args
    assert "Book a flight to Paris" in call_args.kwargs["prompt"]
    assert "Flight Booking" in call_args.kwargs["prompt"]
    
    await bridge.close()


@pytest.mark.asyncio
async def test_generate_action_plan_with_navigate_action(mock_qwen_client, sample_browser_task, sample_structured_dom):
    """Test action plan generation with navigate action."""
    # Arrange
    bridge = LiveKitQwenBridge()
    bridge.qwen_client = mock_qwen_client
    
    # Mock Qwen response for navigate action
    mock_qwen_client.generate_json_response.return_value = {
        "action_type": "navigate",
        "target_selector": None,
        "parameters": {
            "url": "https://example.com/flights",
            "wait_until": "networkidle"
        },
        "expected_result": "Page loaded with booking form"
    }
    
    # Act
    actions = await bridge.generate_action_plan(sample_browser_task, sample_structured_dom)
    
    # Assert
    assert len(actions) == 1
    assert actions[0].action_type == ActionType.NAVIGATE
    assert actions[0].target_selector is None
    assert actions[0].parameters["url"] == "https://example.com/flights"
    
    await bridge.close()


@pytest.mark.asyncio
async def test_generate_action_plan_includes_dom_in_prompt(mock_qwen_client, sample_browser_task, sample_structured_dom):
    """Test that DOM structure is included in the prompt."""
    # Arrange
    bridge = LiveKitQwenBridge()
    bridge.qwen_client = mock_qwen_client
    
    mock_qwen_client.generate_json_response.return_value = {
        "action_type": "click",
        "target_selector": {"css_selector": "button#search-btn", "xpath": "//button", "aria_label": "Search"},
        "parameters": {},
        "expected_result": "Search initiated"
    }
    
    # Act
    await bridge.generate_action_plan(sample_browser_task, sample_structured_dom)
    
    # Assert
    call_args = mock_qwen_client.generate_json_response.call_args
    prompt = call_args.kwargs["prompt"]
    
    # Check that DOM elements are in prompt
    assert "Search Flights" in prompt
    assert "Destination" in prompt
    assert "Departure Date" in prompt
    assert "https://example.com/flights" in prompt
    
    await bridge.close()


@pytest.mark.asyncio
async def test_generate_action_plan_handles_invalid_action_type(mock_qwen_client, sample_browser_task, sample_structured_dom):
    """Test handling of invalid action type from model."""
    # Arrange
    bridge = LiveKitQwenBridge()
    bridge.qwen_client = mock_qwen_client
    
    # Mock Qwen response with invalid action type
    mock_qwen_client.generate_json_response.return_value = {
        "action_type": "invalid_action",
        "target_selector": None,
        "parameters": {},
        "expected_result": "Something"
    }
    
    # Act & Assert
    with pytest.raises(ValueError, match="Invalid action type"):
        await bridge.generate_action_plan(sample_browser_task, sample_structured_dom)
    
    await bridge.close()


@pytest.mark.asyncio
async def test_generate_action_plan_handles_model_error(mock_qwen_client, sample_browser_task, sample_structured_dom):
    """Test handling of model errors during action plan generation."""
    # Arrange
    bridge = LiveKitQwenBridge()
    bridge.qwen_client = mock_qwen_client
    
    # Mock Qwen client to raise error
    mock_qwen_client.generate_json_response.side_effect = QwenModelUnavailableError(
        "Model unavailable",
        host="http://localhost:11434",
        model="qwen2.5-coder:3b"
    )
    
    # Act & Assert
    with pytest.raises(ValueError, match="Could not generate action plan"):
        await bridge.generate_action_plan(sample_browser_task, sample_structured_dom)
    
    await bridge.close()


# ============================================================================
# Test get_next_action()
# ============================================================================

@pytest.mark.asyncio
async def test_get_next_action_success(mock_qwen_client, sample_browser_state, sample_structured_dom, sample_previous_actions):
    """Test successful next action determination."""
    # Arrange
    bridge = LiveKitQwenBridge()
    bridge.qwen_client = mock_qwen_client
    
    # Set task context
    bridge._task_context = {
        'task_id': 'test-task-123',
        'description': 'Book a flight to Paris',
        'task_type': 'web_booking',
        'parameters': {'destination': 'Paris'},
        'expected_outcome': 'Flight booked',
        'target_url': 'https://example.com/flights'
    }
    
    # Mock Qwen response
    mock_qwen_client.generate_json_response.return_value = {
        "action_type": "click",
        "target_selector": {
            "css_selector": "button#search-btn",
            "xpath": "//button[@id='search-btn']",
            "aria_label": "Search Flights"
        },
        "parameters": {},
        "expected_result": "Search initiated"
    }
    
    # Act
    next_action = await bridge.get_next_action(
        sample_browser_state,
        sample_structured_dom,
        sample_previous_actions
    )
    
    # Assert
    assert next_action is not None
    assert next_action.action_type == ActionType.CLICK
    assert next_action.target_selector.aria_label == "Search Flights"
    
    # Verify prompt includes previous actions
    call_args = mock_qwen_client.generate_json_response.call_args
    prompt = call_args.kwargs["prompt"]
    assert "Previous Actions Taken:" in prompt
    assert "navigate" in prompt.lower()
    assert "type" in prompt.lower()
    
    await bridge.close()


@pytest.mark.asyncio
async def test_get_next_action_task_complete(mock_qwen_client, sample_browser_state, sample_structured_dom, sample_previous_actions):
    """Test next action when task is complete."""
    # Arrange
    bridge = LiveKitQwenBridge()
    bridge.qwen_client = mock_qwen_client
    
    # Set task context
    bridge._task_context = {
        'task_id': 'test-task-123',
        'description': 'Book a flight to Paris',
        'task_type': 'web_booking',
        'parameters': {},
        'expected_outcome': 'Flight booked',
        'target_url': None
    }
    
    # Mock Qwen response indicating completion
    mock_qwen_client.generate_json_response.return_value = {
        "action_type": "wait",
        "target_selector": None,
        "parameters": {
            "condition": "complete",
            "timeout_ms": 0
        },
        "expected_result": "Task complete"
    }
    
    # Act
    next_action = await bridge.get_next_action(
        sample_browser_state,
        sample_structured_dom,
        sample_previous_actions
    )
    
    # Assert
    assert next_action is None  # Task is complete
    
    await bridge.close()


@pytest.mark.asyncio
async def test_get_next_action_no_task_context(mock_qwen_client, sample_browser_state, sample_structured_dom, sample_previous_actions):
    """Test next action when no task context is available."""
    # Arrange
    bridge = LiveKitQwenBridge()
    bridge.qwen_client = mock_qwen_client
    
    # Don't set task context
    
    # Act
    next_action = await bridge.get_next_action(
        sample_browser_state,
        sample_structured_dom,
        sample_previous_actions
    )
    
    # Assert
    assert next_action is None  # No task context
    
    await bridge.close()


@pytest.mark.asyncio
async def test_get_next_action_with_empty_previous_actions(mock_qwen_client, sample_browser_state, sample_structured_dom):
    """Test next action with no previous actions."""
    # Arrange
    bridge = LiveKitQwenBridge()
    bridge.qwen_client = mock_qwen_client
    
    # Set task context
    bridge._task_context = {
        'task_id': 'test-task-123',
        'description': 'Book a flight',
        'task_type': 'web_booking',
        'parameters': {},
        'expected_outcome': 'Flight booked',
        'target_url': None
    }
    
    # Mock Qwen response
    mock_qwen_client.generate_json_response.return_value = {
        "action_type": "navigate",
        "target_selector": None,
        "parameters": {"url": "https://example.com/flights"},
        "expected_result": "Page loaded"
    }
    
    # Act
    next_action = await bridge.get_next_action(
        sample_browser_state,
        sample_structured_dom,
        []  # Empty previous actions
    )
    
    # Assert
    assert next_action is not None
    assert next_action.action_type == ActionType.NAVIGATE
    
    # Verify prompt indicates first action
    call_args = mock_qwen_client.generate_json_response.call_args
    prompt = call_args.kwargs["prompt"]
    assert "None (this is the first action)" in prompt
    
    await bridge.close()


# ============================================================================
# Test context management
# ============================================================================

def test_set_task_context(sample_browser_task):
    """Test setting task context."""
    # Arrange
    bridge = LiveKitQwenBridge()
    
    # Act
    bridge._set_task_context(sample_browser_task)
    
    # Assert
    context = bridge._get_task_context()
    assert context is not None
    assert context['task_id'] == sample_browser_task.task_id
    assert context['description'] == sample_browser_task.description
    assert context['task_type'] == sample_browser_task.task_type.value
    assert context['parameters'] == sample_browser_task.parameters


def test_clear_task_context(sample_browser_task):
    """Test clearing task context."""
    # Arrange
    bridge = LiveKitQwenBridge()
    bridge._set_task_context(sample_browser_task)
    
    # Act
    bridge._clear_task_context()
    
    # Assert
    context = bridge._get_task_context()
    assert context is None


def test_get_task_context_when_not_set():
    """Test getting task context when not set."""
    # Arrange
    bridge = LiveKitQwenBridge()
    
    # Act
    context = bridge._get_task_context()
    
    # Assert
    assert context is None


@pytest.mark.asyncio
async def test_translate_voice_command_sets_task_context(mock_qwen_client):
    """Test that translate_voice_command sets task context."""
    # Arrange
    bridge = LiveKitQwenBridge()
    bridge.qwen_client = mock_qwen_client
    
    # Mock Qwen response
    mock_qwen_client.generate_json_response.return_value = {
        "task_type": "web_booking",
        "description": "Book a flight to Paris",
        "target_url": None,
        "parameters": {"destination": "Paris"},
        "expected_outcome": "Flight booked"
    }
    
    # Act
    task = await bridge.translate_voice_command("Book a flight to Paris")
    
    # Assert
    context = bridge._get_task_context()
    assert context is not None
    assert context['task_id'] == task.task_id
    assert context['description'] == "Book a flight to Paris"
    
    await bridge.close()


# ============================================================================
# Test helper methods
# ============================================================================

def test_format_dom_for_prompt(sample_structured_dom):
    """Test DOM formatting for prompts."""
    # Arrange
    bridge = LiveKitQwenBridge()
    
    # Act
    formatted = bridge._format_dom_for_prompt(sample_structured_dom.interactive_elements)
    
    # Assert
    assert "Search Flights" in formatted
    assert "Destination" in formatted
    assert "Departure Date" in formatted
    assert "button" in formatted
    assert "input" in formatted


def test_format_dom_for_prompt_empty_elements():
    """Test DOM formatting with empty elements list."""
    # Arrange
    bridge = LiveKitQwenBridge()
    
    # Act
    formatted = bridge._format_dom_for_prompt([])
    
    # Assert
    assert "No interactive elements found" in formatted


def test_format_previous_actions(sample_previous_actions):
    """Test previous actions formatting."""
    # Arrange
    bridge = LiveKitQwenBridge()
    
    # Act
    formatted = bridge._format_previous_actions(sample_previous_actions)
    
    # Assert
    assert "1. navigate" in formatted
    assert "2. type" in formatted
    assert "Paris" in formatted
    assert "Destination" in formatted


def test_format_previous_actions_empty():
    """Test previous actions formatting with empty list."""
    # Arrange
    bridge = LiveKitQwenBridge()
    
    # Act
    formatted = bridge._format_previous_actions([])
    
    # Assert
    assert "None (this is the first action)" in formatted


def test_json_to_browser_action_with_selector():
    """Test converting JSON to BrowserAction with selector."""
    # Arrange
    bridge = LiveKitQwenBridge()
    action_json = {
        "action_type": "click",
        "target_selector": {
            "css_selector": "button#submit",
            "xpath": "//button[@id='submit']",
            "aria_label": "Submit"
        },
        "parameters": {},
        "expected_result": "Form submitted"
    }
    
    # Act
    action = bridge._json_to_browser_action(action_json)
    
    # Assert
    assert action.action_type == ActionType.CLICK
    assert action.target_selector is not None
    assert action.target_selector.css_selector == "button#submit"
    assert action.target_selector.aria_label == "Submit"
    assert action.expected_result == "Form submitted"


def test_json_to_browser_action_without_selector():
    """Test converting JSON to BrowserAction without selector."""
    # Arrange
    bridge = LiveKitQwenBridge()
    action_json = {
        "action_type": "navigate",
        "target_selector": None,
        "parameters": {"url": "https://example.com"},
        "expected_result": "Page loaded"
    }
    
    # Act
    action = bridge._json_to_browser_action(action_json)
    
    # Assert
    assert action.action_type == ActionType.NAVIGATE
    assert action.target_selector is None
    assert action.parameters["url"] == "https://example.com"


def test_json_to_browser_action_invalid_action_type():
    """Test converting JSON with invalid action type."""
    # Arrange
    bridge = LiveKitQwenBridge()
    action_json = {
        "action_type": "invalid",
        "target_selector": None,
        "parameters": {},
        "expected_result": "Something"
    }
    
    # Act & Assert
    with pytest.raises(ValueError, match="Invalid action type"):
        bridge._json_to_browser_action(action_json)


# ============================================================================
# Integration tests
# ============================================================================

@pytest.mark.asyncio
async def test_full_action_planning_workflow(mock_qwen_client, sample_browser_task, sample_structured_dom, sample_browser_state):
    """Test complete workflow: translate command -> generate plan -> get next actions."""
    # Arrange
    bridge = LiveKitQwenBridge()
    bridge.qwen_client = mock_qwen_client
    
    # Mock translate_voice_command
    mock_qwen_client.generate_json_response.side_effect = [
        # First call: translate_voice_command
        {
            "task_type": "web_booking",
            "description": "Book a flight to Paris",
            "target_url": "https://example.com/flights",
            "parameters": {"destination": "Paris"},
            "expected_outcome": "Flight booked"
        },
        # Second call: generate_action_plan
        {
            "action_type": "navigate",
            "target_selector": None,
            "parameters": {"url": "https://example.com/flights"},
            "expected_result": "Page loaded"
        },
        # Third call: get_next_action
        {
            "action_type": "type",
            "target_selector": {
                "css_selector": "input#destination",
                "xpath": "//input[@id='destination']",
                "aria_label": "Destination"
            },
            "parameters": {"text": "Paris"},
            "expected_result": "Destination entered"
        }
    ]
    
    # Act
    # Step 1: Translate voice command
    task = await bridge.translate_voice_command("Book a flight to Paris")
    assert task.task_type == TaskType.WEB_BOOKING
    
    # Step 2: Generate action plan
    actions = await bridge.generate_action_plan(task, sample_structured_dom)
    assert len(actions) == 1
    assert actions[0].action_type == ActionType.NAVIGATE
    
    # Step 3: Get next action
    next_action = await bridge.get_next_action(
        sample_browser_state,
        sample_structured_dom,
        actions
    )
    assert next_action is not None
    assert next_action.action_type == ActionType.TYPE
    
    await bridge.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
