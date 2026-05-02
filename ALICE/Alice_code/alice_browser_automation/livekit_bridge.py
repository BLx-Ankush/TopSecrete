"""
LiveKit-Qwen Bridge for Alice Browser Automation.

This module provides the bridge between Alice's LiveKit voice agent and the
local Qwen model for browser automation. It translates voice commands into
browser tasks and validates model availability.

**Validates: Requirements 3.1, 3.2, 3.6**
"""

import logging
import json
from typing import Dict, Any, Optional, List
import uuid

from alice_browser_automation.qwen_client import QwenModelClient, create_qwen_client
from alice_browser_automation.types import BrowserTask, TaskType
from alice_browser_automation.exceptions import QwenModelUnavailableError


logger = logging.getLogger(__name__)


# ============================================================================
# Voice Command Translation Prompts
# ============================================================================

VOICE_COMMAND_TRANSLATION_PROMPT = """You are a voice command interpreter for browser automation. 
Convert natural language voice commands into structured browser tasks.

Your response must be valid JSON following this schema:
{
  "task_type": "web_booking|problem_solving|app_access",
  "description": "Clear description of the task",
  "target_url": "URL to navigate to (optional)",
  "parameters": {
    // Task-specific parameters
  },
  "expected_outcome": "What should happen when task completes"
}

Task Types:
- web_booking: Travel bookings, food delivery, event tickets
- problem_solving: Research and solve desktop/technical problems
- app_access: Access and navigate web applications

Examples:
- "Book a flight to Paris" -> web_booking with destination parameter
- "Find solution for Python import error" -> problem_solving with error description
- "Check my Gmail inbox" -> app_access with app=gmail, action=check_inbox
"""

VOICE_COMMAND_EXAMPLES = [
    {
        "user": "Book a flight to Paris on December 25th for 2 passengers",
        "assistant": json.dumps({
            "task_type": "web_booking",
            "description": "Book flight to Paris",
            "target_url": None,
            "parameters": {
                "booking_type": "flight",
                "destination": "Paris",
                "departure_date": "2025-12-25",
                "passengers": 2
            },
            "expected_outcome": "Flight booking confirmed with confirmation number"
        })
    },
    {
        "user": "Order pizza from Dominos with extra cheese",
        "assistant": json.dumps({
            "task_type": "web_booking",
            "description": "Order pizza from Dominos",
            "target_url": None,
            "parameters": {
                "booking_type": "food",
                "restaurant": "Dominos",
                "items": ["pizza with extra cheese"]
            },
            "expected_outcome": "Food order placed with delivery confirmation"
        })
    },
    {
        "user": "Find a solution for ModuleNotFoundError in Python",
        "assistant": json.dumps({
            "task_type": "problem_solving",
            "description": "Find solution for Python ModuleNotFoundError",
            "target_url": None,
            "parameters": {
                "problem_type": "error",
                "error_message": "ModuleNotFoundError",
                "language": "Python"
            },
            "expected_outcome": "Solution found and presented to user"
        })
    },
    {
        "user": "Check my Gmail inbox for unread messages",
        "assistant": json.dumps({
            "task_type": "app_access",
            "description": "Check Gmail inbox",
            "target_url": "https://mail.google.com",
            "parameters": {
                "app_name": "gmail",
                "action": "check_inbox",
                "filter": "unread"
            },
            "expected_outcome": "Unread messages retrieved and reported"
        })
    },
    {
        "user": "Book tickets for the concert next Friday",
        "assistant": json.dumps({
            "task_type": "web_booking",
            "description": "Book concert tickets",
            "target_url": None,
            "parameters": {
                "booking_type": "event",
                "event_type": "concert",
                "date": "next Friday",
                "ticket_count": 1
            },
            "expected_outcome": "Concert tickets booked with confirmation"
        })
    }
]


# ============================================================================
# LiveKitQwenBridge Class
# ============================================================================

class LiveKitQwenBridge:
    """
    Bridge between LiveKit voice agent and Qwen model.
    
    This class establishes the connection between Alice's LiveKit agent and
    the local Qwen model, translating voice commands into browser tasks and
    validating model availability.
    
    **Validates: Requirements 3.1, 3.2, 3.6**
    
    Attributes:
        ollama_host: Ollama API host URL
        model_name: Qwen model name
        qwen_client: QwenModelClient instance for model interaction
        timeout: Request timeout in seconds
    """
    
    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model_name: str = "qwen2.5-coder:3b",
        timeout: int = 30
    ):
        """
        Initialize LiveKit-Qwen Bridge.
        
        **Validates: Requirement 3.1** - Establish connection between Alice's 
        LiveKit agent and local Qwen model
        
        Args:
            ollama_host: Ollama API host URL (default: http://localhost:11434)
            model_name: Qwen model name (default: qwen2.5-coder:3b)
            timeout: Request timeout in seconds (default: 30)
        """
        self.ollama_host = ollama_host
        self.model_name = model_name
        self.timeout = timeout
        
        # Initialize Qwen client for model interaction
        self.qwen_client = QwenModelClient(
            host=ollama_host,
            model=model_name,
            timeout=timeout
        )
        
        logger.info(
            f"Initialized LiveKitQwenBridge: host={ollama_host}, "
            f"model={model_name}, timeout={timeout}s"
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources."""
        await self.close()
    
    async def close(self):
        """Close Qwen client and cleanup resources."""
        await self.qwen_client.close()
        logger.debug("Closed LiveKitQwenBridge")
    
    def validate_model_availability(self) -> bool:
        """
        Check if Qwen model is available via Ollama.
        
        **Validates: Requirement 3.6** - If Qwen model is unavailable, return 
        error message to Alice
        
        This is a synchronous wrapper around the async validation method.
        For async contexts, use the qwen_client.validate_model_availability() directly.
        
        Returns:
            True if model is available, False otherwise
            
        Raises:
            QwenModelUnavailableError: If Ollama service is unreachable or 
                                       model is not installed
        """
        import asyncio
        
        try:
            # Run async validation in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a task
                logger.warning(
                    "validate_model_availability called from async context. "
                    "Consider using await qwen_client.validate_model_availability() instead."
                )
                # Can't use asyncio.run() in running loop, so we'll use the client directly
                # This is a limitation - in production, this should be called properly
                raise RuntimeError(
                    "Cannot call synchronous validate_model_availability from async context. "
                    "Use: await bridge.qwen_client.validate_model_availability()"
                )
            else:
                # Not in async context, safe to use asyncio.run()
                return asyncio.run(self.qwen_client.validate_model_availability())
        except QwenModelUnavailableError:
            # Re-raise model unavailability errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error validating model availability: {e}")
            raise QwenModelUnavailableError(
                f"Failed to validate model availability: {e}",
                host=self.ollama_host,
                model=self.model_name,
                original_error=e
            )
    
    async def translate_voice_command(
        self,
        voice_command: str,
        context: Optional[Dict[str, Any]] = None
    ) -> BrowserTask:
        """
        Translate voice command to BrowserTask.
        
        **Validates: Requirement 3.2** - Implement function calling interface 
        for browser automation capabilities
        
        **Validates: Requirement 3.3** - Translate voice command to Qwen model API call
        
        This method takes a natural language voice command from Alice and
        converts it into a structured BrowserTask that can be executed by
        the Browser Automation Engine.
        
        Args:
            voice_command: Natural language voice command from user
            context: Optional context information (user preferences, history, etc.)
        
        Returns:
            BrowserTask with structured task information
            
        Raises:
            QwenModelUnavailableError: If model is unavailable
            ValueError: If voice command cannot be translated
        """
        logger.info(f"Translating voice command: {voice_command}")
        
        # Build prompt with context if provided
        prompt = voice_command
        if context:
            context_str = json.dumps(context, indent=2)
            prompt = f"Context: {context_str}\n\nVoice command: {voice_command}"
        
        try:
            # Generate structured task using Qwen model
            task_json = await self.qwen_client.generate_json_response(
                prompt=prompt,
                schema={
                    "type": "object",
                    "required": ["task_type", "description"],
                    "properties": {
                        "task_type": {
                            "type": "string",
                            "enum": ["web_booking", "problem_solving", "app_access"]
                        },
                        "description": {"type": "string"},
                        "target_url": {"type": ["string", "null"]},
                        "parameters": {"type": "object"},
                        "expected_outcome": {"type": "string"}
                    }
                },
                few_shot_examples=VOICE_COMMAND_EXAMPLES,
                max_retries=3
            )
            
            # Convert task_type string to TaskType enum
            task_type_str = task_json.get("task_type", "").upper()
            try:
                task_type = TaskType[task_type_str]
            except KeyError:
                logger.error(f"Invalid task_type: {task_type_str}")
                raise ValueError(f"Invalid task type: {task_json.get('task_type')}")
            
            # Generate unique task ID
            task_id = str(uuid.uuid4())
            
            # Create BrowserTask
            browser_task = BrowserTask(
                task_id=task_id,
                description=task_json.get("description", voice_command),
                task_type=task_type,
                parameters=task_json.get("parameters", {}),
                target_url=task_json.get("target_url"),
                expected_outcome=task_json.get("expected_outcome", "Task completed successfully")
            )
            
            logger.info(
                f"Translated voice command to BrowserTask: "
                f"type={task_type.value}, id={task_id}"
            )
            
            # Set task context for multi-step task tracking
            self._set_task_context(browser_task)
            
            return browser_task
            
        except QwenModelUnavailableError:
            # Re-raise model unavailability errors
            logger.error("Qwen model unavailable during voice command translation")
            raise
        except Exception as e:
            logger.error(f"Failed to translate voice command: {e}")
            raise ValueError(f"Could not translate voice command: {e}")
    
    async def validate_and_translate(
        self,
        voice_command: str,
        context: Optional[Dict[str, Any]] = None
    ) -> BrowserTask:
        """
        Validate model availability and translate voice command.
        
        This is a convenience method that combines model validation and
        voice command translation in a single call.
        
        Args:
            voice_command: Natural language voice command from user
            context: Optional context information
        
        Returns:
            BrowserTask with structured task information
            
        Raises:
            QwenModelUnavailableError: If model is unavailable
            ValueError: If voice command cannot be translated
        """
        # First validate model is available
        is_available = await self.qwen_client.validate_model_availability()
        
        if not is_available:
            raise QwenModelUnavailableError(
                f"Qwen model '{self.model_name}' is not available",
                host=self.ollama_host,
                model=self.model_name
            )
        
        # Then translate the command
        return await self.translate_voice_command(voice_command, context)
    
    async def generate_action_plan(
        self,
        task: BrowserTask,
        dom: 'StructuredDOM'
    ) -> List['BrowserAction']:
        """
        Generate action plan from task and DOM.
        
        **Validates: Requirement 3.3** - Translate voice command to Qwen model API call
        **Validates: Requirement 3.4** - Pass DOM structured text to Qwen model
        **Validates: Requirement 4.6** - Generate action plan within 5 seconds
        
        This method takes a high-level BrowserTask and the current DOM structure,
        then generates a sequence of BrowserActions to accomplish the task.
        
        Args:
            task: BrowserTask with task description and parameters
            dom: StructuredDOM with current page structure
        
        Returns:
            List of BrowserAction objects representing the action sequence
            
        Raises:
            QwenModelUnavailableError: If model is unavailable
            ValueError: If action plan cannot be generated
        """
        from alice_browser_automation.qwen_client import PromptBuilder
        from alice_browser_automation.types import BrowserAction, ActionType, ElementSelectors
        
        logger.info(f"Generating action plan for task: {task.task_id}")
        
        # Build DOM snippet for prompt (limit to interactive elements)
        interactive_elements = dom.interactive_elements[:20]  # Limit to first 20 elements
        dom_snippet = self._format_dom_for_prompt(interactive_elements)
        
        # Build prompt for action plan generation
        prompt_builder = PromptBuilder()
        prompt = f"""Task: {task.description}
Task Type: {task.task_type.value}
Parameters: {json.dumps(task.parameters)}
Expected Outcome: {task.expected_outcome}

Current Page: {dom.url}
Page Title: {dom.title}

Interactive Elements:
{dom_snippet}

Generate a sequence of browser actions to accomplish this task. For each action, provide:
1. action_type (navigate, click, type, wait, extract, scroll)
2. target_selector (if applicable)
3. parameters (action-specific)
4. expected_result

Respond with a JSON array of actions."""
        
        try:
            # Generate action plan using Qwen model
            # Note: We'll generate one action at a time for better control
            # For now, generate the first action to start the plan
            action_json = await self.qwen_client.generate_json_response(
                prompt=prompt,
                schema={
                    "type": "object",
                    "required": ["action_type", "expected_result"],
                    "properties": {
                        "action_type": {"type": "string"},
                        "target_selector": {"type": ["object", "null"]},
                        "parameters": {"type": "object"},
                        "expected_result": {"type": "string"}
                    }
                },
                max_retries=3
            )
            
            # Convert JSON to BrowserAction
            action = self._json_to_browser_action(action_json)
            
            logger.info(
                f"Generated initial action plan with {1} action(s) for task {task.task_id}"
            )
            
            # Return list with first action
            # In practice, we'll use get_next_action() to generate subsequent actions
            return [action]
            
        except Exception as e:
            logger.error(f"Failed to generate action plan: {e}")
            raise ValueError(f"Could not generate action plan: {e}")
    
    async def get_next_action(
        self,
        current_state: 'BrowserState',
        dom: 'StructuredDOM',
        previous_actions: List['BrowserAction']
    ) -> Optional['BrowserAction']:
        """
        Get next action based on current state.
        
        **Validates: Requirement 3.3** - Translate voice command to Qwen model API call
        **Validates: Requirement 3.4** - Pass DOM structured text to Qwen model
        **Validates: Requirement 12.3** - Generate action within 5 seconds
        
        This method determines the next action to take based on:
        - Current browser state (URL, DOM)
        - Previous actions taken
        - Task context from multi-step task tracking
        
        Args:
            current_state: BrowserState with current browser state
            dom: StructuredDOM with current page structure
            previous_actions: List of BrowserAction objects already executed
        
        Returns:
            BrowserAction for next step, or None if task is complete
            
        Raises:
            QwenModelUnavailableError: If model is unavailable
            ValueError: If next action cannot be determined
        """
        from alice_browser_automation.qwen_client import PromptBuilder
        from alice_browser_automation.types import BrowserAction, ActionType, ElementSelectors
        
        logger.info(f"Determining next action based on current state: {current_state.url}")
        
        # Check if we have task context
        task_context = self._get_task_context()
        if not task_context:
            logger.warning("No task context available for get_next_action")
            return None
        
        # Build DOM snippet for prompt
        interactive_elements = dom.interactive_elements[:20]  # Limit to first 20 elements
        dom_snippet = self._format_dom_for_prompt(interactive_elements)
        
        # Build previous actions summary
        actions_summary = self._format_previous_actions(previous_actions)
        
        # Build prompt for next action
        prompt_builder = PromptBuilder()
        prompt = f"""Task: {task_context.get('description', 'Unknown task')}
Task Type: {task_context.get('task_type', 'unknown')}
Expected Outcome: {task_context.get('expected_outcome', 'Complete the task')}

Current Page: {current_state.url}
Page Title: {dom.title}

Previous Actions Taken:
{actions_summary}

Current Interactive Elements:
{dom_snippet}

Based on the task and previous actions, what is the next action to take?
If the task is complete, respond with action_type "extract" to extract final results.
If no more actions are needed, respond with action_type "wait" with parameters {{"condition": "complete", "timeout_ms": 0}}.

Generate the next browser action as JSON."""
        
        try:
            # Generate next action using Qwen model
            action_json = await self.qwen_client.generate_json_response(
                prompt=prompt,
                schema={
                    "type": "object",
                    "required": ["action_type", "expected_result"],
                    "properties": {
                        "action_type": {"type": "string"},
                        "target_selector": {"type": ["object", "null"]},
                        "parameters": {"type": "object"},
                        "expected_result": {"type": "string"}
                    }
                },
                max_retries=3
            )
            
            # Convert JSON to BrowserAction
            action = self._json_to_browser_action(action_json)
            
            # Check if task is complete (wait with condition "complete")
            if (action.action_type == ActionType.WAIT and 
                action.parameters.get("condition") == "complete"):
                logger.info("Task marked as complete by model")
                return None
            
            logger.info(
                f"Generated next action: {action.action_type.value} "
                f"for state at {current_state.url}"
            )
            
            return action
            
        except Exception as e:
            logger.error(f"Failed to determine next action: {e}")
            raise ValueError(f"Could not determine next action: {e}")
    
    def _format_dom_for_prompt(self, interactive_elements: List['InteractiveElement']) -> str:
        """
        Format interactive elements for prompt.
        
        Args:
            interactive_elements: List of InteractiveElement objects
        
        Returns:
            Formatted string representation of DOM elements
        """
        lines = []
        for i, elem in enumerate(interactive_elements, 1):
            # Format element as HTML-like string
            attrs = []
            if elem.element_id:
                attrs.append(f'id="{elem.element_id}"')
            if elem.attributes.get('type'):
                attrs.append(f'type="{elem.attributes["type"]}"')
            if elem.selectors.aria_label:
                attrs.append(f'aria-label="{elem.selectors.aria_label}"')
            if elem.attributes.get('placeholder'):
                attrs.append(f'placeholder="{elem.attributes["placeholder"]}"')
            
            attrs_str = ' '.join(attrs) if attrs else ''
            label_text = elem.label[:50] if elem.label else ''
            
            lines.append(
                f"{i}. <{elem.tag_name} {attrs_str}>{label_text}</{elem.tag_name}>"
            )
        
        return '\n'.join(lines) if lines else "No interactive elements found"
    
    def _format_previous_actions(self, previous_actions: List['BrowserAction']) -> str:
        """
        Format previous actions for prompt.
        
        Args:
            previous_actions: List of BrowserAction objects
        
        Returns:
            Formatted string representation of previous actions
        """
        if not previous_actions:
            return "None (this is the first action)"
        
        lines = []
        for i, action in enumerate(previous_actions, 1):
            action_desc = f"{i}. {action.action_type.value}"
            
            if action.target_selector:
                if action.target_selector.aria_label:
                    action_desc += f" on element with aria-label='{action.target_selector.aria_label}'"
                elif action.target_selector.css_selector:
                    action_desc += f" on element '{action.target_selector.css_selector}'"
            
            if action.parameters:
                # Add key parameters
                if 'text' in action.parameters:
                    action_desc += f" with text='{action.parameters['text'][:30]}'"
                if 'url' in action.parameters:
                    action_desc += f" to '{action.parameters['url']}'"
            
            action_desc += f" -> {action.expected_result[:50]}"
            lines.append(action_desc)
        
        return '\n'.join(lines)
    
    def _json_to_browser_action(self, action_json: Dict[str, Any]) -> 'BrowserAction':
        """
        Convert JSON response to BrowserAction object.
        
        Args:
            action_json: Dictionary from Qwen model response
        
        Returns:
            BrowserAction object
        """
        from alice_browser_automation.types import BrowserAction, ActionType, ElementSelectors
        
        # Parse action type
        action_type_str = action_json.get('action_type', '').upper()
        try:
            action_type = ActionType[action_type_str]
        except KeyError:
            logger.error(f"Invalid action_type: {action_type_str}")
            raise ValueError(f"Invalid action type: {action_json.get('action_type')}")
        
        # Parse target selector if present
        target_selector = None
        if action_json.get('target_selector'):
            selector_data = action_json['target_selector']
            target_selector = ElementSelectors(
                css_selector=selector_data.get('css_selector', ''),
                xpath=selector_data.get('xpath', ''),
                aria_label=selector_data.get('aria_label'),
                test_id=selector_data.get('test_id'),
                text_content=selector_data.get('text_content')
            )
        
        # Create BrowserAction
        return BrowserAction(
            action_type=action_type,
            target_selector=target_selector,
            parameters=action_json.get('parameters', {}),
            expected_result=action_json.get('expected_result', ''),
            retry_count=0
        )
    
    def _get_task_context(self) -> Optional[Dict[str, Any]]:
        """
        Get current task context for multi-step tasks.
        
        Returns:
            Dictionary with task context, or None if no active task
        """
        return getattr(self, '_task_context', None)
    
    def _set_task_context(self, task: BrowserTask) -> None:
        """
        Set task context for multi-step task tracking.
        
        Args:
            task: BrowserTask to track
        """
        self._task_context = {
            'task_id': task.task_id,
            'description': task.description,
            'task_type': task.task_type.value,
            'parameters': task.parameters,
            'expected_outcome': task.expected_outcome,
            'target_url': task.target_url
        }
        logger.debug(f"Set task context for task: {task.task_id}")
    
    def _clear_task_context(self) -> None:
        """Clear task context after task completion."""
        self._task_context = None
        logger.debug("Cleared task context")


# ============================================================================
# Convenience Functions
# ============================================================================

async def create_livekit_bridge(
    ollama_host: str = "http://localhost:11434",
    model_name: str = "qwen2.5-coder:3b",
    timeout: int = 30,
    validate: bool = True
) -> LiveKitQwenBridge:
    """
    Create and optionally validate a LiveKit-Qwen bridge.
    
    Args:
        ollama_host: Ollama API host URL
        model_name: Qwen model name
        timeout: Request timeout in seconds
        validate: Whether to validate model availability on creation
    
    Returns:
        Initialized LiveKitQwenBridge
        
    Raises:
        QwenModelUnavailableError: If validate=True and model is unavailable
    """
    bridge = LiveKitQwenBridge(
        ollama_host=ollama_host,
        model_name=model_name,
        timeout=timeout
    )
    
    if validate:
        await bridge.qwen_client.validate_model_availability()
    
    return bridge
