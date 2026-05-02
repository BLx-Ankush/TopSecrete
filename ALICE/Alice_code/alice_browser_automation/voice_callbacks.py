"""
Voice Interaction Callbacks for Alice Browser Automation

This module provides callback adapters for integrating browser automation
with Alice's voice interaction system.

**Validates: Requirements 11.2, 11.3, 11.4, 11.5, 11.6**
"""

import logging
import asyncio
from typing import Optional, Callable, Any
from datetime import datetime


logger = logging.getLogger(__name__)


class VoiceInteractionCallbacks:
    """
    Callback adapter for Alice voice interactions.
    
    This class provides callbacks for:
    - Progress updates during task execution
    - User input requests (OTP, confirmations)
    - Task completion notifications
    - Task cancellation handling
    
    **Validates: Requirements 11.2, 11.3, 11.4, 11.5, 11.6**
    """
    
    def __init__(
        self,
        voice_output_fn: Optional[Callable[[str], None]] = None,
        voice_input_fn: Optional[Callable[[str], str]] = None
    ):
        """
        Initialize voice interaction callbacks.
        
        Args:
            voice_output_fn: Function to send voice output to user
                           Signature: (message: str) -> None
            voice_input_fn: Function to get voice input from user
                          Signature: (prompt: str) -> str
        """
        self.voice_output_fn = voice_output_fn or self._default_output
        self.voice_input_fn = voice_input_fn or self._default_input
        
        # Track last progress update time for rate limiting
        self._last_progress_time = datetime.now()
        self._progress_interval_seconds = 10  # Requirement 12.5
        
        # Cancellation flag
        self._cancellation_requested = False
    
    def _default_output(self, message: str) -> None:
        """Default output function (logs to console)."""
        logger.info(f"[Voice Output] {message}")
    
    def _default_input(self, prompt: str) -> str:
        """Default input function (returns empty string)."""
        logger.warning(f"[Voice Input Requested] {prompt}")
        return ""
    
    def progress_callback(self, message: str) -> None:
        """
        Progress callback for task execution.
        
        **Validates: Requirement 11.2** - Provide real-time status updates
        **Validates: Requirement 12.5** - Progress updates every 10 seconds
        
        Args:
            message: Progress message to send to user
        """
        # Rate limit progress updates (every 10 seconds)
        now = datetime.now()
        time_since_last = (now - self._last_progress_time).total_seconds()
        
        # Always send important messages (starting, completing, errors)
        important_keywords = [
            "starting", "completed", "failed", "error", "success",
            "navigating", "booking", "confirming", "payment"
        ]
        is_important = any(keyword in message.lower() for keyword in important_keywords)
        
        if is_important or time_since_last >= self._progress_interval_seconds:
            self.voice_output_fn(message)
            self._last_progress_time = now
        else:
            # Log but don't send to voice
            logger.debug(f"Progress (not sent): {message}")
    
    async def request_user_input(
        self,
        prompt: str,
        input_type: str = "text"
    ) -> str:
        """
        Request input from user via voice.
        
        **Validates: Requirement 11.3** - Prompt user via voice when needed
        
        Args:
            prompt: Prompt message to send to user
            input_type: Type of input expected (text, otp, confirmation)
        
        Returns:
            User's voice input as text
        """
        logger.info(f"Requesting user input: {prompt} (type: {input_type})")
        
        # Send prompt via voice
        self.voice_output_fn(prompt)
        
        # Get input via voice
        # Note: In real implementation, this would wait for voice input
        # For now, we use the provided input function
        user_input = self.voice_input_fn(prompt)
        
        logger.info(f"Received user input: {user_input}")
        return user_input
    
    async def request_otp(self) -> str:
        """
        Request OTP from user via voice.
        
        **Validates: Requirement 11.3** - Prompt user for OTP
        
        Returns:
            OTP code as string
        """
        prompt = (
            "I need an OTP code to continue. "
            "Please tell me the 6-digit code you received."
        )
        return await self.request_user_input(prompt, input_type="otp")
    
    async def request_confirmation(
        self,
        action: str,
        details: Optional[str] = None
    ) -> bool:
        """
        Request confirmation from user via voice.
        
        **Validates: Requirement 11.3** - Prompt user for confirmation
        
        Args:
            action: Action to confirm (e.g., "payment", "booking")
            details: Optional details about the action
        
        Returns:
            True if user confirms, False otherwise
        """
        prompt = f"Please confirm: {action}"
        if details:
            prompt += f"\n\nDetails: {details}"
        prompt += "\n\nSay 'yes' to confirm or 'no' to cancel."
        
        response = await self.request_user_input(prompt, input_type="confirmation")
        
        # Parse confirmation response
        response_lower = response.lower().strip()
        confirmed = response_lower in ["yes", "confirm", "ok", "proceed", "continue"]
        
        logger.info(f"Confirmation result: {confirmed} (response: {response})")
        return confirmed
    
    def task_completion_callback(
        self,
        success: bool,
        summary: str,
        actions_taken: int,
        duration_seconds: float,
        extracted_data: Optional[dict] = None
    ) -> None:
        """
        Callback for task completion.
        
        **Validates: Requirement 11.4** - Confirm task completion and provide summary
        
        Args:
            success: Whether task completed successfully
            summary: Summary of task execution
            actions_taken: Number of actions performed
            duration_seconds: Task duration in seconds
            extracted_data: Optional extracted data from task
        """
        if success:
            message = f"✅ Task completed successfully!\n\n{summary}"
        else:
            message = f"❌ Task failed.\n\n{summary}"
        
        message += f"\n\nActions performed: {actions_taken}"
        message += f"\nTime taken: {duration_seconds:.1f} seconds"
        
        if extracted_data:
            message += "\n\nExtracted information:"
            for key, value in extracted_data.items():
                message += f"\n• {key}: {value}"
        
        self.voice_output_fn(message)
        logger.info(f"Task completion notification sent: success={success}")
    
    def request_cancellation(self) -> None:
        """
        Request task cancellation.
        
        **Validates: Requirement 11.5** - Support interruption commands
        """
        self._cancellation_requested = True
        logger.info("Task cancellation requested")
        self.voice_output_fn("Cancelling task...")
    
    def is_cancellation_requested(self) -> bool:
        """
        Check if cancellation was requested.
        
        **Validates: Requirement 11.5** - Support interruption commands
        
        Returns:
            True if cancellation requested, False otherwise
        """
        return self._cancellation_requested
    
    def reset_cancellation(self) -> None:
        """Reset cancellation flag for new task."""
        self._cancellation_requested = False
    
    def maintain_context(self, context_data: dict) -> None:
        """
        Maintain conversation context across tasks.
        
        **Validates: Requirement 11.6** - Maintain conversation context
        
        Args:
            context_data: Context data to maintain
        """
        # Store context for next task
        # In real implementation, this would integrate with Alice's memory system
        logger.info(f"Maintaining context: {context_data}")


class LiveKitVoiceAdapter:
    """
    Adapter for LiveKit voice interactions.
    
    This adapter integrates VoiceInteractionCallbacks with LiveKit's
    voice agent system.
    """
    
    def __init__(self, livekit_session=None):
        """
        Initialize LiveKit voice adapter.
        
        Args:
            livekit_session: LiveKit session object (optional)
        """
        self.livekit_session = livekit_session
        self.callbacks = VoiceInteractionCallbacks(
            voice_output_fn=self._send_voice_output,
            voice_input_fn=self._get_voice_input
        )
    
    def _send_voice_output(self, message: str) -> None:
        """
        Send voice output via LiveKit.
        
        Args:
            message: Message to send
        """
        if self.livekit_session:
            # In real implementation, this would use LiveKit's TTS
            # For now, we just log
            logger.info(f"[LiveKit Voice Output] {message}")
        else:
            logger.info(f"[Voice Output] {message}")
    
    def _get_voice_input(self, prompt: str) -> str:
        """
        Get voice input via LiveKit.
        
        Args:
            prompt: Prompt to display
        
        Returns:
            User's voice input as text
        """
        if self.livekit_session:
            # In real implementation, this would use LiveKit's STT
            # For now, we return empty string
            logger.warning(f"[LiveKit Voice Input Requested] {prompt}")
            return ""
        else:
            logger.warning(f"[Voice Input Requested] {prompt}")
            return ""
    
    def get_progress_callback(self) -> Callable[[str], None]:
        """
        Get progress callback function.
        
        Returns:
            Progress callback function
        """
        return self.callbacks.progress_callback
    
    def get_callbacks(self) -> VoiceInteractionCallbacks:
        """
        Get voice interaction callbacks.
        
        Returns:
            VoiceInteractionCallbacks instance
        """
        return self.callbacks


# Convenience function for creating callbacks
def create_voice_callbacks(
    livekit_session=None
) -> VoiceInteractionCallbacks:
    """
    Create voice interaction callbacks for browser automation.
    
    Args:
        livekit_session: Optional LiveKit session object
    
    Returns:
        VoiceInteractionCallbacks instance
    """
    if livekit_session:
        adapter = LiveKitVoiceAdapter(livekit_session)
        return adapter.get_callbacks()
    else:
        return VoiceInteractionCallbacks()
