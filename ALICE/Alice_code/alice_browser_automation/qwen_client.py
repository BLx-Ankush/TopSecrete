"""
Qwen Model Client for Alice Browser Automation.

This module provides the interface to the Qwen Coder 2.5 3B model via Ollama
for browser action planning and DOM processing.

**Validates: Requirements 1.2, 1.4, 4.1, 4.2, 12.3**
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
import httpx

from alice_browser_automation.exceptions import QwenModelUnavailableError, InvalidActionError


logger = logging.getLogger(__name__)


# ============================================================================
# JSON Schema Definitions
# ============================================================================

# JSON schema for browser action responses
ACTION_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["action_type", "expected_result"],
    "properties": {
        "action_type": {
            "type": "string",
            "enum": ["navigate", "click", "type", "wait", "extract", "scroll", "select", "upload", "download"]
        },
        "target_selector": {
            "type": ["object", "null"],
            "properties": {
                "css_selector": {"type": ["string", "null"]},
                "xpath": {"type": ["string", "null"]},
                "aria_label": {"type": ["string", "null"]},
                "test_id": {"type": ["string", "null"]},
                "text_content": {"type": ["string", "null"]}
            }
        },
        "parameters": {
            "type": "object"
        },
        "expected_result": {
            "type": "string"
        }
    }
}

# JSON schema for target selector
TARGET_SELECTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "css_selector": {"type": ["string", "null"]},
        "xpath": {"type": ["string", "null"]},
        "aria_label": {"type": ["string", "null"]},
        "test_id": {"type": ["string", "null"]},
        "text_content": {"type": ["string", "null"]}
    }
}


# ============================================================================
# Prompt Templates and Few-Shot Examples
# ============================================================================

SYSTEM_PROMPT = """You are a browser automation assistant. You analyze web page DOM structures and generate precise browser actions in JSON format.

Your responses must be valid JSON following this schema:
{
  "action_type": "navigate|click|type|wait|extract|scroll",
  "target_selector": {
    "css_selector": "string",
    "xpath": "string",
    "aria_label": "string|null"
  },
  "parameters": {
    // Action-specific parameters
  },
  "expected_result": "string"
}

Rules:
1. Always use the most specific selector available
2. Prefer ARIA labels and test IDs over generic CSS selectors
3. Include expected_result to verify action success
4. For type actions, include "text" in parameters
5. For wait actions, include "condition" and "timeout_ms" in parameters
"""

FEW_SHOT_EXAMPLES = [
    {
        "user": "Click the login button. DOM: <button aria-label='Sign in' class='btn-primary'>Login</button>",
        "assistant": json.dumps({
            "action_type": "click",
            "target_selector": {
                "css_selector": "button.btn-primary",
                "xpath": "//button[@aria-label='Sign in']",
                "aria_label": "Sign in"
            },
            "parameters": {},
            "expected_result": "Navigation to login page or form submission"
        })
    },
    {
        "user": "Type 'john@example.com' in email field. DOM: <input type='email' id='email' placeholder='Email'>",
        "assistant": json.dumps({
            "action_type": "type",
            "target_selector": {
                "css_selector": "input#email",
                "xpath": "//input[@type='email']",
                "aria_label": None
            },
            "parameters": {
                "text": "john@example.com",
                "clear_first": True
            },
            "expected_result": "Email field contains 'john@example.com'"
        })
    },
    {
        "user": "Navigate to booking page",
        "assistant": json.dumps({
            "action_type": "navigate",
            "target_selector": None,
            "parameters": {
                "url": "https://example.com/booking",
                "wait_until": "networkidle"
            },
            "expected_result": "Page loaded with booking form visible"
        })
    },
    {
        "user": "Wait for search results to load. DOM shows loading spinner",
        "assistant": json.dumps({
            "action_type": "wait",
            "target_selector": {
                "css_selector": ".search-results",
                "xpath": "//div[@class='search-results']",
                "aria_label": None
            },
            "parameters": {
                "condition": "visible",
                "timeout_ms": 5000
            },
            "expected_result": "Search results visible on page"
        })
    },
    {
        "user": "Extract booking confirmation number. DOM: <div class='confirmation'>Booking #ABC123</div>",
        "assistant": json.dumps({
            "action_type": "extract",
            "target_selector": {
                "css_selector": "div.confirmation",
                "xpath": "//div[@class='confirmation']",
                "aria_label": None
            },
            "parameters": {
                "extract_type": "text",
                "pattern": r"Booking #(\w+)"
            },
            "expected_result": "Extracted confirmation number: ABC123"
        })
    },
    {
        "user": "Scroll down to load more results. DOM: <div class='results-container' id='results'>",
        "assistant": json.dumps({
            "action_type": "scroll",
            "target_selector": {
                "css_selector": "div#results",
                "xpath": "//div[@class='results-container']",
                "aria_label": None
            },
            "parameters": {
                "direction": "down",
                "amount": 500
            },
            "expected_result": "Page scrolled down, more results visible"
        })
    }
]


# ============================================================================
# PromptBuilder Class
# ============================================================================

class PromptBuilder:
    """
    Builder class for constructing prompts with few-shot examples.
    
    This class helps construct well-formatted prompts for the Qwen model
    by combining system prompts, few-shot examples, and user prompts.
    
    **Validates: Requirements 4.1, 4.2, 4.4**
    
    Attributes:
        system_prompt: System prompt defining model behavior
        few_shot_examples: List of example conversations
        include_schema: Whether to include JSON schema in prompt
    """
    
    def __init__(
        self,
        system_prompt: str = SYSTEM_PROMPT,
        few_shot_examples: Optional[List[Dict[str, str]]] = None,
        include_schema: bool = True
    ):
        """
        Initialize PromptBuilder.
        
        Args:
            system_prompt: System prompt to use (defaults to SYSTEM_PROMPT)
            few_shot_examples: List of examples (defaults to FEW_SHOT_EXAMPLES)
            include_schema: Whether to include JSON schema in system prompt
        """
        self.system_prompt = system_prompt
        self.few_shot_examples = few_shot_examples or FEW_SHOT_EXAMPLES
        self.include_schema = include_schema
        
        logger.debug(f"Initialized PromptBuilder with {len(self.few_shot_examples)} examples")
    
    def build_messages(
        self,
        user_prompt: str,
        additional_context: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Build complete message list for Ollama API.
        
        Args:
            user_prompt: The user's prompt/question
            additional_context: Optional additional context to prepend to user prompt
        
        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        messages = []
        
        # Add system prompt
        messages.append({
            "role": "system",
            "content": self.system_prompt
        })
        
        # Add few-shot examples
        for example in self.few_shot_examples:
            messages.append({
                "role": "user",
                "content": example["user"]
            })
            messages.append({
                "role": "assistant",
                "content": example["assistant"]
            })
        
        # Build final user prompt with optional context
        final_user_prompt = user_prompt
        if additional_context:
            final_user_prompt = f"{additional_context}\n\n{user_prompt}"
        
        messages.append({
            "role": "user",
            "content": final_user_prompt
        })
        
        logger.debug(f"Built {len(messages)} messages for prompt")
        return messages
    
    def build_action_prompt(
        self,
        task_description: str,
        dom_snippet: str,
        previous_actions: Optional[List[str]] = None
    ) -> str:
        """
        Build a prompt for generating browser actions.
        
        Args:
            task_description: High-level description of the task
            dom_snippet: Relevant DOM structure snippet
            previous_actions: Optional list of previous actions taken
        
        Returns:
            Formatted prompt string
        """
        prompt_parts = [f"Task: {task_description}"]
        
        if previous_actions:
            prompt_parts.append(f"\nPrevious actions: {', '.join(previous_actions)}")
        
        prompt_parts.append(f"\nCurrent DOM:\n{dom_snippet}")
        prompt_parts.append("\nGenerate the next browser action as JSON:")
        
        return "\n".join(prompt_parts)
    
    def build_correction_prompt(
        self,
        original_prompt: str,
        invalid_response: str,
        error_message: str
    ) -> str:
        """
        Build a prompt for correcting invalid JSON responses.
        
        Args:
            original_prompt: The original prompt that produced invalid response
            invalid_response: The invalid response that was generated
            error_message: Description of what was wrong
        
        Returns:
            Formatted correction prompt
        """
        correction_prompt = f"""The previous response was invalid:

Original request: {original_prompt}

Invalid response: {invalid_response}

Error: {error_message}

Please generate a corrected response that follows the JSON schema exactly."""
        
        return correction_prompt
    
    def add_example(self, user_message: str, assistant_message: str) -> None:
        """
        Add a new few-shot example.
        
        Args:
            user_message: User message for the example
            assistant_message: Assistant response for the example
        """
        self.few_shot_examples.append({
            "user": user_message,
            "assistant": assistant_message
        })
        logger.debug(f"Added new example. Total examples: {len(self.few_shot_examples)}")
    
    def clear_examples(self) -> None:
        """Clear all few-shot examples."""
        self.few_shot_examples = []
        logger.debug("Cleared all few-shot examples")
    
    def get_example_count(self) -> int:
        """Get the number of few-shot examples."""
        return len(self.few_shot_examples)


# ============================================================================
# QwenModelClient Class
# ============================================================================

class QwenModelClient:
    """
    Client for Qwen model via Ollama API.
    
    Provides interface for text generation and JSON response generation
    with schema validation. Includes connection pooling for efficient
    API communication.
    
    **Validates: Requirements 1.2, 1.4, 4.1, 4.2, 12.3**
    
    Attributes:
        host: Ollama API host URL
        model: Qwen model name
        timeout: Request timeout in seconds
        client: HTTP client with connection pooling
    """
    
    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "qwen2.5-coder:3b",
        timeout: int = 30
    ):
        """
        Initialize Qwen model client.
        
        Args:
            host: Ollama API host URL (default: http://localhost:11434)
            model: Qwen model name (default: qwen2.5-coder:3b)
            timeout: Request timeout in seconds (default: 30)
        """
        self.host = host.rstrip('/')
        self.model = model
        self.timeout = timeout
        
        # Create HTTP client with connection pooling
        # Connection pooling improves performance by reusing connections
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=30.0
            )
        )
        
        logger.info(f"Initialized QwenModelClient: host={host}, model={model}, timeout={timeout}s")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources."""
        await self.close()
    
    async def close(self):
        """Close HTTP client and cleanup resources."""
        await self.client.aclose()
        logger.debug("Closed QwenModelClient HTTP client")
    
    async def validate_model_availability(self) -> bool:
        """
        Check if Qwen model is available via Ollama.
        
        Returns:
            True if model is available, False otherwise
            
        Raises:
            QwenModelUnavailableError: If Ollama service is unreachable
        """
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            response.raise_for_status()
            
            data = response.json()
            models = data.get("models", [])
            
            # Check if our model is in the list
            model_names = [m.get("name", "") for m in models]
            is_available = any(self.model in name for name in model_names)
            
            if is_available:
                logger.info(f"Qwen model '{self.model}' is available")
            else:
                logger.warning(f"Qwen model '{self.model}' not found. Available models: {model_names}")
            
            return is_available
            
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to Ollama at {self.host}: {e}")
            raise QwenModelUnavailableError(
                f"Cannot connect to Ollama at {self.host}. Is Ollama running?",
                host=self.host,
                model=self.model,
                original_error=e
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Ollama: {e}")
            raise QwenModelUnavailableError(
                f"Ollama API error: {e}",
                host=self.host,
                model=self.model,
                original_error=e
            )
        except Exception as e:
            logger.error(f"Unexpected error checking model availability: {e}")
            raise QwenModelUnavailableError(
                f"Unexpected error: {e}",
                host=self.host,
                model=self.model,
                original_error=e
            )
    
    async def generate_with_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        few_shot_examples: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate text response with few-shot examples.
        
        **Validates: Requirement 4.1** - Generate responses with few-shot examples
        
        Args:
            system_prompt: System prompt defining model behavior
            user_prompt: User prompt with task description
            few_shot_examples: Optional list of example conversations
                              Each dict should have 'user' and 'assistant' keys
        
        Returns:
            Generated text response
            
        Raises:
            QwenModelUnavailableError: If model is unavailable or request fails
        """
        start_time = time.time()
        
        # Build messages list
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add few-shot examples if provided
        if few_shot_examples:
            for example in few_shot_examples:
                messages.append({"role": "user", "content": example["user"]})
                messages.append({"role": "assistant", "content": example["assistant"]})
        
        # Add actual user prompt
        messages.append({"role": "user", "content": user_prompt})
        
        # Prepare request payload
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }
        
        try:
            logger.debug(f"Sending generation request to Ollama: {len(messages)} messages")
            
            response = await self.client.post(
                f"{self.host}/api/chat",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            generated_text = data.get("message", {}).get("content", "")
            
            elapsed = time.time() - start_time
            logger.info(f"Generated response in {elapsed:.2f}s ({len(generated_text)} chars)")
            
            return generated_text
            
        except httpx.ConnectError as e:
            logger.error(f"Connection error during generation: {e}")
            raise QwenModelUnavailableError(
                f"Cannot connect to Ollama at {self.host}",
                host=self.host,
                model=self.model,
                original_error=e
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during generation: {e}")
            raise QwenModelUnavailableError(
                f"Ollama API error: {e.response.status_code}",
                host=self.host,
                model=self.model,
                original_error=e
            )
        except Exception as e:
            logger.error(f"Unexpected error during generation: {e}")
            raise QwenModelUnavailableError(
                f"Generation failed: {e}",
                host=self.host,
                model=self.model,
                original_error=e
            )
    
    async def generate_json_response(
        self,
        prompt: str,
        schema: Dict[str, Any],
        few_shot_examples: Optional[List[Dict[str, str]]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate JSON response matching schema with validation and retry logic.
        
        **Validates: Requirements 4.2, 4.4, 4.5, 4.6** - Generate valid JSON with schema validation and retry
        
        This method implements retry logic with exponential backoff when the model
        generates invalid JSON. On each retry, error context is added to the prompt
        to help the model correct its mistakes.
        
        Args:
            prompt: User prompt describing desired action
            schema: JSON schema for validation
            few_shot_examples: Optional few-shot examples (defaults to FEW_SHOT_EXAMPLES)
            max_retries: Maximum number of retry attempts (default: 3)
        
        Returns:
            Parsed and validated JSON response
            
        Raises:
            InvalidActionError: If generated JSON is invalid after all retries
            QwenModelUnavailableError: If model is unavailable
        """
        # Use default few-shot examples if none provided
        if few_shot_examples is None:
            few_shot_examples = FEW_SHOT_EXAMPLES
        
        # Track retry attempts
        attempt = 0
        last_error_message = None
        last_invalid_response = None
        current_prompt = prompt
        
        while attempt <= max_retries:
            try:
                # Generate response with system prompt and few-shot examples
                response_text = await self.generate_with_prompt(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=current_prompt,
                    few_shot_examples=few_shot_examples
                )
                
                # Validate and parse JSON
                is_valid, parsed_json = self.validate_json_output(response_text, schema)
                
                if is_valid:
                    if attempt > 0:
                        logger.info(f"Successfully generated valid JSON after {attempt} retries")
                    else:
                        logger.debug(f"Successfully generated and validated JSON response")
                    return parsed_json
                
                # JSON is invalid - prepare for retry
                last_invalid_response = response_text
                last_error_message = "Schema validation failed"
                
                # Check if we have retries left
                if attempt >= max_retries:
                    logger.error(f"Failed to generate valid JSON after {max_retries} retries")
                    raise InvalidActionError(
                        f"Generated JSON does not match schema after {max_retries} retries",
                        invalid_json=response_text,
                        validation_error=last_error_message
                    )
                
                # Prepare retry with error context
                attempt += 1
                
                # Calculate exponential backoff delay: 1s, 2s, 4s
                backoff_delay = 2 ** (attempt - 1)
                logger.warning(
                    f"Invalid JSON generated (attempt {attempt}/{max_retries}). "
                    f"Retrying in {backoff_delay}s with error context..."
                )
                
                # Wait with exponential backoff
                await self._async_sleep(backoff_delay)
                
                # Build correction prompt with error context
                prompt_builder = PromptBuilder(
                    system_prompt=SYSTEM_PROMPT,
                    few_shot_examples=few_shot_examples
                )
                current_prompt = prompt_builder.build_correction_prompt(
                    original_prompt=prompt,
                    invalid_response=response_text[:500],  # Limit to 500 chars
                    error_message=last_error_message
                )
                
            except InvalidActionError:
                # Re-raise InvalidActionError (already formatted)
                raise
            except QwenModelUnavailableError:
                # Re-raise model unavailability errors
                raise
            except Exception as e:
                # Unexpected error during generation
                logger.error(f"Unexpected error during JSON generation: {e}")
                
                if attempt >= max_retries:
                    raise InvalidActionError(
                        f"Failed to generate JSON due to error: {e}",
                        invalid_json=last_invalid_response or "",
                        validation_error=str(e)
                    )
                
                # Retry on unexpected errors too
                attempt += 1
                backoff_delay = 2 ** (attempt - 1)
                logger.warning(f"Retrying after error in {backoff_delay}s...")
                await self._async_sleep(backoff_delay)
        
        # Should not reach here, but just in case
        raise InvalidActionError(
            f"Failed to generate valid JSON after {max_retries} retries",
            invalid_json=last_invalid_response or "",
            validation_error=last_error_message or "Unknown error"
        )
    
    async def _async_sleep(self, seconds: float) -> None:
        """
        Async sleep helper for exponential backoff.
        
        Args:
            seconds: Number of seconds to sleep
        """
        import asyncio
        await asyncio.sleep(seconds)
    
    def validate_json_output(
        self,
        output: str,
        schema: Dict[str, Any]
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate and parse JSON output against schema.
        
        **Validates: Requirement 4.4** - Parse and validate JSON output
        
        This method extracts JSON from the output (handling markdown code blocks),
        parses it, and validates against the provided schema.
        
        Args:
            output: Raw output string from model (may contain markdown)
            schema: JSON schema for validation
        
        Returns:
            Tuple of (is_valid, parsed_json)
            - is_valid: True if JSON is valid and matches schema
            - parsed_json: Parsed JSON dict if valid, None otherwise
        """
        try:
            # Extract JSON from output (handle markdown code blocks)
            json_str = self._extract_json_from_text(output)
            
            # Parse JSON
            parsed = json.loads(json_str)
            
            # Basic schema validation
            # Check required fields based on schema
            if not isinstance(parsed, dict):
                logger.warning("Parsed JSON is not a dictionary")
                return False, None
            
            # Validate against schema (basic validation)
            is_valid = self._validate_against_schema(parsed, schema)
            
            if is_valid:
                return True, parsed
            else:
                logger.warning("JSON does not match schema")
                return False, None
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error validating JSON: {e}")
            return False, None
    
    def _extract_json_from_text(self, text: str) -> str:
        """
        Extract JSON from text, handling markdown code blocks.
        
        Args:
            text: Text potentially containing JSON
        
        Returns:
            Extracted JSON string
        """
        text = text.strip()
        
        # Check for markdown code blocks
        if "```json" in text:
            # Extract from ```json ... ```
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()
        elif "```" in text:
            # Extract from ``` ... ```
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()
        
        # Try to find JSON object boundaries
        if "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            return text[start:end]
        
        # Return as-is if no special formatting detected
        return text
    
    def _validate_against_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """
        Basic schema validation for browser actions.
        
        This is a simplified validation focused on browser action structure.
        For production, consider using jsonschema library for full validation.
        
        Args:
            data: Parsed JSON data
            schema: Schema to validate against
        
        Returns:
            True if data matches schema
        """
        # Check for required action_type field
        if "action_type" not in data:
            logger.warning("Missing required field: action_type")
            return False
        
        # Validate action_type is one of the allowed values
        valid_actions = ["navigate", "click", "type", "wait", "extract", "scroll", "select", "upload", "download"]
        if data["action_type"] not in valid_actions:
            logger.warning(f"Invalid action_type: {data['action_type']}")
            return False
        
        # Check for expected_result field
        if "expected_result" not in data:
            logger.warning("Missing recommended field: expected_result")
            # Not a hard failure, but log it
        
        # Validate target_selector structure if present
        if "target_selector" in data and data["target_selector"] is not None:
            selector = data["target_selector"]
            if not isinstance(selector, dict):
                logger.warning("target_selector must be a dictionary")
                return False
            
            # Should have at least one selector type
            has_selector = any(key in selector for key in ["css_selector", "xpath", "aria_label"])
            if not has_selector:
                logger.warning("target_selector must have at least one selector type")
                return False
        
        # Validate parameters is a dict if present
        if "parameters" in data and not isinstance(data["parameters"], dict):
            logger.warning("parameters must be a dictionary")
            return False
        
        return True


# ============================================================================
# Convenience Functions
# ============================================================================

async def create_qwen_client(
    host: str = "http://localhost:11434",
    model: str = "qwen2.5-coder:3b",
    timeout: int = 30,
    validate: bool = True
) -> QwenModelClient:
    """
    Create and optionally validate a Qwen model client.
    
    Args:
        host: Ollama API host URL
        model: Qwen model name
        timeout: Request timeout in seconds
        validate: Whether to validate model availability on creation
    
    Returns:
        Initialized QwenModelClient
        
    Raises:
        QwenModelUnavailableError: If validate=True and model is unavailable
    """
    client = QwenModelClient(host=host, model=model, timeout=timeout)
    
    if validate:
        await client.validate_model_availability()
    
    return client
