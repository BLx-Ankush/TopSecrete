"""
Unit tests for Browser Automation Engine Task Orchestration (Task 13.2).

Tests task routing, progress callbacks, result aggregation, task cancellation,
and statistics tracking.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from alice_browser_automation.engine import BrowserAutomationEngine
from alice_browser_automation.config import Config
from alice_browser_automation.types import (
    TaskType, TaskResult, BrowserTask, BrowserAction, ActionType,
    ElementSelectors
)
from alice_browser_automation.exceptions import BrowserAutomationError


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
    engine.livekit_bridge = AsyncMock()
    engine.session_manager = AsyncMock()
    engine.dom_parser = Mock()
    engine.error_handler = Mock()
    
    return engine


@pytest.fixture
def mock_browser_task():
    """Create a mock browser task."""
    return BrowserTask(
        task_id="task-123",
        description="Test task",
        task_type=TaskType.WEB_BOOKING,
        parameters={"booking_type": "flight", "destination": "Paris"},
        target_url="https://example.com",
        expected_outcome="Task completed"
    )


@pytest.fixture
def mock_browser_actions():
    """Create mock browser actions."""
    return [
        BrowserAction(
            action_type=ActionType.NAVIGATE,
            target_selector=None,
            parameters={"url": "https://example.com"},
            expected_result="Page loaded",
            retry_count=0
        ),
        BrowserAction(
            action_type=ActionType.CLICK,
            target_selector=ElementSelectors(
                css_selector="button.submit",
                xpath="//button[@class='submit']",
                aria_label="Submit",
                test_id=None,
                text_content="Submit"
            ),
            parameters={},
            expected_result="Form submitted",
            retry_count=0
        )
    ]


# ============================================================================
# Test: Task Cancellation
# ============================================================================

class TestTaskCancellation:
    """Test task cancellation functionality."""
    
    def test_cancel_task_success(self, initialized_engine, mock_browser_task):
        """Test cancelling an active task."""
        # Add task to active tasks
        initialized_engine._active_tasks[mock_browser_task.task_id] = mock_browser_task
        initialized_engine._task_cancellation_flags[mock_browser_task.task_id] = False
        
        # Cancel task
        result = initialized_engine.cancel_task(mock_browser_task.task_id)
        
        # Assertions
        assert result is True
        assert initialized_engine._task_cancellation_flags[mock_browser_task.task_id] is True
    
    def test_cancel_task_not_found(self, initialized_engine):
        """Test cancelling a non-existent task."""
        result = initialized_engine.cancel_task("non-existent-task")
        
        assert result is False
    
    def test_is_task_cancelled_true(self, initialized_engine):
        """Test checking if task is cancelled (true case)."""
        task_id = "task-123"
        initialized_engine._task_cancellation_flags[task_id] = True
        
        result = initialized_engine.is_task_cancelled(task_id)
        
        assert result is True
    
    def test_is_task_cancelled_false(self, initialized_engine):
        """Test checking if task is cancelled (false case)."""
        task_id = "task-123"
        initialized_engine._task_cancellation_flags[task_id] = False
        
        result = initialized_engine.is_task_cancelled(task_id)
        
        assert result is False
    
    def test_is_task_cancelled_not_found(self, initialized_engine):
        """Test checking if non-existent task is cancelled."""
        result = initialized_engine.is_task_cancelled("non-existent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_execute_task_handles_cancellation(self, initialized_engine, mock_browser_task):
        """Test that execute_task handles cancellation correctly."""
        # Mock translate_voice_command
        initialized_engine.livekit_bridge.translate_voice_command = AsyncMock(
            return_value=mock_browser_task
        )
        
        # Mock action suite to set cancellation flag
        async def mock_execute_web_booking(task, callback):
            # Simulate cancellation during execution
            initialized_engine._task_cancellation_flags[task.task_id] = True
            return TaskResult(
                task_id=task.task_id,
                success=True,
                summary="Partial completion",
                actions_taken=[],
                extracted_data={},
                error=None,
                duration_seconds=0.0,
                screenshots=[]
            )
        
        initialized_engine._execute_web_booking = mock_execute_web_booking
        
        # Execute task
        result = await initialized_engine.execute_task(
            task_description="Test task",
            task_type=TaskType.WEB_BOOKING,
            parameters={},
            callback=None
        )
        
        # Assertions
        assert result.success is False
        assert "cancelled" in result.error.lower()
        assert initialized_engine._task_stats["cancelled_tasks"] == 1


# ============================================================================
# Test: Task Statistics
# ============================================================================

class TestTaskStatistics:
    """Test task statistics tracking."""
    
    @pytest.mark.asyncio
    async def test_statistics_successful_task(self, initialized_engine, mock_browser_task):
        """Test statistics for successful task."""
        # Mock components
        initialized_engine.livekit_bridge.translate_voice_command = AsyncMock(
            return_value=mock_browser_task
        )
        
        success_result = TaskResult(
            task_id=mock_browser_task.task_id,
            success=True,
            summary="Success",
            actions_taken=[],
            extracted_data={},
            error=None,
            duration_seconds=0.0,
            screenshots=[]
        )
        initialized_engine._execute_web_booking = AsyncMock(return_value=success_result)
        
        # Execute task
        await initialized_engine.execute_task(
            task_description="Test",
            task_type=TaskType.WEB_BOOKING,
            parameters={},
            callback=None
        )
        
        # Check statistics
        stats = initialized_engine.get_task_statistics()
        assert stats["total_tasks"] == 1
        assert stats["successful_tasks"] == 1
        assert stats["failed_tasks"] == 0
        assert stats["cancelled_tasks"] == 0
    
    @pytest.mark.asyncio
    async def test_statistics_failed_task(self, initialized_engine, mock_browser_task):
        """Test statistics for failed task."""
        # Mock components
        initialized_engine.livekit_bridge.translate_voice_command = AsyncMock(
            return_value=mock_browser_task
        )
        
        failed_result = TaskResult(
            task_id=mock_browser_task.task_id,
            success=False,
            summary="Failed",
            actions_taken=[],
            extracted_data={},
            error="Test error",
            duration_seconds=0.0,
            screenshots=[]
        )
        initialized_engine._execute_web_booking = AsyncMock(return_value=failed_result)
        
        # Execute task
        await initialized_engine.execute_task(
            task_description="Test",
            task_type=TaskType.WEB_BOOKING,
            parameters={},
            callback=None
        )
        
        # Check statistics
        stats = initialized_engine.get_task_statistics()
        assert stats["total_tasks"] == 1
        assert stats["successful_tasks"] == 0
        assert stats["failed_tasks"] == 1
        assert stats["cancelled_tasks"] == 0
    
    @pytest.mark.asyncio
    async def test_statistics_exception_task(self, initialized_engine):
        """Test statistics when task raises exception."""
        # Mock components to raise exception
        initialized_engine.livekit_bridge.translate_voice_command = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        # Execute task
        await initialized_engine.execute_task(
            task_description="Test",
            task_type=TaskType.WEB_BOOKING,
            parameters={},
            callback=None
        )
        
        # Check statistics
        stats = initialized_engine.get_task_statistics()
        assert stats["total_tasks"] == 1
        assert stats["successful_tasks"] == 0
        assert stats["failed_tasks"] == 1
        assert stats["cancelled_tasks"] == 0
    
    def test_get_task_statistics_returns_copy(self, initialized_engine):
        """Test that get_task_statistics returns a copy."""
        stats1 = initialized_engine.get_task_statistics()
        stats1["total_tasks"] = 999
        
        stats2 = initialized_engine.get_task_statistics()
        
        assert stats2["total_tasks"] == 0  # Original not modified


# ============================================================================
# Test: Active Task Tracking
# ============================================================================

class TestActiveTaskTracking:
    """Test active task tracking."""
    
    def test_get_active_task_ids_empty(self, initialized_engine):
        """Test getting active task IDs when none active."""
        task_ids = initialized_engine.get_active_task_ids()
        
        assert task_ids == []
    
    def test_get_active_task_ids_with_tasks(self, initialized_engine, mock_browser_task):
        """Test getting active task IDs with active tasks."""
        # Add tasks
        initialized_engine._active_tasks[mock_browser_task.task_id] = mock_browser_task
        initialized_engine._active_tasks["task-456"] = BrowserTask(
            task_id="task-456",
            description="Another task",
            task_type=TaskType.PROBLEM_SOLVING,
            parameters={},
            target_url=None,
            expected_outcome="Done"
        )
        
        task_ids = initialized_engine.get_active_task_ids()
        
        assert len(task_ids) == 2
        assert mock_browser_task.task_id in task_ids
        assert "task-456" in task_ids


# ============================================================================
# Test: Result Aggregation
# ============================================================================

class TestResultAggregation:
    """Test result aggregation functionality."""
    
    def test_aggregate_task_result_success(self, initialized_engine, mock_browser_task, mock_browser_actions):
        """Test aggregating successful task result."""
        extracted_data = {
            "confirmation_number": "ABC123",
            "booking_id": "BOOK456"
        }
        
        result = initialized_engine._aggregate_task_result(
            task=mock_browser_task,
            actions_taken=mock_browser_actions,
            extracted_data=extracted_data,
            success=True,
            error=None,
            screenshots=["screenshot1.png"]
        )
        
        # Assertions
        assert result.task_id == mock_browser_task.task_id
        assert result.success is True
        assert "confirmation" in result.summary.lower() or "ABC123" in result.summary
        assert len(result.actions_taken) == 2
        assert result.extracted_data == extracted_data
        assert result.error is None
        assert len(result.screenshots) == 1
    
    def test_aggregate_task_result_failure(self, initialized_engine, mock_browser_task):
        """Test aggregating failed task result."""
        result = initialized_engine._aggregate_task_result(
            task=mock_browser_task,
            actions_taken=[],
            extracted_data={},
            success=False,
            error="Test error occurred",
            screenshots=None
        )
        
        # Assertions
        assert result.success is False
        assert "failed" in result.summary.lower()
        assert "Test error occurred" in result.summary
        assert result.error == "Test error occurred"
        assert len(result.screenshots) == 0
    
    def test_generate_success_summary_with_confirmation(self, initialized_engine, mock_browser_task, mock_browser_actions):
        """Test generating success summary with confirmation number."""
        extracted_data = {"confirmation_number": "XYZ789"}
        
        summary = initialized_engine._generate_success_summary(
            task=mock_browser_task,
            actions_taken=mock_browser_actions,
            extracted_data=extracted_data
        )
        
        assert "successfully completed" in summary.lower()
        assert "web_booking" in summary.lower()
        assert "2 actions" in summary.lower()
        assert "XYZ789" in summary
    
    def test_generate_success_summary_no_data(self, initialized_engine, mock_browser_task):
        """Test generating success summary without extracted data."""
        summary = initialized_engine._generate_success_summary(
            task=mock_browser_task,
            actions_taken=[],
            extracted_data={}
        )
        
        assert "successfully completed" in summary.lower()
        assert "0 action" in summary.lower()


# ============================================================================
# Test: Task Routing
# ============================================================================

class TestTaskRouting:
    """Test task routing functionality."""
    
    @pytest.mark.asyncio
    async def test_route_task_web_booking(self, initialized_engine, mock_browser_task):
        """Test routing web booking task."""
        initialized_engine._execute_web_booking = AsyncMock(
            return_value=TaskResult(
                task_id=mock_browser_task.task_id,
                success=True,
                summary="Success",
                actions_taken=[],
                extracted_data={},
                error=None,
                duration_seconds=0.0,
                screenshots=[]
            )
        )
        
        result = await initialized_engine._route_task_by_type(
            task=mock_browser_task,
            progress_callback=Mock()
        )
        
        assert result.success is True
        initialized_engine._execute_web_booking.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_route_task_problem_solving(self, initialized_engine):
        """Test routing problem solving task."""
        task = BrowserTask(
            task_id="task-456",
            description="Solve problem",
            task_type=TaskType.PROBLEM_SOLVING,
            parameters={},
            target_url=None,
            expected_outcome="Problem solved"
        )
        
        initialized_engine._execute_problem_solving = AsyncMock(
            return_value=TaskResult(
                task_id=task.task_id,
                success=True,
                summary="Success",
                actions_taken=[],
                extracted_data={},
                error=None,
                duration_seconds=0.0,
                screenshots=[]
            )
        )
        
        result = await initialized_engine._route_task_by_type(
            task=task,
            progress_callback=Mock()
        )
        
        assert result.success is True
        initialized_engine._execute_problem_solving.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_route_task_app_access(self, initialized_engine):
        """Test routing app access task."""
        task = BrowserTask(
            task_id="task-789",
            description="Access app",
            task_type=TaskType.APP_ACCESS,
            parameters={"app_name": "gmail"},
            target_url="https://mail.google.com",
            expected_outcome="App accessed"
        )
        
        initialized_engine._execute_app_access = AsyncMock(
            return_value=TaskResult(
                task_id=task.task_id,
                success=True,
                summary="Success",
                actions_taken=[],
                extracted_data={},
                error=None,
                duration_seconds=0.0,
                screenshots=[]
            )
        )
        
        result = await initialized_engine._route_task_by_type(
            task=task,
            progress_callback=Mock()
        )
        
        assert result.success is True
        initialized_engine._execute_app_access.assert_called_once()


# ============================================================================
# Test: Task Validation
# ============================================================================

class TestTaskValidation:
    """Test task parameter validation."""
    
    def test_validate_task_parameters_valid_web_booking(self, initialized_engine):
        """Test validating valid web booking task."""
        task = BrowserTask(
            task_id="task-123",
            description="Book flight",
            task_type=TaskType.WEB_BOOKING,
            parameters={"booking_type": "flight"},
            target_url=None,
            expected_outcome="Booked"
        )
        
        is_valid, error = initialized_engine._validate_task_parameters(task)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_task_parameters_missing_description(self, initialized_engine):
        """Test validating task with missing description."""
        task = BrowserTask(
            task_id="task-123",
            description="",
            task_type=TaskType.WEB_BOOKING,
            parameters={"booking_type": "flight"},
            target_url=None,
            expected_outcome="Booked"
        )
        
        is_valid, error = initialized_engine._validate_task_parameters(task)
        
        assert is_valid is False
        assert "description" in error.lower()
    
    def test_validate_task_parameters_missing_booking_type(self, initialized_engine):
        """Test validating web booking without booking_type."""
        task = BrowserTask(
            task_id="task-123",
            description="Book something",
            task_type=TaskType.WEB_BOOKING,
            parameters={"other_param": "value"},  # Has parameters but missing booking_type
            target_url=None,
            expected_outcome="Booked"
        )
        
        is_valid, error = initialized_engine._validate_task_parameters(task)
        
        assert is_valid is False
        assert "booking_type" in error.lower()
    
    def test_validate_task_parameters_app_access_missing_app_name(self, initialized_engine):
        """Test validating app access without app_name."""
        task = BrowserTask(
            task_id="task-123",
            description="Access app",
            task_type=TaskType.APP_ACCESS,
            parameters={"other_param": "value"},  # Has parameters but missing app_name
            target_url=None,
            expected_outcome="Accessed"
        )
        
        is_valid, error = initialized_engine._validate_task_parameters(task)
        
        assert is_valid is False
        assert "app_name" in error.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
