"""
Integration module for interim transcription handling with LiveKit AgentSession.

This module connects the InterimTranscriptionHandler to the LiveKit AgentSession
to process interim and final transcription results from the Gemini Realtime Model.

Requirements covered:
- 2.1: Configure interim result callback handler in LiveKit agent
- 2.2: Extract confidence scores and timestamps from interim results
- 2.3: Use final transcription for LLM inference if different from interim
- 2.6: Add logging for interim result latency tracking
"""

import logging
from typing import TYPE_CHECKING

from deepgram_interim_handler import get_interim_handler, InterimTranscript

if TYPE_CHECKING:
    from livekit.agents.voice import AgentSession

logger = logging.getLogger(__name__)


class InterimTranscriptionIntegration:
    """
    Integrates interim transcription handling with LiveKit AgentSession.
    
    This class:
    1. Hooks into AgentSession transcription events
    2. Routes interim and final transcripts to the handler
    3. Prepares LLM context using interim results
    4. Handles reconciliation between interim and final transcripts
    """
    
    def __init__(self, session: "AgentSession"):
        self._session = session
        self._handler = get_interim_handler()
        self._enabled = True
        
        # Register event handlers
        self._setup_event_handlers()
        
        logger.info("[Interim STT Integration] Initialized with interim results enabled")
    
    def _setup_event_handlers(self):
        """Set up event handlers for the AgentSession"""
        
        # Hook into user state changes to detect speech start
        @self._session.on("user_state_changed")
        def on_user_state_changed(event):
            if event.new_state == "speaking":
                # User started speaking - reset metrics
                import asyncio
                asyncio.create_task(self._handler.on_speech_started())
                logger.debug("[Interim STT Integration] User started speaking")
        
        # Hook into transcription events
        @self._session.on("user_input_transcribed")
        def on_user_input_transcribed(event):
            """
            Process transcription events from the Gemini Realtime Model.
            
            The event contains:
            - transcript: str - The transcribed text
            - is_final: bool - Whether this is a final or interim result
            - speaker_id: Optional[str] - Speaker identifier
            - language: Optional[str] - Detected language
            """
            import asyncio
            
            if not self._enabled:
                return
            
            transcript = event.transcript
            is_final = event.is_final
            speaker_id = getattr(event, 'speaker_id', None)
            
            # Estimate confidence (Gemini doesn't provide explicit confidence scores)
            # We use 0.8 for interim and 1.0 for final as reasonable defaults
            confidence = 1.0 if is_final else 0.8
            
            if is_final:
                # Process final transcript
                asyncio.create_task(
                    self._handler.on_final_result(
                        text=transcript,
                        confidence=confidence,
                        speaker_id=speaker_id
                    )
                )
            else:
                # Process interim transcript
                asyncio.create_task(
                    self._handler.on_interim_result(
                        text=transcript,
                        confidence=confidence,
                        speaker_id=speaker_id
                    )
                )
    
    def enable(self):
        """Enable interim transcription processing"""
        self._enabled = True
        logger.info("[Interim STT Integration] Enabled")
    
    def disable(self):
        """Disable interim transcription processing"""
        self._enabled = False
        logger.info("[Interim STT Integration] Disabled")
    
    def is_enabled(self) -> bool:
        """Check if interim transcription processing is enabled"""
        return self._enabled
    
    def get_handler(self):
        """Get the underlying interim transcription handler"""
        return self._handler
    
    def register_interim_callback(self, callback):
        """
        Register a callback for interim transcription results.
        
        The callback will be called with an InterimTranscript object.
        This can be used to begin LLM context preparation.
        """
        self._handler.register_interim_callback(callback)
    
    def register_final_callback(self, callback):
        """
        Register a callback for final transcription results.
        
        The callback will be called with (InterimTranscript, bool) where
        the bool indicates if the final differs from the last interim.
        """
        self._handler.register_final_callback(callback)


def setup_interim_transcription(session: "AgentSession") -> InterimTranscriptionIntegration:
    """
    Set up interim transcription handling for an AgentSession.
    
    Args:
        session: The LiveKit AgentSession to integrate with
        
    Returns:
        InterimTranscriptionIntegration: The integration instance
        
    Example:
        ```python
        async def entrypoint(ctx: agents.JobContext):
            session = AgentSession(...)
            
            # Set up interim transcription handling
            interim_integration = setup_interim_transcription(session)
            
            # Optionally register callbacks for custom processing
            def on_interim(transcript: InterimTranscript):
                print(f"Interim: {transcript.text}")
            
            interim_integration.register_interim_callback(on_interim)
            
            await session.start(...)
        ```
    """
    integration = InterimTranscriptionIntegration(session)
    logger.info("[Interim STT] Setup complete - interim results enabled")
    return integration
