"""
Unit tests for Qwen Model Client retry logic.

Tests the retry mechanism with exponential backoff for invalid JSON responses.

**Validates: Requirements 4.5, 4.6**
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from alice_browser_automation.qwen_client import QwenModelClient, ACTION_RESPONSE_SCHEMA
from alice_browser_automation.exceptions import InvalidActionError, QwenModelUnavailableError


class TestQwenRetryLogic:
    """Test retry logic for invalid JSON responses."""
    
    @pytest.fixture
    def client(self):
        """Create a QwenModelClient instance."""
        return QwenModelClient(
            host="http://localhost:11434",
            model="qwen2.5-coder:3b",
            timeout=30
        )
    
    @pytest.mark.asyncio
    async def test_successful_first_attempt(self, client):
        """Test successful JSON generation on first attempt (no retry needed)."""
        # Arrange
        valid_json = """
        {
            "action_type": "click",
            "target_selector": {
                "css_selector": "button.submit",
                "xpath": "//button[@class='submit']",
                "aria_label": "Submit"
            },
            "parameters": {},
            "expected_result": "Form submitted"
        }
        """
        
        # Mock generate_with_prompt to return valid JSON
        client.generate_with_prompt = AsyncMock(return_value=valid_json)
        
        # Act
        result = await client.generate_json_response(
            prompt="Click the submit button",
            schema=ACTION_RESPONSE_SCHEMA
        )
        
        # Assert
        assert result is not None
        assert result["action_type"] == "click"
        assert result["expected_result"] == "Form submitted"
        assert client.generate_with_prompt.call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_invalid_json_success_on_second_attempt(self, client):
        """Test retry logic when first attempt fails but second succeeds."""
        # Arrange
        invalid_json = "This is not valid JSON"
        valid_json = """
        {
            "action_type": "type",
            "target_selector": {
                "css_selector": "input#email",
                "xpath": "//input[@id='email']",
                "aria_label": null
            },
            "parameters": {
                "text": "test@example.com",
                "clear_first": true
            },
            "expected_result": "Email entered"
        }
        """
        
        # Mock generate_with_prompt to return invalid JSON first, then valid
        client.generate_with_prompt = AsyncMock(side_effect=[invalid_json, valid_json])
        
        # Mock sleep to avoid waiting
        client._async_sleep = AsyncMock()
        
        # Act
        result = await client.generate_json_response(
            prompt="Type email address",
            schema=ACTION_RESPONSE_SCHEMA,
            max_retries=3
        )
        
        # Assert
        assert result is not None
        assert result["action_type"] == "type"
        assert result["parameters"]["text"] == "test@example.com"
        assert client.generate_with_prompt.call_count == 2
        # Verify exponential backoff was called with 1 second (2^0)
        client._async_sleep.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_error(self, client):
        """Test that InvalidActionError is raised after max retries."""
        # Arrange
        invalid_json = "Invalid JSON response"
        
        # Mock generate_with_prompt to always return invalid JSON
        client.generate_with_prompt = AsyncMock(return_value=invalid_json)
        
        # Mock sleep to avoid waiting
        client._async_sleep = AsyncMock()
        
        # Act & Assert
        with pytest.raises(InvalidActionError) as exc_info:
            await client.generate_json_response(
                prompt="Click button",
                schema=ACTION_RESPONSE_SCHEMA,
                max_retries=3
            )
        
        # Verify error message
        assert "after 3 retries" in str(exc_info.value)
        
        # Verify all retries were attempted (1 initial + 3 retries = 4 calls)
        assert client.generate_with_prompt.call_count == 4
        
        # Verify exponential backoff was called correctly
        assert client._async_sleep.call_count == 3
        # Check backoff delays: 1s, 2s, 4s
        calls = client._async_sleep.call_args_list
        assert calls[0][0][0] == 1  # 2^0 = 1
        assert calls[1][0][0] == 2  # 2^1 = 2
        assert calls[2][0][0] == 4  # 2^2 = 4
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, client):
        """Test that exponential backoff delays are correct."""
        # Arrange
        invalid_json = "Not JSON"
        
        client.generate_with_prompt = AsyncMock(return_value=invalid_json)
        
        # Track sleep calls
        sleep_calls = []
        
        async def mock_sleep(seconds):
            sleep_calls.append(seconds)
        
        client._async_sleep = mock_sleep
        
        # Act
        with pytest.raises(InvalidActionError):
            await client.generate_json_response(
                prompt="Test",
                schema=ACTION_RESPONSE_SCHEMA,
                max_retries=3
            )
        
        # Assert exponential backoff: 1s, 2s, 4s
        assert sleep_calls == [1, 2, 4]
    
    @pytest.mark.asyncio
    async def test_correction_prompt_includes_error_context(self, client):
        """Test that retry includes error context in prompt."""
        # Arrange
        invalid_json = '{"action_type": "invalid_action"}'  # Invalid action type
        valid_json = """
        {
            "action_type": "click",
            "target_selector": {"css_selector": "button"},
            "parameters": {},
            "expected_result": "Clicked"
        }
        """
        
        client.generate_with_prompt = AsyncMock(side_effect=[invalid_json, valid_json])
        client._async_sleep = AsyncMock()
        
        # Act
        result = await client.generate_json_response(
            prompt="Click button",
            schema=ACTION_RESPONSE_SCHEMA,
            max_retries=3
        )
        
        # Assert
        assert result is not None
        assert client.generate_with_prompt.call_count == 2
        
        # Check that second call includes correction prompt
        second_call_prompt = client.generate_with_prompt.call_args_list[1][1]["user_prompt"]
        assert "previous response was invalid" in second_call_prompt.lower()
        assert "error" in second_call_prompt.lower()
    
    @pytest.mark.asyncio
    async def test_retry_with_missing_required_field(self, client):
        """Test retry when JSON is missing required fields."""
        # Arrange
        invalid_json = '{"parameters": {}}'  # Missing action_type
        valid_json = """
        {
            "action_type": "navigate",
            "target_selector": null,
            "parameters": {"url": "https://example.com"},
            "expected_result": "Page loaded"
        }
        """
        
        client.generate_with_prompt = AsyncMock(side_effect=[invalid_json, valid_json])
        client._async_sleep = AsyncMock()
        
        # Act
        result = await client.generate_json_response(
            prompt="Navigate to example.com",
            schema=ACTION_RESPONSE_SCHEMA,
            max_retries=3
        )
        
        # Assert
        assert result is not None
        assert result["action_type"] == "navigate"
        assert client.generate_with_prompt.call_count == 2
    
    @pytest.mark.asyncio
    async def test_model_unavailable_error_not_retried(self, client):
        """Test that QwenModelUnavailableError is not retried."""
        # Arrange
        client.generate_with_prompt = AsyncMock(
            side_effect=QwenModelUnavailableError(
                "Model unavailable",
                host="http://localhost:11434",
                model="qwen2.5-coder:3b"
            )
        )
        
        # Act & Assert
        with pytest.raises(QwenModelUnavailableError):
            await client.generate_json_response(
                prompt="Test",
                schema=ACTION_RESPONSE_SCHEMA,
                max_retries=3
            )
        
        # Should only try once, not retry on model unavailable
        assert client.generate_with_prompt.call_count == 1
    
    @pytest.mark.asyncio
    async def test_max_retries_parameter_respected(self, client):
        """Test that max_retries parameter is respected."""
        # Arrange
        invalid_json = "Invalid"
        client.generate_with_prompt = AsyncMock(return_value=invalid_json)
        client._async_sleep = AsyncMock()
        
        # Act & Assert - Test with max_retries=2
        with pytest.raises(InvalidActionError) as exc_info:
            await client.generate_json_response(
                prompt="Test",
                schema=ACTION_RESPONSE_SCHEMA,
                max_retries=2
            )
        
        assert "after 2 retries" in str(exc_info.value)
        # 1 initial + 2 retries = 3 calls
        assert client.generate_with_prompt.call_count == 3
        assert client._async_sleep.call_count == 2
    
    @pytest.mark.asyncio
    async def test_success_on_third_attempt(self, client):
        """Test successful generation on third attempt."""
        # Arrange
        invalid_json_1 = "Not JSON"
        invalid_json_2 = '{"action_type": "invalid"}'
        valid_json = """
        {
            "action_type": "wait",
            "target_selector": {"css_selector": ".loading"},
            "parameters": {"condition": "hidden", "timeout_ms": 5000},
            "expected_result": "Loading complete"
        }
        """
        
        client.generate_with_prompt = AsyncMock(
            side_effect=[invalid_json_1, invalid_json_2, valid_json]
        )
        client._async_sleep = AsyncMock()
        
        # Act
        result = await client.generate_json_response(
            prompt="Wait for loading",
            schema=ACTION_RESPONSE_SCHEMA,
            max_retries=3
        )
        
        # Assert
        assert result is not None
        assert result["action_type"] == "wait"
        assert client.generate_with_prompt.call_count == 3
        assert client._async_sleep.call_count == 2
    
    @pytest.mark.asyncio
    async def test_json_with_markdown_code_blocks_retried(self, client):
        """Test that JSON wrapped in markdown is handled correctly."""
        # Arrange
        # First attempt: invalid JSON
        invalid_json = "```json\n{invalid}\n```"
        # Second attempt: valid JSON in markdown
        valid_json_markdown = """```json
        {
            "action_type": "extract",
            "target_selector": {"css_selector": ".result"},
            "parameters": {"extract_type": "text"},
            "expected_result": "Data extracted"
        }
        ```"""
        
        client.generate_with_prompt = AsyncMock(
            side_effect=[invalid_json, valid_json_markdown]
        )
        client._async_sleep = AsyncMock()
        
        # Act
        result = await client.generate_json_response(
            prompt="Extract data",
            schema=ACTION_RESPONSE_SCHEMA,
            max_retries=3
        )
        
        # Assert
        assert result is not None
        assert result["action_type"] == "extract"
        assert client.generate_with_prompt.call_count == 2


class TestAsyncSleepHelper:
    """Test the async sleep helper method."""
    
    @pytest.mark.asyncio
    async def test_async_sleep_waits_correct_duration(self):
        """Test that _async_sleep waits for the correct duration."""
        # Arrange
        client = QwenModelClient()
        start_time = asyncio.get_event_loop().time()
        
        # Act
        await client._async_sleep(0.1)  # Sleep for 100ms
        
        # Assert
        elapsed = asyncio.get_event_loop().time() - start_time
        assert elapsed >= 0.1
        assert elapsed < 0.2  # Should not take too long


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
