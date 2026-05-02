"""
Unit tests for Browser Automation Engine.

Tests the core orchestrator functionality including initialization,
shutdown, task execution, and component integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from alice_browser_automation.engine import BrowserAutomationEngine
from alice_browser_automation.config import Config, BrowserConfig, QwenConfig
from alice_browser_automation.types import (
    TaskType, TaskResult, BrowserTask, BrowserSession, SessionState
)
from alice_browser_automation.exceptions import (
    BrowserAutomationError, QwenModelUnavailableError
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Config()
    config.browser = BrowserConfig(
        headless_default=True,
        max_concurrent_sessions=3,
        idle_timeout_seconds=300,
        profiles_dir="/tmp/test_profiles",
        default_profile="test"
    )
    config.qwen = QwenConfig(
        host="http://localhost:11434",
        model="qwen2.5-coder:3b",
        timeout_seconds=30,
        max_retries=3
    )
    return config


@pytest.fixture
def mock_session():
    """Create a mock browser session."""
    return BrowserSession(
        session_id="test-session-123",
        profile_name="test",
        domain="example.com",
        playwright_context=Mock(),
        playwright_page=Mock(),
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


# ============================================================================
# Test: Initialization and Shutdown
# ============================================================================

class TestInitializationAndShutdown:
    """Test engine initialization and shutdown."""
    
    @pytest.mark.asyncio
    async def test_init_creates_engine(self, mock_config):
        """Test that __init__ creates engine instance."""
        engine = BrowserAutomationEngine(config=mock_config)
        
        assert engine is not None
        assert engine.config == mock_config
        assert not engine.is_initialized
        assert engine.profile_manager is None
        assert engine.session_manager is None
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_config):
        """Test successful engine initialization."""
        engine = BrowserAutomationEngine(config=mock_config)
        
        # Mock all component initializations
        with patch('alice_browser_automation.engine.ChromeProfileManager') as mock_pm, \
             patch('alice_browser_automation.engine.SessionManager') as mock_sm, \
             patch('alice_browser_automation.engine.DOMParser') as mock_dp, \
             patch('alice_browser_automation.engine.LiveKitQwenBridge') as mock_bridge, \
             patch('alice_browser_automation.engine.ErrorHandler') as mock_eh:
            
            # Set up mocks
            mock_sm_instance = AsyncMock()
            mock_sm.return_value = mock_sm_instance
            
            mock_bridge_instance = AsyncMock()
            mock_bridge_instance.qwen_client = AsyncMock()
            mock_bridge_instance.qwen_client.validate_model_availability = AsyncMock(return_value=True)
            mock_bridge.return_value = mock_bridge_instance
            
            # Initialize
            result = await engine.initialize()
            
            # Assertions
            assert result is True
            assert engine.is_initialized
            assert engine.profile_manager is not None
            assert engine.session_manager is not None
            assert engine.dom_parser is not None
            assert engine.livekit_bridge is not None
            assert engine.error_handler is not None
            
            # Verify component initialization calls
            mock_sm_instance.initialize.assert_called_once()
            mock_bridge_instance.qwen_client.validate_model_availability.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_model_unavailable(self, mock_config):
        """Test initialization fails when Qwen model is unavailable."""
        engine = BrowserAutomationEngine(config=mock_config)
        
        with patch('alice_browser_automation.engine.ChromeProfileManager'), \
             patch('alice_browser_automation.engine.SessionManager') as mock_sm, \
             patch('alice_browser_automation.engine.DOMParser'), \
             patch('alice_browser_automation.engine.LiveKitQwenBridge') as mock_bridge:
            
            # Set up mocks
            mock_sm_instance = AsyncMock()
            mock_sm.return_value = mock_sm_instance
            
            mock_bridge_instance = AsyncMock()
            mock_bridge_instance.qwen_client = AsyncMock()
            mock_bridge_instance.qwen_client.validate_model_availability = AsyncMock(return_value=False)
            mock_bridge.return_value = mock_bridge_instance
            
            # Initialize should raise QwenModelUnavailableError
            with pytest.raises(QwenModelUnavailableError):
                await engine.initialize()
            
            assert not engine.is_initialized
    
    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, mock_config):
        """Test that initializing twice returns True without re-initializing."""
        engine = BrowserAutomationEngine(config=mock_config)
        
        with patch('alice_browser_automation.engine.ChromeProfileManager'), \
             patch('alice_browser_automation.engine.SessionManager') as mock_sm, \
             patch('alice_browser_automation.engine.DOMParser'), \
             patch('alice_browser_automation.engine.LiveKitQwenBridge') as mock_bridge, \
             patch('alice_browser_automation.engine.ErrorHandler'):
            
            # Set up mocks
            mock_sm_instance = AsyncMock()
            mock_sm.return_value = mock_sm_instance
            
            mock_bridge_instance = AsyncMock()
            mock_bridge_instance.qwen_client = AsyncMock()
            mock_bridge_instance.qwen_client.validate_model_availability = AsyncMock(return_value=True)
            mock_bridge.return_value = mock_bridge_instance
            
            # First initialization
            await engine.initialize()
            assert engine.is_initialized
            
            # Second initialization should return True without re-initializing
            result = await engine.initialize()
            assert result is True
            
            # Verify components were only initialized once
            assert mock_sm_instance.initialize.call_count == 1
    
    @pytest.mark.asyncio
    async def test_shutdown_success(self, mock_config):
        """Test successful engine shutdown."""
        engine = BrowserAutomationEngine(config=mock_config)
        
        # Mock components
        engine.livekit_bridge = AsyncMock()
        engine.session_manager = AsyncMock()
        engine.dom_parser = Mock()
        engine.dom_parser.clear_cache = Mock()
        engine.is_initialized = True
        
        # Shutdown
        await engine.shutdown()
        
        # Assertions
        assert not engine.is_initialized
        engine.livekit_bridge.close.assert_called_once()
        engine.session_manager.shutdown.assert_called_once()
        engine.dom_parser.clear_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_not_initialized(self, mock_config):
        """Test shutdown when engine is not initialized."""
        engine = BrowserAutomationEngine(config=mock_config)
        
        # Shutdown should not raise error
        await engine.shutdown()
        
        assert not engine.is_initialized


# ============================================================================
# Test: Session Management
# ============================================================================

class TestSessionManagement:
    """Test session management functionality."""
    
    @pytest.mark.asyncio
    async def test_get_active_sessions_not_initialized(self, mock_config):
        """Test get_active_sessions when engine not initialized."""
        engine = BrowserAutomationEngine(config=mock_config)
        
        sessions = engine.get_active_sessions()
        
        assert sessions == []
    
    @pytest.mark.asyncio
    async def test_get_active_sessions_success(self, mock_config, mock_session):
        """Test get_active_sessions returns active sessions."""
        engine = BrowserAutomationEngine(config=mock_config)
        
        # Mock session manager
        engine.session_manager = Mock()
        engine.session_manager.get_all_sessions = Mock(return_value=[mock_session])
        engine.is_initialized = True
        
        sessions = engine.get_active_sessions()
        
        assert len(sessions) == 1
        assert sessions[0] == mock_session
        engine.session_manager.get_all_sessions.assert_called_once()


# ============================================================================
# Test: Task Execution
# ============================================================================

class TestTaskExecution:
    """Test task execution functionality."""
    
    @pytest.mark.asyncio
    async def test_execute_task_not_initialized(self, mock_config):
        """Test execute_task raises error when engine not initialized."""
        engine = BrowserAutomationEngine(config=mock_config)
        
        with pytest.raises(BrowserAutomationError, match="not initialized"):
            await engine.execute_task(
                task_description="Test task",
                task_type=TaskType.WEB_BOOKING,
                parameters={},
                callback=None
            )
    
    @pytest.mark.asyncio
    async def test_execute_task_web_booking(self, mock_config, mock_browser_task):
        """Test execute_task for web booking task."""
        engine = BrowserAutomationEngine(config=mock_config)
        engine.is_initialized = True
        
        # Mock components
        engine.livekit_bridge = AsyncMock()
        engine.livekit_bridge.translate_voice_command = AsyncMock(return_value=mock_browser_task)
        
        # Mock _execute_web_booking
        expected_result = TaskResult(
            task_id=mock_browser_task.task_id,
            success=False,
            summary="Not implemented",
            actions_taken=[],
            extracted_data={},
            error="Not implemented",
            duration_seconds=0.0,
            screenshots=[]
        )
        engine._execute_web_booking = AsyncMock(return_value=expected_result)
        
        # Execute task
        result = await engine.execute_task(
            task_description="Book a flight",
            task_type=TaskType.WEB_BOOKING,
            parameters={"destination": "Paris"},
            callback=None
        )
        
        # Assertions
        assert result.task_id == mock_browser_task.task_id
        assert result.success is False
        engine.livekit_bridge.translate_voice_command.assert_called_once()
        engine._execute_web_booking.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_task_problem_solving(self, mock_config):
        """Test execute_task for problem solving task."""
        engine = BrowserAutomationEngine(config=mock_config)
        engine.is_initialized = True
        
        # Mock components
        mock_task = BrowserTask(
            task_id="task-456",
            description="Solve problem",
            task_type=TaskType.PROBLEM_SOLVING,
            parameters={},
            target_url=None,
            expected_outcome="Problem solved"
        )
        
        engine.livekit_bridge = AsyncMock()
        engine.livekit_bridge.translate_voice_command = AsyncMock(return_value=mock_task)
        
        expected_result = TaskResult(
            task_id=mock_task.task_id,
            success=False,
            summary="Not implemented",
            actions_taken=[],
            extracted_data={},
            error="Not implemented",
            duration_seconds=0.0,
            screenshots=[]
        )
        engine._execute_problem_solving = AsyncMock(return_value=expected_result)
        
        # Execute task
        result = await engine.execute_task(
            task_description="Find solution for error",
            task_type=TaskType.PROBLEM_SOLVING,
            parameters={},
            callback=None
        )
        
        # Assertions
        assert result.task_id == mock_task.task_id
        engine._execute_problem_solving.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_task_app_access(self, mock_config):
        """Test execute_task for app access task."""
        engine = BrowserAutomationEngine(config=mock_config)
        engine.is_initialized = True
        
        # Mock components
        mock_task = BrowserTask(
            task_id="task-789",
            description="Access app",
            task_type=TaskType.APP_ACCESS,
            parameters={},
            target_url="https://mail.google.com",
            expected_outcome="App accessed"
        )
        
        engine.livekit_bridge = AsyncMock()
        engine.livekit_bridge.translate_voice_command = AsyncMock(return_value=mock_task)
        
        expected_result = TaskResult(
            task_id=mock_task.task_id,
            success=False,
            summary="Not implemented",
            actions_taken=[],
            extracted_data={},
            error="Not implemented",
            duration_seconds=0.0,
            screenshots=[]
        )
        engine._execute_app_access = AsyncMock(return_value=expected_result)
        
        # Execute task
        result = await engine.execute_task(
            task_description="Check Gmail",
            task_type=TaskType.APP_ACCESS,
            parameters={},
            callback=None
        )
        
        # Assertions
        assert result.task_id == mock_task.task_id
        engine._execute_app_access.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_task_with_callback(self, mock_config, mock_browser_task):
        """Test execute_task calls progress callback."""
        engine = BrowserAutomationEngine(config=mock_config)
        engine.is_initialized = True
        
        # Mock components
        engine.livekit_bridge = AsyncMock()
        engine.livekit_bridge.translate_voice_command = AsyncMock(return_value=mock_browser_task)
        
        expected_result = TaskResult(
            task_id=mock_browser_task.task_id,
            success=True,
            summary="Task completed",
            actions_taken=[],
            extracted_data={},
            error=None,
            duration_seconds=0.0,
            screenshots=[]
        )
        engine._execute_web_booking = AsyncMock(return_value=expected_result)
        
        # Create callback mock
        callback_mock = Mock()
        
        # Execute task
        await engine.execute_task(
            task_description="Test task",
            task_type=TaskType.WEB_BOOKING,
            parameters={},
            callback=callback_mock
        )
        
        # Assertions - callback should be called at least once
        assert callback_mock.call_count > 0
    
    @pytest.mark.asyncio
    async def test_execute_task_handles_exception(self, mock_config):
        """Test execute_task handles exceptions gracefully."""
        engine = BrowserAutomationEngine(config=mock_config)
        engine.is_initialized = True
        
        # Mock components to raise exception
        engine.livekit_bridge = AsyncMock()
        engine.livekit_bridge.translate_voice_command = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        # Execute task
        result = await engine.execute_task(
            task_description="Test task",
            task_type=TaskType.WEB_BOOKING,
            parameters={},
            callback=None
        )
        
        # Assertions - should return error result
        assert result.success is False
        assert "Test error" in result.error
        assert result.summary.startswith("Task failed")


# ============================================================================
# Test: Configuration Loading
# ============================================================================

class TestConfigurationLoading:
    """Test configuration loading."""
    
    def test_engine_loads_default_config(self):
        """Test engine loads default config when none provided."""
        with patch('alice_browser_automation.engine.Config.load') as mock_load:
            mock_config = Config()
            mock_load.return_value = mock_config
            
            engine = BrowserAutomationEngine()
            
            assert engine.config == mock_config
            mock_load.assert_called_once()
    
    def test_engine_uses_provided_config(self, mock_config):
        """Test engine uses provided config."""
        engine = BrowserAutomationEngine(config=mock_config)
        
        assert engine.config == mock_config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
