"""
Unit tests for QwenModelClient.

Tests cover:
- Initialization and configuration
- Model availability validation
- Text generation with few-shot examples
- JSON response generation and validation
- Connection pooling
- Error handling
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from alice_browser_automation.qwen_client import (
    QwenModelClient,
    create_qwen_client,
    SYSTEM_PROMPT,
    FEW_SHOT_EXAMPLES
)
from alice_browser_automation.exceptions import (
    QwenModelUnavailableError,
    InvalidActionError
)


class TestQwenModelClientInitialization:
    """Test QwenModelClient initialization and configuration."""
    
    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        client = QwenModelClient()
        
        assert client.host == "http://localhost:11434"
        assert client.model == "qwen2.5-coder:3b"
        assert client.timeout == 30
        assert client.client is not None
    
    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        client = QwenModelClient(
            host="http://custom-host:8080",
            model="custom-model",
            timeout=60
        )
        
        assert client.host == "http://custom-host:8080"
        assert client.model == "custom-model"
        assert client.timeout == 60
    
    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is removed from host."""
        client = QwenModelClient(host="http://localhost:11434/")
        assert client.host == "http://localhost:11434"
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager usage."""
        async with QwenModelClient() as client:
            assert client is not None
            assert client.client is not None
        
        # Client should be closed after context exit
        # (We can't easily test this without accessing internal state)
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test explicit close method."""
        client = QwenModelClient()
        await client.close()
        # Should not raise any errors


class TestModelAvailability:
    """Test model availability validation."""
    
    @pytest.mark.asyncio
    async def test_validate_model_available(self):
        """Test validation when model is available."""
        client = QwenModelClient()
        
        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "qwen2.5-coder:3b"},
                {"name": "llama2:7b"}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        client.client.get = AsyncMock(return_value=mock_response)
        
        # Should return True
        is_available = await client.validate_model_availability()
        assert is_available is True
        
        # Verify the correct endpoint was called
        client.client.get.assert_called_once_with("http://localhost:11434/api/tags")
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_validate_model_not_available(self):
        """Test validation when model is not in list."""
        client = QwenModelClient()
        
        # Mock response without our model
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama2:7b"},
                {"name": "mistral:7b"}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        client.client.get = AsyncMock(return_value=mock_response)
        
        # Should return False
        is_available = await client.validate_model_availability()
        assert is_available is False
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_validate_connection_error(self):
        """Test validation when Ollama is unreachable."""
        client = QwenModelClient()
        
        # Mock connection error
        client.client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        
        # Should raise QwenModelUnavailableError
        with pytest.raises(QwenModelUnavailableError) as exc_info:
            await client.validate_model_availability()
        
        assert "Cannot connect to Ollama" in str(exc_info.value)
        assert exc_info.value.host == "http://localhost:11434"
        assert exc_info.value.model == "qwen2.5-coder:3b"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_validate_http_error(self):
        """Test validation when Ollama returns HTTP error."""
        client = QwenModelClient()
        
        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.status_code = 500
        error = httpx.HTTPStatusError("Server error", request=MagicMock(), response=mock_response)
        client.client.get = AsyncMock(side_effect=error)
        
        # Should raise QwenModelUnavailableError
        with pytest.raises(QwenModelUnavailableError) as exc_info:
            await client.validate_model_availability()
        
        assert "Ollama API error" in str(exc_info.value)
        
        await client.close()


class TestTextGeneration:
    """Test text generation with prompts."""
    
    @pytest.mark.asyncio
    async def test_generate_with_prompt_basic(self):
        """Test basic text generation."""
        client = QwenModelClient()
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "content": "Generated response text"
            }
        }
        mock_response.raise_for_status = MagicMock()
        
        client.client.post = AsyncMock(return_value=mock_response)
        
        # Generate text
        result = await client.generate_with_prompt(
            system_prompt="You are a helpful assistant",
            user_prompt="What is 2+2?"
        )
        
        assert result == "Generated response text"
        
        # Verify request was made correctly
        client.client.post.assert_called_once()
        call_args = client.client.post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/chat"
        
        payload = call_args[1]["json"]
        assert payload["model"] == "qwen2.5-coder:3b"
        assert len(payload["messages"]) == 2  # system + user
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_generate_with_few_shot_examples(self):
        """Test generation with few-shot examples."""
        client = QwenModelClient()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "Response"}
        }
        mock_response.raise_for_status = MagicMock()
        
        client.client.post = AsyncMock(return_value=mock_response)
        
        few_shot = [
            {"user": "Example 1", "assistant": "Response 1"},
            {"user": "Example 2", "assistant": "Response 2"}
        ]
        
        result = await client.generate_with_prompt(
            system_prompt="System",
            user_prompt="User prompt",
            few_shot_examples=few_shot
        )
        
        # Verify messages include few-shot examples
        payload = client.client.post.call_args[1]["json"]
        messages = payload["messages"]
        
        # Should have: system + 2 examples (user+assistant each) + user prompt
        assert len(messages) == 6
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Example 1"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Response 1"
        assert messages[5]["role"] == "user"
        assert messages[5]["content"] == "User prompt"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_generate_connection_error(self):
        """Test generation with connection error."""
        client = QwenModelClient()
        
        client.client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        
        with pytest.raises(QwenModelUnavailableError) as exc_info:
            await client.generate_with_prompt("system", "user")
        
        assert "Cannot connect to Ollama" in str(exc_info.value)
        
        await client.close()


class TestJSONGeneration:
    """Test JSON response generation and validation."""
    
    @pytest.mark.asyncio
    async def test_generate_json_response_valid(self):
        """Test generating valid JSON response."""
        client = QwenModelClient()
        
        # Mock response with valid JSON
        valid_json = {
            "action_type": "click",
            "target_selector": {
                "css_selector": "button.submit",
                "xpath": "//button[@class='submit']",
                "aria_label": "Submit"
            },
            "parameters": {},
            "expected_result": "Form submitted"
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": json.dumps(valid_json)}
        }
        mock_response.raise_for_status = MagicMock()
        
        client.client.post = AsyncMock(return_value=mock_response)
        
        schema = {"type": "object"}  # Simplified schema
        result = await client.generate_json_response(
            prompt="Click the submit button",
            schema=schema
        )
        
        assert result == valid_json
        assert result["action_type"] == "click"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_generate_json_response_with_markdown(self):
        """Test parsing JSON from markdown code blocks."""
        client = QwenModelClient()
        
        valid_json = {
            "action_type": "type",
            "target_selector": {"css_selector": "input#email", "xpath": "//input[@id='email']", "aria_label": None},
            "parameters": {"text": "test@example.com"},
            "expected_result": "Email entered"
        }
        
        # Response wrapped in markdown
        markdown_response = f"```json\n{json.dumps(valid_json)}\n```"
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": markdown_response}
        }
        mock_response.raise_for_status = MagicMock()
        
        client.client.post = AsyncMock(return_value=mock_response)
        
        result = await client.generate_json_response(
            prompt="Type email",
            schema={}
        )
        
        assert result == valid_json
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_generate_json_response_invalid(self):
        """Test handling of invalid JSON response."""
        client = QwenModelClient()
        
        # Mock response with invalid JSON (missing required field)
        invalid_json = {
            "parameters": {},
            "expected_result": "Something"
            # Missing action_type!
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": json.dumps(invalid_json)}
        }
        mock_response.raise_for_status = MagicMock()
        
        client.client.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(InvalidActionError) as exc_info:
            await client.generate_json_response(
                prompt="Do something",
                schema={}
            )
        
        assert "does not match schema" in str(exc_info.value)
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_generate_json_uses_default_examples(self):
        """Test that default few-shot examples are used."""
        client = QwenModelClient()
        
        valid_json = {"action_type": "navigate", "parameters": {}, "expected_result": "Navigated"}
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": json.dumps(valid_json)}
        }
        mock_response.raise_for_status = MagicMock()
        
        client.client.post = AsyncMock(return_value=mock_response)
        
        await client.generate_json_response(
            prompt="Navigate to page",
            schema={}
        )
        
        # Verify few-shot examples were included
        payload = client.client.post.call_args[1]["json"]
        messages = payload["messages"]
        
        # Should have system + FEW_SHOT_EXAMPLES (5 examples * 2 messages) + user
        assert len(messages) == 1 + (len(FEW_SHOT_EXAMPLES) * 2) + 1
        
        await client.close()


class TestJSONValidation:
    """Test JSON validation logic."""
    
    def test_validate_json_output_valid(self):
        """Test validation of valid JSON."""
        client = QwenModelClient()
        
        valid_json = {
            "action_type": "click",
            "target_selector": {
                "css_selector": "button",
                "xpath": "//button"
            },
            "parameters": {},
            "expected_result": "Clicked"
        }
        
        is_valid, parsed = client.validate_json_output(
            json.dumps(valid_json),
            {}
        )
        
        assert is_valid is True
        assert parsed == valid_json
    
    def test_validate_json_output_with_markdown(self):
        """Test extracting JSON from markdown code blocks."""
        client = QwenModelClient()
        
        valid_json = {"action_type": "navigate", "expected_result": "Done"}
        markdown = f"Here's the JSON:\n```json\n{json.dumps(valid_json)}\n```\nThat's it!"
        
        is_valid, parsed = client.validate_json_output(markdown, {})
        
        assert is_valid is True
        assert parsed == valid_json
    
    def test_validate_json_output_missing_action_type(self):
        """Test validation fails without action_type."""
        client = QwenModelClient()
        
        invalid_json = {
            "parameters": {},
            "expected_result": "Something"
        }
        
        is_valid, parsed = client.validate_json_output(
            json.dumps(invalid_json),
            {}
        )
        
        assert is_valid is False
        assert parsed is None
    
    def test_validate_json_output_invalid_action_type(self):
        """Test validation fails with invalid action_type."""
        client = QwenModelClient()
        
        invalid_json = {
            "action_type": "invalid_action",
            "expected_result": "Something"
        }
        
        is_valid, parsed = client.validate_json_output(
            json.dumps(invalid_json),
            {}
        )
        
        assert is_valid is False
        assert parsed is None
    
    def test_validate_json_output_invalid_selector_structure(self):
        """Test validation fails with invalid selector structure."""
        client = QwenModelClient()
        
        invalid_json = {
            "action_type": "click",
            "target_selector": "not a dict",  # Should be dict
            "expected_result": "Something"
        }
        
        is_valid, parsed = client.validate_json_output(
            json.dumps(invalid_json),
            {}
        )
        
        assert is_valid is False
        assert parsed is None
    
    def test_validate_json_output_malformed_json(self):
        """Test validation fails with malformed JSON."""
        client = QwenModelClient()
        
        malformed = "{this is not valid json"
        
        is_valid, parsed = client.validate_json_output(malformed, {})
        
        assert is_valid is False
        assert parsed is None
    
    def test_validate_json_output_not_dict(self):
        """Test validation fails when JSON is not a dictionary."""
        client = QwenModelClient()
        
        is_valid, parsed = client.validate_json_output(
            json.dumps(["array", "not", "dict"]),
            {}
        )
        
        assert is_valid is False
        assert parsed is None
    
    def test_validate_json_all_action_types(self):
        """Test validation accepts all valid action types."""
        client = QwenModelClient()
        
        valid_actions = ["navigate", "click", "type", "wait", "extract", "scroll", "select", "upload", "download"]
        
        for action in valid_actions:
            test_json = {
                "action_type": action,
                "expected_result": "Done"
            }
            
            is_valid, parsed = client.validate_json_output(
                json.dumps(test_json),
                {}
            )
            
            assert is_valid is True, f"Action type '{action}' should be valid"
            assert parsed["action_type"] == action


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @pytest.mark.asyncio
    async def test_create_qwen_client_no_validation(self):
        """Test creating client without validation."""
        client = await create_qwen_client(validate=False)
        
        assert client is not None
        assert client.host == "http://localhost:11434"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_create_qwen_client_with_validation(self):
        """Test creating client with validation."""
        # Mock validation
        with patch.object(QwenModelClient, 'validate_model_availability', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = True
            
            client = await create_qwen_client(validate=True)
            
            assert client is not None
            mock_validate.assert_called_once()
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_create_qwen_client_custom_params(self):
        """Test creating client with custom parameters."""
        client = await create_qwen_client(
            host="http://custom:8080",
            model="custom-model",
            timeout=60,
            validate=False
        )
        
        assert client.host == "http://custom:8080"
        assert client.model == "custom-model"
        assert client.timeout == 60
        
        await client.close()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_extract_json_from_plain_text(self):
        """Test extracting JSON from plain text."""
        client = QwenModelClient()
        
        json_str = '{"action_type": "click"}'
        extracted = client._extract_json_from_text(json_str)
        
        assert extracted == json_str
    
    def test_extract_json_with_surrounding_text(self):
        """Test extracting JSON with surrounding text."""
        client = QwenModelClient()
        
        text = "Here is the action: {\"action_type\": \"click\"} and that's it"
        extracted = client._extract_json_from_text(text)
        
        assert extracted == '{"action_type": "click"}'
    
    def test_extract_json_with_generic_code_block(self):
        """Test extracting JSON from generic code block."""
        client = QwenModelClient()
        
        text = "```\n{\"action_type\": \"click\"}\n```"
        extracted = client._extract_json_from_text(text)
        
        assert extracted == '{"action_type": "click"}'
    
    def test_validate_selector_with_no_selectors(self):
        """Test validation fails when selector has no selector fields."""
        client = QwenModelClient()
        
        invalid_json = {
            "action_type": "click",
            "target_selector": {
                "some_other_field": "value"
                # No css_selector, xpath, or aria_label
            },
            "expected_result": "Something"
        }
        
        is_valid, _ = client.validate_json_output(json.dumps(invalid_json), {})
        
        assert is_valid is False
    
    def test_validate_parameters_not_dict(self):
        """Test validation fails when parameters is not a dict."""
        client = QwenModelClient()
        
        invalid_json = {
            "action_type": "type",
            "parameters": "not a dict",
            "expected_result": "Something"
        }
        
        is_valid, _ = client.validate_json_output(json.dumps(invalid_json), {})
        
        assert is_valid is False
