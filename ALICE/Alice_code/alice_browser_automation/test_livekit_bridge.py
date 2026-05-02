"""
Unit tests for LiveKitQwenBridge.

Tests the bridge between LiveKit voice agent and Qwen model, including
voice command translation and model availability validation.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from alice_browser_automation.livekit_bridge import (
    LiveKitQwenBridge,
    create_livekit_bridge,
    VOICE_COMMAND_EXAMPLES
)
from alice_browser_automation.types import BrowserTask, TaskType
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
def bridge(mock_qwen_client):
    """Create LiveKitQwenBridge with mocked QwenModelClient."""
    with patch('alice_browser_automation.livekit_bridge.QwenModelClient', return_value=mock_qwen_client):
        bridge = LiveKitQwenBridge(
            ollama_host="http://localhost:11434",
            model_name="qwen2.5-coder:3b",
            timeout=30
        )
        return bridge


# ============================================================================
# Initialization Tests
# ============================================================================

class TestLiveKitQwenBridgeInit:
    """Test LiveKitQwenBridge initialization."""
    
    def test_init_with_defaults(self, mock_qwen_client):
        """Test initialization with default parameters."""
        with patch('alice_browser_automation.livekit_bridge.QwenModelClient', return_value=mock_qwen_client):
            bridge = LiveKitQwenBridge()
            
            assert bridge.ollama_host == "http://localhost:11434"
            assert bridge.model_name == "qwen2.5-coder:3b"
            assert bridge.timeout == 30
            assert bridge.qwen_client is not None
    
    def test_init_with_custom_params(self, mock_qwen_client):
        """Test initialization with custom parameters."""
        with patch('alice_browser_automation.livekit_bridge.QwenModelClient', return_value=mock_qwen_client):
            bridge = LiveKitQwenBridge(
                ollama_host="http://custom-host:8080",
                model_name="custom-model",
                timeout=60
            )
            
            assert bridge.ollama_host == "http://custom-host:8080"
            assert bridge.model_name == "custom-model"
            assert bridge.timeout == 60
    
    @pytest.mark.asyncio
    async def test_context_manager(self, bridge):
        """Test async context manager protocol."""
        async with bridge as b:
            assert b is bridge
        
        # Verify close was called
        bridge.qwen_client.close.assert_called_once()


# ============================================================================
# Model Availability Tests
# ============================================================================

class TestModelAvailability:
    """Test model availability validation."""
    
    @pytest.mark.asyncio
    async def test_validate_model_available(self, bridge):
        """Test validation when model is available."""
        bridge.qwen_client.validate_model_availability.return_value = True
        
        # Use async validation directly
        is_available = await bridge.qwen_client.validate_model_availability()
        
        assert is_available is True
        bridge.qwen_client.validate_model_availability.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_model_unavailable(self, bridge):
        """Test validation when model is unavailable."""
        bridge.qwen_client.validate_model_availability.side_effect = QwenModelUnavailableError(
            "Model not found",
            host="http://localhost:11434",
            model="qwen2.5-coder:3b"
        )
        
        with pytest.raises(QwenModelUnavailableError) as exc_info:
            await bridge.qwen_client.validate_model_availability()
        
        assert "Model not found" in str(exc_info.value)
        assert exc_info.value.host == "http://localhost:11434"
        assert exc_info.value.model == "qwen2.5-coder:3b"
    
    @pytest.mark.asyncio
    async def test_validate_ollama_unreachable(self, bridge):
        """Test validation when Ollama service is unreachable."""
        bridge.qwen_client.validate_model_availability.side_effect = QwenModelUnavailableError(
            "Cannot connect to Ollama",
            host="http://localhost:11434",
            model="qwen2.5-coder:3b"
        )
        
        with pytest.raises(QwenModelUnavailableError) as exc_info:
            await bridge.qwen_client.validate_model_availability()
        
        assert "Cannot connect to Ollama" in str(exc_info.value)


# ============================================================================
# Voice Command Translation Tests
# ============================================================================

class TestVoiceCommandTranslation:
    """Test voice command translation to BrowserTask."""
    
    @pytest.mark.asyncio
    async def test_translate_flight_booking(self, bridge):
        """Test translating flight booking voice command."""
        # Mock Qwen response
        bridge.qwen_client.generate_json_response.return_value = {
            "task_type": "web_booking",
            "description": "Book flight to Paris",
            "target_url": None,
            "parameters": {
                "booking_type": "flight",
                "destination": "Paris",
                "departure_date": "2025-12-25",
                "passengers": 2
            },
            "expected_outcome": "Flight booking confirmed"
        }
        
        # Translate command
        task = await bridge.translate_voice_command(
            "Book a flight to Paris on December 25th for 2 passengers"
        )
        
        # Verify task structure
        assert isinstance(task, BrowserTask)
        assert task.task_type == TaskType.WEB_BOOKING
        assert task.description == "Book flight to Paris"
        assert task.parameters["booking_type"] == "flight"
        assert task.parameters["destination"] == "Paris"
        assert task.parameters["passengers"] == 2
        assert task.task_id is not None  # UUID generated
    
    @pytest.mark.asyncio
    async def test_translate_food_order(self, bridge):
        """Test translating food order voice command."""
        bridge.qwen_client.generate_json_response.return_value = {
            "task_type": "web_booking",
            "description": "Order pizza from Dominos",
            "target_url": None,
            "parameters": {
                "booking_type": "food",
                "restaurant": "Dominos",
                "items": ["pizza with extra cheese"]
            },
            "expected_outcome": "Food order placed"
        }
        
        task = await bridge.translate_voice_command(
            "Order pizza from Dominos with extra cheese"
        )
        
        assert task.task_type == TaskType.WEB_BOOKING
        assert task.parameters["booking_type"] == "food"
        assert task.parameters["restaurant"] == "Dominos"
        assert "pizza" in task.parameters["items"][0]
    
    @pytest.mark.asyncio
    async def test_translate_problem_solving(self, bridge):
        """Test translating problem solving voice command."""
        bridge.qwen_client.generate_json_response.return_value = {
            "task_type": "problem_solving",
            "description": "Find solution for Python ModuleNotFoundError",
            "target_url": None,
            "parameters": {
                "problem_type": "error",
                "error_message": "ModuleNotFoundError",
                "language": "Python"
            },
            "expected_outcome": "Solution found and presented"
        }
        
        task = await bridge.translate_voice_command(
            "Find a solution for ModuleNotFoundError in Python"
        )
        
        assert task.task_type == TaskType.PROBLEM_SOLVING
        assert task.parameters["error_message"] == "ModuleNotFoundError"
        assert task.parameters["language"] == "Python"
    
    @pytest.mark.asyncio
    async def test_translate_app_access(self, bridge):
        """Test translating app access voice command."""
        bridge.qwen_client.generate_json_response.return_value = {
            "task_type": "app_access",
            "description": "Check Gmail inbox",
            "target_url": "https://mail.google.com",
            "parameters": {
                "app_name": "gmail",
                "action": "check_inbox",
                "filter": "unread"
            },
            "expected_outcome": "Unread messages retrieved"
        }
        
        task = await bridge.translate_voice_command(
            "Check my Gmail inbox for unread messages"
        )
        
        assert task.task_type == TaskType.APP_ACCESS
        assert task.target_url == "https://mail.google.com"
        assert task.parameters["app_name"] == "gmail"
        assert task.parameters["action"] == "check_inbox"
    
    @pytest.mark.asyncio
    async def test_translate_with_context(self, bridge):
        """Test translating voice command with additional context."""
        bridge.qwen_client.generate_json_response.return_value = {
            "task_type": "web_booking",
            "description": "Book flight to Paris",
            "target_url": None,
            "parameters": {
                "booking_type": "flight",
                "destination": "Paris",
                "origin": "SFO",  # From context
                "passengers": 1
            },
            "expected_outcome": "Flight booking confirmed"
        }
        
        context = {
            "user_location": "San Francisco",
            "preferred_airport": "SFO"
        }
        
        task = await bridge.translate_voice_command(
            "Book a flight to Paris",
            context=context
        )
        
        assert task.parameters["origin"] == "SFO"
        
        # Verify context was passed to Qwen
        call_args = bridge.qwen_client.generate_json_response.call_args
        assert "SFO" in call_args[1]["prompt"] or "San Francisco" in call_args[1]["prompt"]
    
    @pytest.mark.asyncio
    async def test_translate_invalid_task_type(self, bridge):
        """Test handling invalid task type from Qwen."""
        bridge.qwen_client.generate_json_response.return_value = {
            "task_type": "invalid_type",
            "description": "Some task",
            "parameters": {}
        }
        
        with pytest.raises(ValueError) as exc_info:
            await bridge.translate_voice_command("Do something")
        
        assert "Invalid task type" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_translate_model_unavailable(self, bridge):
        """Test translation when model is unavailable."""
        bridge.qwen_client.generate_json_response.side_effect = QwenModelUnavailableError(
            "Model unavailable",
            host="http://localhost:11434",
            model="qwen2.5-coder:3b"
        )
        
        with pytest.raises(QwenModelUnavailableError):
            await bridge.translate_voice_command("Book a flight")
    
    @pytest.mark.asyncio
    async def test_translate_generation_error(self, bridge):
        """Test translation when generation fails."""
        bridge.qwen_client.generate_json_response.side_effect = Exception("Generation failed")
        
        with pytest.raises(ValueError) as exc_info:
            await bridge.translate_voice_command("Book a flight")
        
        assert "Could not translate voice command" in str(exc_info.value)


# ============================================================================
# Validate and Translate Tests
# ============================================================================

class TestValidateAndTranslate:
    """Test combined validation and translation."""
    
    @pytest.mark.asyncio
    async def test_validate_and_translate_success(self, bridge):
        """Test successful validation and translation."""
        bridge.qwen_client.validate_model_availability.return_value = True
        bridge.qwen_client.generate_json_response.return_value = {
            "task_type": "web_booking",
            "description": "Book flight",
            "parameters": {"booking_type": "flight"}
        }
        
        task = await bridge.validate_and_translate("Book a flight")
        
        assert isinstance(task, BrowserTask)
        bridge.qwen_client.validate_model_availability.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_and_translate_model_unavailable(self, bridge):
        """Test when model is unavailable during validation."""
        bridge.qwen_client.validate_model_availability.return_value = False
        
        with pytest.raises(QwenModelUnavailableError) as exc_info:
            await bridge.validate_and_translate("Book a flight")
        
        assert "not available" in str(exc_info.value)
        # Should not call generate_json_response if validation fails
        bridge.qwen_client.generate_json_response.assert_not_called()


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests with real-like scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_workflow_flight_booking(self, bridge):
        """Test complete workflow for flight booking."""
        # Setup
        bridge.qwen_client.validate_model_availability.return_value = True
        bridge.qwen_client.generate_json_response.return_value = {
            "task_type": "web_booking",
            "description": "Book round-trip flight to Tokyo",
            "target_url": None,
            "parameters": {
                "booking_type": "flight",
                "origin": "LAX",
                "destination": "Tokyo",
                "departure_date": "2025-06-01",
                "return_date": "2025-06-15",
                "passengers": 2,
                "class_preference": "economy"
            },
            "expected_outcome": "Round-trip flight booking confirmed with confirmation number"
        }
        
        # Execute
        task = await bridge.validate_and_translate(
            "Book a round-trip flight from LAX to Tokyo for 2 passengers, "
            "departing June 1st and returning June 15th, economy class"
        )
        
        # Verify
        assert task.task_type == TaskType.WEB_BOOKING
        assert task.parameters["origin"] == "LAX"
        assert task.parameters["destination"] == "Tokyo"
        assert task.parameters["passengers"] == 2
        assert task.parameters["class_preference"] == "economy"
        assert "round-trip" in task.description.lower() or "round-trip" in task.expected_outcome.lower()
    
    @pytest.mark.asyncio
    async def test_full_workflow_with_retry(self, bridge):
        """Test workflow with retry on invalid response."""
        # First call returns invalid, second call succeeds
        bridge.qwen_client.validate_model_availability.return_value = True
        bridge.qwen_client.generate_json_response.return_value = {
            "task_type": "web_booking",
            "description": "Book hotel",
            "parameters": {"booking_type": "hotel"}
        }
        
        task = await bridge.validate_and_translate("Book a hotel in Paris")
        
        assert task.task_type == TaskType.WEB_BOOKING
        # Verify retry logic was available (max_retries passed to generate_json_response)
        call_kwargs = bridge.qwen_client.generate_json_response.call_args[1]
        assert "max_retries" in call_kwargs


# ============================================================================
# Convenience Function Tests
# ============================================================================

class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @pytest.mark.asyncio
    async def test_create_livekit_bridge_with_validation(self, mock_qwen_client):
        """Test creating bridge with validation."""
        mock_qwen_client.validate_model_availability.return_value = True
        
        with patch('alice_browser_automation.livekit_bridge.QwenModelClient', return_value=mock_qwen_client):
            bridge = await create_livekit_bridge(validate=True)
            
            assert isinstance(bridge, LiveKitQwenBridge)
            mock_qwen_client.validate_model_availability.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_livekit_bridge_without_validation(self, mock_qwen_client):
        """Test creating bridge without validation."""
        with patch('alice_browser_automation.livekit_bridge.QwenModelClient', return_value=mock_qwen_client):
            bridge = await create_livekit_bridge(validate=False)
            
            assert isinstance(bridge, LiveKitQwenBridge)
            mock_qwen_client.validate_model_availability.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_livekit_bridge_custom_params(self, mock_qwen_client):
        """Test creating bridge with custom parameters."""
        mock_qwen_client.validate_model_availability.return_value = True
        
        with patch('alice_browser_automation.livekit_bridge.QwenModelClient', return_value=mock_qwen_client):
            bridge = await create_livekit_bridge(
                ollama_host="http://custom:8080",
                model_name="custom-model",
                timeout=60,
                validate=True
            )
            
            assert bridge.ollama_host == "http://custom:8080"
            assert bridge.model_name == "custom-model"
            assert bridge.timeout == 60


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_empty_voice_command(self, bridge):
        """Test handling empty voice command."""
        bridge.qwen_client.generate_json_response.side_effect = ValueError("Empty command")
        
        with pytest.raises(ValueError):
            await bridge.translate_voice_command("")
    
    @pytest.mark.asyncio
    async def test_very_long_voice_command(self, bridge):
        """Test handling very long voice command."""
        long_command = "Book a flight " * 100  # Very long command
        
        bridge.qwen_client.generate_json_response.return_value = {
            "task_type": "web_booking",
            "description": "Book flight",
            "parameters": {"booking_type": "flight"}
        }
        
        task = await bridge.translate_voice_command(long_command)
        
        assert isinstance(task, BrowserTask)
        # Verify command was passed to Qwen
        bridge.qwen_client.generate_json_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_special_characters_in_command(self, bridge):
        """Test handling special characters in voice command."""
        bridge.qwen_client.generate_json_response.return_value = {
            "task_type": "web_booking",
            "description": "Book flight to São Paulo",
            "parameters": {
                "booking_type": "flight",
                "destination": "São Paulo"
            }
        }
        
        task = await bridge.translate_voice_command(
            "Book a flight to São Paulo with €500 budget"
        )
        
        assert task.parameters["destination"] == "São Paulo"
    
    @pytest.mark.asyncio
    async def test_missing_expected_outcome(self, bridge):
        """Test handling missing expected_outcome field."""
        bridge.qwen_client.generate_json_response.return_value = {
            "task_type": "web_booking",
            "description": "Book flight",
            "parameters": {"booking_type": "flight"}
            # No expected_outcome field
        }
        
        task = await bridge.translate_voice_command("Book a flight")
        
        # Should use default expected_outcome
        assert task.expected_outcome == "Task completed successfully"
    
    @pytest.mark.asyncio
    async def test_close_cleanup(self, bridge):
        """Test proper cleanup on close."""
        await bridge.close()
        
        bridge.qwen_client.close.assert_called_once()


# ============================================================================
# Few-Shot Examples Validation
# ============================================================================

class TestFewShotExamples:
    """Test that few-shot examples are valid."""
    
    def test_voice_command_examples_valid_json(self):
        """Test that all few-shot examples contain valid JSON."""
        for example in VOICE_COMMAND_EXAMPLES:
            assert "user" in example
            assert "assistant" in example
            
            # Verify assistant response is valid JSON
            try:
                parsed = json.loads(example["assistant"])
                assert "task_type" in parsed
                assert "description" in parsed
                assert parsed["task_type"] in ["web_booking", "problem_solving", "app_access"]
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON in example: {example['assistant']}")
    
    def test_voice_command_examples_coverage(self):
        """Test that examples cover all task types."""
        task_types = set()
        for example in VOICE_COMMAND_EXAMPLES:
            parsed = json.loads(example["assistant"])
            task_types.add(parsed["task_type"])
        
        assert "web_booking" in task_types
        assert "problem_solving" in task_types
        assert "app_access" in task_types
