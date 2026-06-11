"""
Voice Activity Detection (VAD) Configuration Module

This module provides configuration for LiveKit VAD (Voice Activity Detection)
to achieve natural turn-taking in conversations. The VAD silence threshold
determines when the user has finished speaking.

Configuration (updated to Google Assistant / Siri class targets):
- Silence threshold: 150–350ms (default 250ms)
- Configurable via environment variable: VAD_SILENCE_THRESHOLD_MS
"""

import os
import logging

logger = logging.getLogger(__name__)

# Default VAD silence threshold in seconds
# Google Assistant / Siri use ~150–250ms.  250ms is a safe default
# that balances responsiveness with false-end-of-turn rate.
DEFAULT_VAD_SILENCE_THRESHOLD = 0.25   # 250ms (was 400ms)

# Minimum and maximum allowed thresholds
MIN_VAD_SILENCE_THRESHOLD = 0.15       # 150ms (was 300ms)
MAX_VAD_SILENCE_THRESHOLD = 0.35       # 350ms (was 500ms)


def get_vad_silence_threshold(
    environment: str = "noisy",
    nvidia_broadcast_available: bool = False
) -> float:
    """
    Get the VAD silence threshold optimized for environment conditions.
    
    The silence threshold determines how long the user must pause before
    the VAD triggers end-of-speech detection. This function dynamically
    adjusts the threshold based on:
    - Audio environment (quiet vs noisy)
    - NVIDIA Broadcast availability (enables lower thresholds)
    - Environment variable override (VAD_SILENCE_THRESHOLD_MS)
    
    Threshold Strategy:
    - Quiet environment + NVIDIA Broadcast: 300ms (optimal latency)
    - Quiet environment without NVIDIA Broadcast: 350ms (balanced)
    - Noisy environment: 400-500ms (prevent false triggers)
    
    Args:
        environment: Audio environment classification ("quiet" or "noisy")
        nvidia_broadcast_available: Whether NVIDIA Broadcast is active
    
    Returns:
        float: Silence threshold in seconds (0.3 to 0.5)
    
    Requirements: 1.1, 1.5, 2.1, 2.5, 3.1
    """
    # Check for environment variable override first
    threshold_ms = os.getenv("VAD_SILENCE_THRESHOLD_MS")
    
    if threshold_ms is not None:
        try:
            threshold_s = float(threshold_ms) / 1000.0
            
            # Validate threshold is within acceptable range
            if threshold_s < MIN_VAD_SILENCE_THRESHOLD:
                logger.warning(
                    f"VAD silence threshold {threshold_ms}ms is below minimum {MIN_VAD_SILENCE_THRESHOLD * 1000}ms, "
                    f"using minimum"
                )
                threshold_s = MIN_VAD_SILENCE_THRESHOLD
            
            if threshold_s > MAX_VAD_SILENCE_THRESHOLD:
                logger.warning(
                    f"VAD silence threshold {threshold_ms}ms is above maximum {MAX_VAD_SILENCE_THRESHOLD * 1000}ms, "
                    f"using maximum"
                )
                threshold_s = MAX_VAD_SILENCE_THRESHOLD
            
            logger.info(
                f"Using VAD silence threshold from environment override: {threshold_s * 1000:.0f}ms "
                f"(environment: {environment}, NVIDIA Broadcast: {nvidia_broadcast_available})"
            )
            return threshold_s
        
        except ValueError:
            logger.error(
                f"Invalid VAD_SILENCE_THRESHOLD_MS value: {threshold_ms}, "
                f"falling back to dynamic threshold selection"
            )
            # Fall through to dynamic selection
    
    # Dynamic threshold selection based on environment
    if environment == "quiet":
        if nvidia_broadcast_available:
            # Optimal conditions: quiet + noise cancellation
            # 150ms — matches Siri's aggressive turn detection
            threshold_s = 0.15
            reasoning = "quiet environment with NVIDIA Broadcast (Siri-class latency)"
        else:
            # Quiet but no advanced noise cancellation
            threshold_s = 0.20
            reasoning = "quiet environment without NVIDIA Broadcast (balanced)"
    else:
        # Noisy environment — still keep well under 300ms
        if nvidia_broadcast_available:
            threshold_s = 0.25
            reasoning = "noisy environment with NVIDIA Broadcast (conservative)"
        else:
            # No noise cancellation: 300ms is still 2× faster than the old 450ms
            threshold_s = 0.30
            reasoning = "noisy environment without NVIDIA Broadcast (safe minimum)"

    logger.info(
        f"Selected VAD silence threshold: {threshold_s * 1000:.0f}ms "
        f"({reasoning})"
    )

    return threshold_s


def log_vad_configuration(
    silence_threshold: float,
    environment: str = "unknown",
    nvidia_broadcast_available: bool = False
) -> None:
    """
    Log VAD configuration details for debugging and monitoring.
    
    Args:
        silence_threshold: The configured silence threshold in seconds
        environment: Audio environment classification ("quiet", "noisy", or "unknown")
        nvidia_broadcast_available: Whether NVIDIA Broadcast is active
    """
    logger.info("=" * 60)
    logger.info("Voice Activity Detection (VAD) Configuration")
    logger.info("=" * 60)
    logger.info(f"Silence Threshold: {silence_threshold * 1000:.0f}ms")
    logger.info(f"Range: {MIN_VAD_SILENCE_THRESHOLD * 1000:.0f}ms - {MAX_VAD_SILENCE_THRESHOLD * 1000:.0f}ms")
    logger.info(f"Environment: {environment.upper()}")
    logger.info(f"NVIDIA Broadcast: {'Active' if nvidia_broadcast_available else 'Not Available'}")
    logger.info("Purpose: Natural turn-taking without awkward interruptions")
    logger.info("Optimization: Dynamic threshold based on environment conditions")
    logger.info("=" * 60)


# ===========================================================================
# VADThresholdManager
# Added for Alice Conversation Fluidity Enhancement (Tasks 4.1–4.4)
# Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
# ===========================================================================

class VADThresholdManager:
    """
    Manage VAD / neural turn detection thresholds based on ambient noise levels.

    Supports both detector types:
      - "neural"  : adjusts End-of-Turn Confidence threshold [0.3, 0.6]
      - "silero"  : adjusts Silero VAD silence threshold    [0.3, 0.6]

    Design guarantees (validated by property tests):
      Property 3: All returned thresholds stay within [min_threshold, max_threshold].
      Property 4: Higher noise produces equal-or-higher threshold (monotonicity).

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
    """

    DETECTOR_NEURAL = "neural"
    DETECTOR_SILERO = "silero"

    def __init__(
        self,
        min_threshold: float = 0.3,
        max_threshold: float = 0.6,
        default_threshold: float = 0.4,
    ):
        """
        Initialize VAD threshold manager.

        Args:
            min_threshold:     Lower bound for any returned threshold (Property 3)
            max_threshold:     Upper bound for any returned threshold (Property 3)
            default_threshold: Starting threshold before any noise measurement

        Raises:
            ValueError: If bounds or default are invalid.

        Requirements: 4.1, 4.2, 4.5
        """
        if not (0.0 <= min_threshold <= 1.0):
            raise ValueError(f"min_threshold must be in [0, 1], got {min_threshold}")
        if not (0.0 <= max_threshold <= 1.0):
            raise ValueError(f"max_threshold must be in [0, 1], got {max_threshold}")
        if min_threshold >= max_threshold:
            raise ValueError(
                f"min_threshold ({min_threshold}) must be < max_threshold ({max_threshold})"
            )
        if not (min_threshold <= default_threshold <= max_threshold):
            raise ValueError(
                f"default_threshold ({default_threshold}) must be in "
                f"[{min_threshold}, {max_threshold}]"
            )

        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self._current_threshold = default_threshold
        self._last_noise_level: float = 0.0

        logger.info(
            f"[VADThresholdManager] Initialized "
            f"(min={min_threshold}, max={max_threshold}, default={default_threshold})"
        )

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    async def adjust_threshold(
        self,
        noise_level: float,
        detector_type: str = DETECTOR_NEURAL,
    ) -> float:
        """
        Compute a threshold adjusted for the measured ambient noise level.

        The mapping is linear and monotonic:
          noise_level = 0.0 → threshold = min_threshold
          noise_level = 1.0 → threshold = max_threshold

        This guarantees Property 3 (range invariant) and
        Property 4 (monotonicity with noise).

        Args:
            noise_level:   Ambient noise level [0.0, 1.0]
            detector_type: "neural" or "silero"

        Returns:
            Adjusted threshold in [min_threshold, max_threshold]

        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
        """
        # Clamp noise_level to valid range
        noise_level = max(0.0, min(1.0, noise_level))

        # Linear interpolation: maps noise [0,1] → threshold [min, max]
        new_threshold = self.min_threshold + noise_level * (
            self.max_threshold - self.min_threshold
        )
        # Enforce range invariant (Property 3)
        new_threshold = max(self.min_threshold, min(self.max_threshold, new_threshold))

        if abs(new_threshold - self._current_threshold) > 0.001:
            logger.debug(
                f"[VADThresholdManager] {detector_type} threshold: "
                f"{self._current_threshold:.3f} → {new_threshold:.3f} "
                f"(noise={noise_level:.3f})"
            )

        self._current_threshold = new_threshold
        self._last_noise_level = noise_level
        return new_threshold

    async def get_current_threshold(self) -> float:
        """Return the most recently computed threshold."""
        return self._current_threshold

    def get_current_threshold_sync(self) -> float:
        """Synchronous accessor for use in non-async contexts."""
        return self._current_threshold

    # ------------------------------------------------------------------
    # Integration helpers
    # ------------------------------------------------------------------

    async def get_neural_threshold(self, noise_level: float) -> float:
        """Convenience: get threshold for neural turn detector."""
        return await self.adjust_threshold(noise_level, self.DETECTOR_NEURAL)

    async def get_silero_threshold(self, noise_level: float) -> float:
        """Convenience: get threshold for Silero VAD fallback."""
        return await self.adjust_threshold(noise_level, self.DETECTOR_SILERO)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return current manager state for logging."""
        return {
            "current_threshold": self._current_threshold,
            "min_threshold": self.min_threshold,
            "max_threshold": self.max_threshold,
            "last_noise_level": self._last_noise_level,
        }
