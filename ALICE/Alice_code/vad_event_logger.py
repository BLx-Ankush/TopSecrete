"""
VAD Event Logger Module

This module provides logging functionality for Voice Activity Detection (VAD) events
to monitor and tune VAD performance for natural turn-taking.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class VADEventLogger:
    """
    Logger for VAD events to track speech detection and silence duration.
    
    This helps monitor VAD performance and tune the silence threshold for
    optimal turn-taking behavior.
    """
    
    def __init__(self):
        self.speech_start_time: Optional[float] = None
        self.last_speech_end_time: Optional[float] = None
        self.silence_start_time: Optional[float] = None
        
    def on_speech_start(self) -> None:
        """Called when VAD detects start of speech"""
        self.speech_start_time = time.time()
        
        if self.silence_start_time is not None:
            silence_duration = (self.speech_start_time - self.silence_start_time) * 1000
            logger.debug(f"[VAD] Speech started after {silence_duration:.0f}ms silence")
        else:
            logger.debug("[VAD] Speech started")
        
        self.silence_start_time = None
    
    def on_speech_end(self, pause_duration_ms: Optional[float] = None) -> None:
        """
        Called when VAD detects end of speech
        
        Args:
            pause_duration_ms: Duration of the pause that triggered end-of-speech (in milliseconds)
        """
        self.last_speech_end_time = time.time()
        self.silence_start_time = self.last_speech_end_time
        
        if self.speech_start_time is not None:
            speech_duration = (self.last_speech_end_time - self.speech_start_time) * 1000
            
            if pause_duration_ms is not None:
                logger.info(
                    f"[VAD] End-of-speech detected | "
                    f"Speech duration: {speech_duration:.0f}ms | "
                    f"Pause duration: {pause_duration_ms:.0f}ms"
                )
            else:
                logger.info(
                    f"[VAD] End-of-speech detected | "
                    f"Speech duration: {speech_duration:.0f}ms"
                )
        else:
            if pause_duration_ms is not None:
                logger.info(f"[VAD] End-of-speech detected | Pause duration: {pause_duration_ms:.0f}ms")
            else:
                logger.info("[VAD] End-of-speech detected")
        
        self.speech_start_time = None
    
    def on_vad_trigger(self, silence_duration_ms: float) -> None:
        """
        Called when VAD triggers due to silence threshold being met
        
        Args:
            silence_duration_ms: Duration of silence that triggered VAD (in milliseconds)
        """
        logger.info(
            f"[VAD] Trigger | Silence threshold met: {silence_duration_ms:.0f}ms | "
            f"User turn complete, ready for Alice response"
        )
    
    def log_vad_metrics(self, probability: float, silence_duration: float, speech_duration: float) -> None:
        """
        Log detailed VAD metrics for analysis
        
        Args:
            probability: VAD probability score (0.0 to 1.0)
            silence_duration: Current silence duration in seconds
            speech_duration: Current speech duration in seconds
        """
        logger.debug(
            f"[VAD Metrics] Probability: {probability:.2f} | "
            f"Silence: {silence_duration * 1000:.0f}ms | "
            f"Speech: {speech_duration * 1000:.0f}ms"
        )


# Global VAD event logger instance
vad_event_logger = VADEventLogger()
