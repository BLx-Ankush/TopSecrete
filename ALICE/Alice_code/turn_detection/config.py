"""
Configuration for Neural Turn Detector.

This module provides configuration management for neural turn detection,
including environment variable loading and validation.

Requirements: 15.1, 15.4, 15.5, 15.6, 15.8, 15.9
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class NeuralTurnDetectorConfig:
    """
    Configuration for Neural Turn Detector.
    
    This class manages configuration parameters for neural turn detection,
    including confidence thresholds, silence durations, and feature flags.
    
    Environment Variables:
    - NEURAL_TURN_DETECTOR_ENABLED: Enable neural turn detection (default: true)
    - END_OF_TURN_CONFIDENCE_THRESHOLD: Confidence threshold (default: 0.4)
    - MIN_TURN_SILENCE_MS: Minimum silence duration (default: 300)
    - MAX_TURN_SILENCE_MS: Maximum silence duration (default: 1200)
    - NEURAL_TURN_DETECTOR_HEALTH_CHECK_INTERVAL_S: Health check interval (default: 30)
    - NEURAL_TURN_DETECTOR_MAX_FAILURES: Max failures before fallback (default: 3)
    
    Requirements: 15.1, 15.4, 15.5, 15.6, 15.8, 15.9
    """
    
    # Default configuration values
    DEFAULT_ENABLED = True
    DEFAULT_CONFIDENCE_THRESHOLD = 0.4
    DEFAULT_MIN_TURN_SILENCE_MS = 300
    DEFAULT_MAX_TURN_SILENCE_MS = 1200
    DEFAULT_HEALTH_CHECK_INTERVAL_S = 30
    DEFAULT_MAX_FAILURES = 3
    
    # Valid ranges for configuration parameters
    MIN_CONFIDENCE_THRESHOLD = 0.0
    MAX_CONFIDENCE_THRESHOLD = 1.0
    MIN_SILENCE_MS = 100
    MAX_SILENCE_MS = 5000
    
    def __init__(
        self,
        enabled: bool = DEFAULT_ENABLED,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        min_turn_silence_ms: int = DEFAULT_MIN_TURN_SILENCE_MS,
        max_turn_silence_ms: int = DEFAULT_MAX_TURN_SILENCE_MS,
        health_check_interval_s: int = DEFAULT_HEALTH_CHECK_INTERVAL_S,
        max_failures: int = DEFAULT_MAX_FAILURES
    ):
        """
        Initialize neural turn detector configuration.
        
        Args:
            enabled: Enable neural turn detection
            confidence_threshold: Minimum confidence for end-of-turn (0.0-1.0)
            min_turn_silence_ms: Minimum silence duration to consider turn end
            max_turn_silence_ms: Maximum silence before forcing turn end
            health_check_interval_s: Health check interval in seconds
            max_failures: Maximum failures before fallback to Silero VAD
        
        Raises:
            ValueError: If configuration parameters are invalid
        
        Requirements: 15.4, 15.5, 15.6, 15.8, 15.9
        """
        self.enabled = enabled
        self.confidence_threshold = confidence_threshold
        self.min_turn_silence_ms = min_turn_silence_ms
        self.max_turn_silence_ms = max_turn_silence_ms
        self.health_check_interval_s = health_check_interval_s
        self.max_failures = max_failures
        
        # Validate configuration
        self._validate()
        
        logger.info(
            f"NeuralTurnDetectorConfig initialized: "
            f"enabled={enabled}, "
            f"confidence_threshold={confidence_threshold}, "
            f"min_silence={min_turn_silence_ms}ms, "
            f"max_silence={max_turn_silence_ms}ms, "
            f"health_check_interval={health_check_interval_s}s, "
            f"max_failures={max_failures}"
        )
    
    def _validate(self) -> None:
        """
        Validate configuration parameters.
        
        Raises:
            ValueError: If any parameter is invalid
        
        Requirements: 15.8, 15.9
        """
        # Validate confidence threshold
        if not self.MIN_CONFIDENCE_THRESHOLD <= self.confidence_threshold <= self.MAX_CONFIDENCE_THRESHOLD:
            raise ValueError(
                f"Confidence threshold must be between {self.MIN_CONFIDENCE_THRESHOLD} "
                f"and {self.MAX_CONFIDENCE_THRESHOLD}, got {self.confidence_threshold}"
            )
        
        # Validate min silence
        if not self.MIN_SILENCE_MS <= self.min_turn_silence_ms <= self.MAX_SILENCE_MS:
            raise ValueError(
                f"Minimum turn silence must be between {self.MIN_SILENCE_MS}ms "
                f"and {self.MAX_SILENCE_MS}ms, got {self.min_turn_silence_ms}ms"
            )
        
        # Validate max silence
        if not self.MIN_SILENCE_MS <= self.max_turn_silence_ms <= self.MAX_SILENCE_MS:
            raise ValueError(
                f"Maximum turn silence must be between {self.MIN_SILENCE_MS}ms "
                f"and {self.MAX_SILENCE_MS}ms, got {self.max_turn_silence_ms}ms"
            )
        
        # Validate max silence > min silence
        if self.max_turn_silence_ms <= self.min_turn_silence_ms:
            raise ValueError(
                f"Maximum turn silence ({self.max_turn_silence_ms}ms) must be greater "
                f"than minimum turn silence ({self.min_turn_silence_ms}ms)"
            )
        
        # Validate health check interval
        if self.health_check_interval_s <= 0:
            raise ValueError(
                f"Health check interval must be positive, got {self.health_check_interval_s}s"
            )
        
        # Validate max failures
        if self.max_failures < 0:
            raise ValueError(
                f"Max failures must be non-negative, got {self.max_failures}"
            )
    
    @classmethod
    def from_env(cls) -> 'NeuralTurnDetectorConfig':
        """
        Create configuration from environment variables.
        
        This method reads configuration from environment variables and creates
        a NeuralTurnDetectorConfig instance with validation.
        
        Returns:
            NeuralTurnDetectorConfig instance
        
        Raises:
            ValueError: If configuration validation fails
        
        Requirements: 15.1, 15.4, 15.5, 15.6, 15.8, 15.9
        """
        # Read configuration from environment with defaults
        enabled = os.getenv(
            "NEURAL_TURN_DETECTOR_ENABLED",
            str(cls.DEFAULT_ENABLED)
        ).lower() in ("true", "1", "yes")
        
        confidence_threshold = float(
            os.getenv(
                "END_OF_TURN_CONFIDENCE_THRESHOLD",
                str(cls.DEFAULT_CONFIDENCE_THRESHOLD)
            )
        )
        
        min_turn_silence_ms = int(
            os.getenv(
                "MIN_TURN_SILENCE_MS",
                str(cls.DEFAULT_MIN_TURN_SILENCE_MS)
            )
        )
        
        max_turn_silence_ms = int(
            os.getenv(
                "MAX_TURN_SILENCE_MS",
                str(cls.DEFAULT_MAX_TURN_SILENCE_MS)
            )
        )
        
        health_check_interval_s = int(
            os.getenv(
                "NEURAL_TURN_DETECTOR_HEALTH_CHECK_INTERVAL_S",
                str(cls.DEFAULT_HEALTH_CHECK_INTERVAL_S)
            )
        )
        
        max_failures = int(
            os.getenv(
                "NEURAL_TURN_DETECTOR_MAX_FAILURES",
                str(cls.DEFAULT_MAX_FAILURES)
            )
        )
        
        try:
            config = cls(
                enabled=enabled,
                confidence_threshold=confidence_threshold,
                min_turn_silence_ms=min_turn_silence_ms,
                max_turn_silence_ms=max_turn_silence_ms,
                health_check_interval_s=health_check_interval_s,
                max_failures=max_failures
            )
            
            logger.info("Neural turn detector configuration loaded from environment")
            return config
        
        except ValueError as e:
            logger.error(f"Configuration validation failed: {e}")
            logger.warning("Using default configuration values")
            
            # Return default configuration on validation failure
            return cls()
    
    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            'enabled': self.enabled,
            'confidence_threshold': self.confidence_threshold,
            'min_turn_silence_ms': self.min_turn_silence_ms,
            'max_turn_silence_ms': self.max_turn_silence_ms,
            'health_check_interval_s': self.health_check_interval_s,
            'max_failures': self.max_failures
        }
    
    def log_configuration(self) -> None:
        """
        Log configuration details for debugging and monitoring.
        
        Requirements: 15.8, 15.9
        """
        logger.info("=" * 60)
        logger.info("Neural Turn Detector Configuration")
        logger.info("=" * 60)
        logger.info(f"Enabled: {self.enabled}")
        logger.info(f"Confidence Threshold: {self.confidence_threshold}")
        logger.info(f"Min Turn Silence: {self.min_turn_silence_ms}ms")
        logger.info(f"Max Turn Silence: {self.max_turn_silence_ms}ms")
        logger.info(f"Health Check Interval: {self.health_check_interval_s}s")
        logger.info(f"Max Failures Before Fallback: {self.max_failures}")
        logger.info("=" * 60)


def create_neural_turn_detector_config_from_env() -> NeuralTurnDetectorConfig:
    """
    Convenience function to create configuration from environment variables.
    
    Returns:
        NeuralTurnDetectorConfig instance
    
    Requirements: 15.1, 15.4, 15.5, 15.6, 15.8, 15.9
    """
    return NeuralTurnDetectorConfig.from_env()
