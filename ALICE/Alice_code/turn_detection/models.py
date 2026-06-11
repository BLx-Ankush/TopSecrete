"""
Data models for turn detection.

This module defines data structures for turn detection events and
related information.

Requirements: 10.2, 10.4
"""

from dataclasses import dataclass, field
from typing import Dict, Any
import uuid
import time


@dataclass
class TurnDetectionEvent:
    """
    Turn detection event for monitoring and logging.
    
    This data model represents a turn detection event including confidence scores,
    thresholds, and metadata for monitoring and debugging.
    
    Attributes:
        event_id: Unique event identifier
        timestamp_ms: Event timestamp in milliseconds
        detector_type: Type of detector ("neural" or "silero")
        end_of_turn_confidence: Confidence score (0.0-1.0)
        threshold: Threshold used for detection
        triggered: Whether end-of-turn was triggered
        audio_duration_ms: Duration of user audio in milliseconds
        silence_duration_ms: Duration of silence before trigger in milliseconds
        is_false_trigger: Whether this was a false trigger (labeled post-hoc)
    
    Requirements: 10.2, 10.4
    """
    
    event_id: str
    timestamp_ms: int
    detector_type: str
    end_of_turn_confidence: float
    threshold: float
    triggered: bool
    audio_duration_ms: int
    silence_duration_ms: int
    is_false_trigger: bool = False
    
    def __post_init__(self):
        """Validate turn detection event data."""
        # Validate detector type
        valid_types = ["neural", "silero"]
        if self.detector_type not in valid_types:
            raise ValueError(
                f"Detector type must be one of {valid_types}, got {self.detector_type}"
            )
        
        # Validate confidence is in valid range [0.0, 1.0]
        if not 0.0 <= self.end_of_turn_confidence <= 1.0:
            raise ValueError(
                f"End-of-turn confidence must be between 0.0 and 1.0, "
                f"got {self.end_of_turn_confidence}"
            )
        
        # Validate threshold is in valid range [0.0, 1.0]
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError(
                f"Threshold must be between 0.0 and 1.0, got {self.threshold}"
            )
        
        # Validate timestamp is non-negative
        if self.timestamp_ms < 0:
            raise ValueError(
                f"Timestamp must be non-negative, got {self.timestamp_ms}"
            )
        
        # Validate durations are non-negative
        if self.audio_duration_ms < 0:
            raise ValueError(
                f"Audio duration must be non-negative, got {self.audio_duration_ms}"
            )
        
        if self.silence_duration_ms < 0:
            raise ValueError(
                f"Silence duration must be non-negative, got {self.silence_duration_ms}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert turn detection event to dictionary."""
        return {
            'event_id': self.event_id,
            'timestamp_ms': self.timestamp_ms,
            'detector_type': self.detector_type,
            'end_of_turn_confidence': self.end_of_turn_confidence,
            'threshold': self.threshold,
            'triggered': self.triggered,
            'audio_duration_ms': self.audio_duration_ms,
            'silence_duration_ms': self.silence_duration_ms,
            'is_false_trigger': self.is_false_trigger
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TurnDetectionEvent':
        """Create turn detection event from dictionary."""
        return cls(
            event_id=data['event_id'],
            timestamp_ms=data['timestamp_ms'],
            detector_type=data['detector_type'],
            end_of_turn_confidence=data['end_of_turn_confidence'],
            threshold=data['threshold'],
            triggered=data['triggered'],
            audio_duration_ms=data['audio_duration_ms'],
            silence_duration_ms=data['silence_duration_ms'],
            is_false_trigger=data.get('is_false_trigger', False)
        )
    
    @classmethod
    def create(
        cls,
        detector_type: str,
        end_of_turn_confidence: float,
        threshold: float,
        triggered: bool,
        audio_duration_ms: int,
        silence_duration_ms: int,
        is_false_trigger: bool = False
    ) -> 'TurnDetectionEvent':
        """
        Create a new turn detection event with auto-generated ID and timestamp.
        
        Args:
            detector_type: Type of detector ("neural" or "silero")
            end_of_turn_confidence: Confidence score (0.0-1.0)
            threshold: Threshold used for detection
            triggered: Whether end-of-turn was triggered
            audio_duration_ms: Duration of user audio in milliseconds
            silence_duration_ms: Duration of silence before trigger in milliseconds
            is_false_trigger: Whether this was a false trigger
        
        Returns:
            TurnDetectionEvent instance
        """
        return cls(
            event_id=str(uuid.uuid4()),
            timestamp_ms=int(time.time() * 1000),
            detector_type=detector_type,
            end_of_turn_confidence=end_of_turn_confidence,
            threshold=threshold,
            triggered=triggered,
            audio_duration_ms=audio_duration_ms,
            silence_duration_ms=silence_duration_ms,
            is_false_trigger=is_false_trigger
        )
