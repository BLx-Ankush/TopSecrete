"""
Interim Transcription Handler for Alice Voice Agent

This module implements interim transcription processing for the Gemini Realtime Model,
providing functionality similar to Deepgram Nova-3's interim results feature.

Requirements covered:
- 2.1: Enable interim_results parameter in configuration
- 2.2: Implement interim transcription processing pipeline  
- 2.3: Implement final transcription reconciliation
- 2.6: Add logging for interim result latency tracking
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class InterimTranscript:
    """Represents an interim transcription result"""
    text: str
    confidence: float
    timestamp: float
    is_final: bool = False
    speaker_id: Optional[str] = None


@dataclass
class TranscriptionMetrics:
    """Tracks latency metrics for transcription processing"""
    speech_start_time: Optional[float] = None
    first_interim_time: Optional[float] = None
    final_transcript_time: Optional[float] = None
    interim_count: int = 0
    
    def get_interim_latency(self) -> Optional[float]:
        """Calculate latency from speech start to first interim result"""
        if self.speech_start_time and self.first_interim_time:
            return self.first_interim_time - self.speech_start_time
        return None
    
    def get_total_latency(self) -> Optional[float]:
        """Calculate total latency from speech start to final transcript"""
        if self.speech_start_time and self.final_transcript_time:
            return self.final_transcript_time - self.speech_start_time
        return None


class InterimTranscriptionHandler:
    """
    Handles interim transcription results from the Gemini Realtime Model.
    
    This handler:
    1. Receives interim transcription results as they arrive
    2. Extracts confidence scores and timestamps
    3. Begins LLM context preparation using interim results
    4. Reconciles final transcriptions with interim results
    5. Tracks latency metrics for performance monitoring
    """
    
    def __init__(self):
        self._current_interim: Optional[InterimTranscript] = None
        self._last_final: Optional[InterimTranscript] = None
        self._metrics = TranscriptionMetrics()
        self._interim_callbacks: list = []
        self._final_callbacks: list = []
        self._lock = asyncio.Lock()
        
    def register_interim_callback(self, callback):
        """Register a callback to be called when interim results arrive"""
        self._interim_callbacks.append(callback)
    
    def register_final_callback(self, callback):
        """Register a callback to be called when final transcripts arrive"""
        self._final_callbacks.append(callback)
    
    async def on_speech_started(self):
        """Called when user speech is detected (VAD trigger)"""
        async with self._lock:
            self._metrics = TranscriptionMetrics()
            self._metrics.speech_start_time = time.time()
            self._current_interim = None
            self._last_final = None
            
            logger.debug(
                "[Interim STT] Speech started",
                extra={"timestamp": self._metrics.speech_start_time}
            )
    
    async def on_interim_result(
        self,
        text: str,
        confidence: float = 0.0,
        speaker_id: Optional[str] = None
    ):
        """
        Process an interim transcription result.
        
        Args:
            text: The interim transcription text
            confidence: Confidence score (0.0-1.0)
            speaker_id: Optional speaker identifier
        """
        async with self._lock:
            current_time = time.time()
            
            # Track first interim result latency
            if self._metrics.interim_count == 0 and self._metrics.speech_start_time:
                self._metrics.first_interim_time = current_time
                interim_latency = self._metrics.get_interim_latency()
                
                logger.info(
                    "[Interim STT] First interim result received",
                    extra={
                        "latency_ms": f"{interim_latency * 1000:.2f}" if interim_latency else "N/A",
                        "text_length": len(text),
                        "confidence": f"{confidence:.2f}"
                    }
                )
            
            self._metrics.interim_count += 1
            
            # Store current interim result
            self._current_interim = InterimTranscript(
                text=text,
                confidence=confidence,
                timestamp=current_time,
                is_final=False,
                speaker_id=speaker_id
            )
            
            logger.debug(
                "[Interim STT] Interim result",
                extra={
                    "text": text[:50] + "..." if len(text) > 50 else text,
                    "confidence": f"{confidence:.2f}",
                    "interim_count": self._metrics.interim_count
                }
            )
            
            # Notify callbacks for LLM context preparation
            for callback in self._interim_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(self._current_interim)
                    else:
                        callback(self._current_interim)
                except Exception as e:
                    logger.error(f"Error in interim callback: {e}", exc_info=True)
    
    async def on_final_result(
        self,
        text: str,
        confidence: float = 1.0,
        speaker_id: Optional[str] = None
    ) -> bool:
        """
        Process a final transcription result and reconcile with interim results.
        
        Args:
            text: The final transcription text
            confidence: Confidence score (0.0-1.0)
            speaker_id: Optional speaker identifier
            
        Returns:
            bool: True if final differs from last interim (needs LLM update)
        """
        async with self._lock:
            current_time = time.time()
            self._metrics.final_transcript_time = current_time
            
            # Calculate total latency
            total_latency = self._metrics.get_total_latency()
            
            # Create final transcript
            final_transcript = InterimTranscript(
                text=text,
                confidence=confidence,
                timestamp=current_time,
                is_final=True,
                speaker_id=speaker_id
            )
            
            # Reconcile with last interim result
            differs_from_interim = False
            if self._current_interim:
                differs_from_interim = self._current_interim.text != text
                
                if differs_from_interim:
                    logger.info(
                        "[Interim STT] Final transcript differs from interim",
                        extra={
                            "interim_text": self._current_interim.text[:50],
                            "final_text": text[:50],
                            "interim_count": self._metrics.interim_count
                        }
                    )
                else:
                    logger.debug(
                        "[Interim STT] Final transcript matches last interim",
                        extra={"text": text[:50]}
                    )
            
            logger.info(
                "[Interim STT] Final transcript received",
                extra={
                    "total_latency_ms": f"{total_latency * 1000:.2f}" if total_latency else "N/A",
                    "interim_count": self._metrics.interim_count,
                    "text_length": len(text),
                    "confidence": f"{confidence:.2f}",
                    "differs_from_interim": differs_from_interim
                }
            )
            
            self._last_final = final_transcript
            
            # Notify callbacks
            for callback in self._final_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(final_transcript, differs_from_interim)
                    else:
                        callback(final_transcript, differs_from_interim)
                except Exception as e:
                    logger.error(f"Error in final callback: {e}", exc_info=True)
            
            return differs_from_interim
    
    def get_metrics(self) -> TranscriptionMetrics:
        """Get current transcription metrics"""
        return self._metrics
    
    def get_current_interim(self) -> Optional[InterimTranscript]:
        """Get the most recent interim transcript"""
        return self._current_interim
    
    def get_last_final(self) -> Optional[InterimTranscript]:
        """Get the most recent final transcript"""
        return self._last_final


# Global handler instance for the agent
_global_handler: Optional[InterimTranscriptionHandler] = None


def get_interim_handler() -> InterimTranscriptionHandler:
    """Get or create the global interim transcription handler"""
    global _global_handler
    if _global_handler is None:
        _global_handler = InterimTranscriptionHandler()
    return _global_handler


def reset_interim_handler():
    """Reset the global handler (useful for testing)"""
    global _global_handler
    _global_handler = None
