"""
Unit tests for type definitions and data models.
"""

import pytest
from datetime import datetime, date
from alice_browser_automation.types import (
    TaskType,
    ActionType,
    SessionState,
    ElementSelectors,
    InteractiveElement,
    StructuredDOM,
    BrowserAction,
    BrowserTask,
    TaskResult,
    BrowserSession,
    RetryConfig,
    TravelBookingDetails,
    EventTicketDetails,
)


class TestEnums:
    """Test enum definitions"""
    
    def test_task_type_enum(self):
        """Test TaskType enum values"""
        assert TaskType.WEB_BOOKING.value == "web_booking"
        assert TaskType.PROBLEM_SOLVING.value == "problem_solving"
        assert TaskType.APP_ACCESS.value == "app_access"
    
    def test_action_type_enum(self):
        """Test ActionType enum values"""
        assert ActionType.NAVIGATE.value == "navigate"
        assert ActionType.CLICK.value == "click"
        assert ActionType.TYPE.value == "type"
        assert ActionType.WAIT.value == "wait"
        assert ActionType.EXTRACT.value == "extract"
        assert ActionType.SCROLL.value == "scroll"
    
    def test_session_state_enum(self):
        """Test SessionState enum values"""
        assert SessionState.CREATING.value == "creating"
        assert SessionState.ACTIVE.value == "active"
        assert SessionState.IDLE.value == "idle"
        assert SessionState.CRASHED.value == "crashed"
        assert SessionState.CLOSING.value == "closing"


class TestElementSelectors:
    """Test ElementSelectors dataclass"""
    
    def test_element_selectors_creation(self):
        """Test creating ElementSelectors with all fields"""
        selectors = ElementSelectors(
            css_selector="button#submit",
            xpath="//button[@id='submit']",
            aria_label="Submit",
            test_id="submit-btn",
            text_content="Submit"
        )
        
        assert selectors.css_selector == "button#submit"
        assert selectors.xpath == "//button[@id='submit']"
        assert selectors.aria_label == "Submit"
        assert selectors.test_id == "submit-btn"
        assert selectors.text_content == "Submit"
    
    def test_element_selectors_optional_fields(self):
        """Test ElementSelectors with only required fields"""
        selectors = ElementSelectors(
            css_selector="button",
            xpath="//button"
        )
        
        assert selectors.css_selector == "button"
        assert selectors.xpath == "//button"
        assert selectors.aria_label is None
        assert selectors.test_id is None
        assert selectors.text_content is None


class TestInteractiveElement:
    """Test InteractiveElement dataclass"""
    
    def test_interactive_element_creation(self):
        """Test creating InteractiveElement"""
        selectors = ElementSelectors(
            css_selector="button#submit",
            xpath="//button[@id='submit']"
        )
        
        element = InteractiveElement(
            element_id="submit",
            tag_name="button",
            role="button",
            label="Submit",
            selectors=selectors,
            attributes={"type": "submit", "class": "btn-primary"},
            position=(100, 200),
            is_visible=True
        )
        
        assert element.element_id == "submit"
        assert element.tag_name == "button"
        assert element.role == "button"
        assert element.label == "Submit"
        assert element.selectors == selectors
        assert element.attributes["type"] == "submit"
        assert element.position == (100, 200)
        assert element.is_visible is True


class TestBrowserAction:
    """Test BrowserAction dataclass"""
    
    def test_browser_action_creation(self):
        """Test creating BrowserAction"""
        selectors = ElementSelectors(
            css_selector="button",
            xpath="//button"
        )
        
        action = BrowserAction(
            action_type=ActionType.CLICK,
            target_selector=selectors,
            parameters={"wait_after": 1.0},
            expected_result="Button clicked",
            retry_count=0
        )
        
        assert action.action_type == ActionType.CLICK
        assert action.target_selector == selectors
        assert action.parameters["wait_after"] == 1.0
        assert action.expected_result == "Button clicked"
        assert action.retry_count == 0
    
    def test_browser_action_defaults(self):
        """Test BrowserAction with default values"""
        action = BrowserAction(action_type=ActionType.NAVIGATE)
        
        assert action.action_type == ActionType.NAVIGATE
        assert action.target_selector is None
        assert action.parameters == {}
        assert action.expected_result == ""
        assert action.retry_count == 0


class TestBrowserTask:
    """Test BrowserTask dataclass"""
    
    def test_browser_task_creation(self):
        """Test creating BrowserTask"""
        task = BrowserTask(
            task_id="task-123",
            description="Book a flight",
            task_type=TaskType.WEB_BOOKING,
            parameters={"origin": "SFO", "destination": "CDG"},
            target_url="https://booking.example.com",
            expected_outcome="Flight booked successfully"
        )
        
        assert task.task_id == "task-123"
        assert task.description == "Book a flight"
        assert task.task_type == TaskType.WEB_BOOKING
        assert task.parameters["origin"] == "SFO"
        assert task.target_url == "https://booking.example.com"
        assert task.expected_outcome == "Flight booked successfully"


class TestTaskResult:
    """Test TaskResult dataclass"""
    
    def test_task_result_success(self):
        """Test creating successful TaskResult"""
        action = BrowserAction(action_type=ActionType.CLICK)
        
        result = TaskResult(
            task_id="task-123",
            success=True,
            summary="Task completed successfully",
            actions_taken=[action],
            extracted_data={"confirmation": "ABC123"},
            duration_seconds=45.5
        )
        
        assert result.task_id == "task-123"
        assert result.success is True
        assert result.summary == "Task completed successfully"
        assert len(result.actions_taken) == 1
        assert result.extracted_data["confirmation"] == "ABC123"
        assert result.error is None
        assert result.duration_seconds == 45.5
    
    def test_task_result_failure(self):
        """Test creating failed TaskResult"""
        result = TaskResult(
            task_id="task-123",
            success=False,
            summary="Task failed",
            error="Element not found"
        )
        
        assert result.task_id == "task-123"
        assert result.success is False
        assert result.error == "Element not found"


class TestRetryConfig:
    """Test RetryConfig dataclass"""
    
    def test_retry_config_defaults(self):
        """Test RetryConfig default values"""
        config = RetryConfig()
        
        assert config.max_retries == 2
        assert config.retry_delay_seconds == 1.0
        assert config.exponential_backoff is True
        assert config.backoff_multiplier == 2.0
        assert config.element_not_found_retries == 3
        assert config.page_load_retries == 2
    
    def test_retry_config_custom(self):
        """Test RetryConfig with custom values"""
        config = RetryConfig(
            max_retries=5,
            retry_delay_seconds=2.0,
            exponential_backoff=False
        )
        
        assert config.max_retries == 5
        assert config.retry_delay_seconds == 2.0
        assert config.exponential_backoff is False


class TestTravelBookingDetails:
    """Test TravelBookingDetails dataclass"""
    
    def test_travel_booking_details(self):
        """Test creating TravelBookingDetails"""
        details = TravelBookingDetails(
            booking_type="flight",
            origin="SFO",
            destination="CDG",
            departure_date=date(2025, 12, 25),
            return_date=date(2026, 1, 5),
            passengers=2,
            class_preference="economy"
        )
        
        assert details.booking_type == "flight"
        assert details.origin == "SFO"
        assert details.destination == "CDG"
        assert details.passengers == 2
        assert details.class_preference == "economy"


class TestEventTicketDetails:
    """Test EventTicketDetails dataclass"""
    
    def test_event_ticket_details(self):
        """Test creating EventTicketDetails"""
        details = EventTicketDetails(
            event_name="Concert",
            venue="Madison Square Garden",
            date=date(2025, 6, 15),
            time="19:00",
            ticket_count=2,
            ticket_type="VIP"
        )
        
        assert details.event_name == "Concert"
        assert details.venue == "Madison Square Garden"
        assert details.ticket_count == 2
        assert details.ticket_type == "VIP"
