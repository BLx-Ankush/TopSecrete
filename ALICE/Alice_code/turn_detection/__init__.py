"""
Turn Detection Module for Alice Conversation Fluidity Enhancement.

This module provides neural turn detection using STT provider streaming
to detect end-of-turn using acoustic and linguistic signals.

Components:
- NeuralTurnDetector: Main turn detection class using STT providers
- TurnDetectionEvent: Data model for turn detection events
- NeuralTurnDetectorConfig: Configuration management
- create_neural_turn_detector_config_from_env: Factory function for config

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 15.1, 15.4, 15.5, 15.6, 15.8, 15.9
"""

from .neural_turn_detector import NeuralTurnDetector
from .models import TurnDetectionEvent
from .config import (
    NeuralTurnDetectorConfig,
    create_neural_turn_detector_config_from_env
)

__all__ = [
    'NeuralTurnDetector',
    'TurnDetectionEvent',
    'NeuralTurnDetectorConfig',
    'create_neural_turn_detector_config_from_env',
]
