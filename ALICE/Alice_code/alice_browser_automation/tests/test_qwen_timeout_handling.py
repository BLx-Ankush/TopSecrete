"""
Unit tests for Qwen Model Client timeout handling.

Tests timeout scenarios for model requests and validates proper error handling.

**Validates: Requirements 4.6, 12.3**
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from alice_browser_automation.qwen_client import (
    QwenModelClient,
    ACTION_RESPONSE_SCHEMA
)
from alice_browser_automation.exceptions import QwenModelUnavailableError


class TestQwenTimeoutHandling:
    """Test timeout handling for Qwen model requests."""
    
    @pytest.fixture
    def client(self):
        """Create a QwenModelClient instance with short timeout."""
        return QwenModelClient(
            host="http://localhost:11434",
            model="qwen2.5-coder:3b",
            timeout=5  # Short timeout for testing
        )
    
    @pytest.mark.asyncio
    async def test_timeout_on_model_availability_check(self, client):
        """Test timeout during model availability validation."""
        # Mock timeout error
        client.client.get = AsyncMock(
            side_effect=httpx.ReadTimeout("Request timed out")
        )
        
        # Should raise QwenModelUnavailableError
        with pytest.raises(QwenModelUnavailableError) as exc_info:
            await client.validate_model_availability()
        
        assert "Unexpected error" in str(exc_info.value)
        assert exc_info.value.host == "http://localhost:11434"
        assert exc_info.value.model == "qwen2.5-coder:3b"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_timeout_on_text_generation(self, client):
        """Test timeout during text generation."""
        # Mock timeout error
        client.client.post = AsyncMock(
            side_effect=httpx.ReadTimeout("Request timed out after 5 seconds")
        )
        
        # Should raise QwenModelUnavailableError
        with pytest.raises(QwenModelUnavailableError) as exc_info:
            await client.generate_with_prompt(
                system_prompt="You are a helpful assistant",
                user_prompt="What is 2+2?"
            )
        
        assert "Generation failed" in str(exc_info.value)
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_timeout_on_json_generation(self, client):
        """Test timeout during JSON generation."""
        # Mock timeout error
        client.client.post = AsyncMock(
            side_effect=httpx.ReadTimeout("Request timed out")
        )
        
        # Should raise QwenModelUnavailableError
        with pytest.raises(QwenModelUnavailableError) as exc_info:
            await client.generate_json_response(
                prompt="Click the submit button",
                schema=ACTION_RESPONSE_SCHEMA
            )
        
        assert "Generation failed" in str(exc_info.value)
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_timeout_configuration_respected(self):
        """Test that timeout configuration is properly set."""
        # Create client with custom timeout
        client = QwenModelClient(timeout=10)
        
        # Verify timeout is set correctly
        assert client.timeout == 10
        assert client.client.timeout.read == 10
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_timeout_with_retry_logic(self, client):
        """Test that timeout errors are not retried in JSON generation."""
        # Mock timeout error
        client.generate_with_prompt = AsyncMock(
            side_effect=QwenModelUnavailableError(
                "Request timed out",
                host="http://localhost:11434",
                model="qwen2.5-coder:3b"
            )
        )
        
        # Should raise immediately without retry
        with pytest.raises(QwenModelUnavailableError):
            await client.generate_json_response(
                prompt="Test",
                schema=ACTION_RESPONSE_SCHEMA,
                max_retries=3
            )
        
        # Should only try once (no retries for model unavailable errors)
        assert client.generate_with_prompt.call_count == 1
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_slow_response_within_timeout(self, client):
        """Test that slow but successful responses work within timeout."""
        # Mock slow but successful response
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(0.5)  # Simulate slow response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "message": {"content": "Response"}
            }
            mock_response.raise_for_status = MagicMock()
            return mock_response
        
        client.client.post = slow_response
        
        # Should succeed
        result = await client.generate_with_prompt(
            system_prompt="System",
            user_prompt="User"
        )
        
        assert result == "Response"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_timeout_error_includes_context(self, client):
        """Test that timeout errors include helpful context."""
        # Mock timeout with detailed error
        timeout_error = httpx.ReadTimeout(
            "Request timed out after 5.0 seconds"
        )
        client.client.post = AsyncMock(side_effect=timeout_error)
        
        # Capture the error
        with pytest.raises(QwenModelUnavailableError) as exc_info:
            await client.generate_with_prompt(
                system_prompt="System",
                user_prompt="User"
            )
        
        # Verify error contains useful information
        error = exc_info.value
        assert error.host == "http://localhost:11434"
        assert error.model == "qwen2.5-coder:3b"
        assert error.original_error is timeout_error
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_connection_timeout_vs_read_timeout(self, client):
        """Test distinction between connection and read timeouts."""
        # Test connection timeout
        client.client.post = AsyncMock(
            side_effect=httpx.ConnectTimeout("Connection timed out")
        )
        
        with pytest.raises(QwenModelUnavailableError) as exc_info:
            await client.generate_with_prompt("System", "User")
        
        assert "Generation failed" in str(exc_info.value)
        
        # Test read timeout
        client.client.post = AsyncMock(
            side_effect=httpx.ReadTimeout("Read timed out")
        )
        
        with pytest.raises(QwenModelUnavailableError) as exc_info:
            await client.generate_with_prompt("System", "User")
        
        assert "Generation failed" in str(exc_info.value)
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_timeout_during_model_list_retrieval(self, client):
        """Test timeout when retrieving model list."""
        # Mock timeout on GET request
        client.client.get = AsyncMock(
            side_effect=httpx.ReadTimeout("Timeout retrieving models")
        )
        
        with pytest.raises(QwenModelUnavailableError):
            await client.validate_model_availability()
        
        await client.close()


class TestTimeoutConfiguration:
    """Test timeout configuration and edge cases."""
    
    def test_default_timeout_value(self):
        """Test that default timeout is set correctly."""
        client = QwenModelClient()
        assert client.timeout == 30
    
    def test_custom_timeout_value(self):
        """Test setting custom timeout value."""
        client = QwenModelClient(timeout=60)
        assert client.timeout == 60
    
    def test_very_short_timeout(self):
        """Test that very short timeouts are accepted."""
        client = QwenModelClient(timeout=1)
        assert client.timeout == 1
    
    def test_very_long_timeout(self):
        """Test that very long timeouts are accepted."""
        client = QwenModelClient(timeout=300)
        assert client.timeout == 300
    
    @pytest.mark.asyncio
    async def test_timeout_applies_to_all_requests(self):
        """Test that timeout configuration applies to all HTTP requests."""
        client = QwenModelClient(timeout=15)
        
        # Verify timeout is set on the HTTP client
        assert client.client.timeout.read == 15
        
        await client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
