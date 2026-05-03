"""
Voice Activity Detection (VAD) Configuration Module

This module provides configuration for LiveKit VAD (Voice Activity Detection)
to achieve natural turn-taking in conversations. The VAD silence threshold
determines when the user has finished speaking.

Configuration:
- Silence threshold: 300-500ms (default 400ms)
- Configurable via environment variable: VAD_SILENCE_THRESHOLD_MS
"""

import os
import logging

logger = logging.getLogger(__name__)

# Default VAD silence threshold in seconds (400ms = 0.4s)
# This is the midpoint of the 300-500ms range specified in requirements
DEFAULT_VAD_SILENCE_THRESHOLD = 0.4

# Minimum and maximum allowed thresholds
MIN_VAD_SILENCE_THRESHOLD = 0.3  # 300ms
MAX_VAD_SILENCE_THRESHOLD = 0.5  # 500ms


def get_vad_silence_threshold() -> float:
    """
    Get the VAD silence threshold from environment variable or use default.
    
    The silence threshold determines how long the user must pause before
    the VAD triggers end-of-speech detection.
    
    Returns:
        float: Silence threshold in seconds (0.3 to 0.5)
    """
    threshold_ms = os.getenv("VAD_SILENCE_THRESHOLD_MS")
    
    if threshold_ms is None:
        logger.info(
            f"VAD_SILENCE_THRESHOLD_MS not set, using default: {DEFAULT_VAD_SILENCE_THRESHOLD * 1000}ms"
        )
        return DEFAULT_VAD_SILENCE_THRESHOLD
    
    try:
        threshold_s = float(threshold_ms) / 1000.0
        
        # Validate threshold is within acceptable range
        if threshold_s < MIN_VAD_SILENCE_THRESHOLD:
            logger.warning(
                f"VAD silence threshold {threshold_ms}ms is below minimum {MIN_VAD_SILENCE_THRESHOLD * 1000}ms, "
                f"using minimum"
            )
            return MIN_VAD_SILENCE_THRESHOLD
        
        if threshold_s > MAX_VAD_SILENCE_THRESHOLD:
            logger.warning(
                f"VAD silence threshold {threshold_ms}ms is above maximum {MAX_VAD_SILENCE_THRESHOLD * 1000}ms, "
                f"using maximum"
            )
            return MAX_VAD_SILENCE_THRESHOLD
        
        logger.info(f"Using VAD silence threshold: {threshold_ms}ms")
        return threshold_s
    
    except ValueError:
        logger.error(
            f"Invalid VAD_SILENCE_THRESHOLD_MS value: {threshold_ms}, using default: {DEFAULT_VAD_SILENCE_THRESHOLD * 1000}ms"
        )
        return DEFAULT_VAD_SILENCE_THRESHOLD


def log_vad_configuration(silence_threshold: float) -> None:
    """
    Log VAD configuration details for debugging and monitoring.
    
    Args:
        silence_threshold: The configured silence threshold in seconds
    """
    logger.info("=" * 60)
    logger.info("Voice Activity Detection (VAD) Configuration")
    logger.info("=" * 60)
    logger.info(f"Silence Threshold: {silence_threshold * 1000:.0f}ms")
    logger.info(f"Range: {MIN_VAD_SILENCE_THRESHOLD * 1000:.0f}ms - {MAX_VAD_SILENCE_THRESHOLD * 1000:.0f}ms")
    logger.info("Purpose: Natural turn-taking without awkward interruptions")
    logger.info("=" * 60)
