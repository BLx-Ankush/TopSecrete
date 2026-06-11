"""
Data models for STT provider infrastructure.

This module defines data structures for transcription results and
related information from STT providers.

Requirements: 2.1, 2.2, 2.3, 2.4
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class TranscriptionResult:
    """
    Transcription result from STT provider with turn detection signals.
    
    This data model represents the output from STT providers (AssemblyAI or Deepgram)
    including transcribed text, confidence scores, and acoustic/linguistic features
    for neural turn detection.
    
    Attributes:
        text: Transcribed text from audio
        confidence: Transcription confidence score (0.0-1.0)
        end_of_utterance: End-of-utterance signal from STT provider
        is_final: Whether this is a final transcription result
        timestamp_ms: Timestamp in milliseconds
        acoustic_features: Acoustic features (pitch, energy, rhythm, etc.)
        linguistic_features: Linguistic features (sentence completion, discourse markers, etc.)
    
    Requirements: 2.1, 2.2, 2.3, 2.4
    """
    
    text: str
    confidence: float
    end_of_utterance: bool
    is_final: bool
    timestamp_ms: int
    acoustic_features: Dict[str, Any] = field(default_factory=dict)
    linguistic_features: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate transcription result data."""
        # Validate confidence is in valid range [0.0, 1.0]
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )
        
        # Validate timestamp is non-negative
        if self.timestamp_ms < 0:
            raise ValueError(
                f"Timestamp must be non-negative, got {self.timestamp_ms}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transcription result to dictionary."""
        return {
            'text': self.text,
            'confidence': self.confidence,
            'end_of_utterance': self.end_of_utterance,
            'is_final': self.is_final,
            'timestamp_ms': self.timestamp_ms,
            'acoustic_features': self.acoustic_features,
            'linguistic_features': self.linguistic_features
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranscriptionResult':
        """Create transcription result from dictionary."""
        return cls(
            text=data['text'],
            confidence=data['confidence'],
            end_of_utterance=data['end_of_utterance'],
            is_final=data['is_final'],
            timestamp_ms=data['timestamp_ms'],
            acoustic_features=data.get('acoustic_features', {}),
            linguistic_features=data.get('linguistic_features', {})
        )


@dataclass
class STTProviderConfig:
    """
    Configuration for STT provider.
    
    This data model encapsulates configuration parameters for STT providers
    including API credentials, audio format settings, and connection parameters.
    
    Attributes:
        provider_type: Type of STT provider ("assemblyai" or "deepgram")
        api_key: API key for authentication
        sample_rate: Audio sample rate in Hz (default: 24000)
        encoding: Audio encoding format (default: "pcm_s16le")
        channels: Number of audio channels (default: 1 for mono)
        connection_timeout_s: Connection timeout in seconds (default: 10)
        reconnect_attempts: Maximum reconnection attempts (default: 3)
        enable_end_of_utterance: Enable end-of-utterance detection (default: True)
    
    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 15.1, 15.3, 15.9
    """
    
    provider_type: str
    api_key: str
    sample_rate: int = 24000
    encoding: str = "pcm_s16le"
    channels: int = 1
    connection_timeout_s: int = 10
    reconnect_attempts: int = 3
    enable_end_of_utterance: bool = True
    
    def __post_init__(self):
        """Validate configuration parameters."""
        # Validate provider type
        valid_providers = ["assemblyai", "deepgram"]
        if self.provider_type not in valid_providers:
            raise ValueError(
                f"Invalid provider type: {self.provider_type}. "
                f"Must be one of {valid_providers}"
            )
        
        # Validate API key is not empty
        if not self.api_key or not self.api_key.strip():
            raise ValueError("API key cannot be empty")
        
        # Validate sample rate (24kHz for LiveKit audio pipeline)
        if self.sample_rate != 24000:
            raise ValueError(
                f"Sample rate must be 24000 Hz to match LiveKit audio pipeline, "
                f"got {self.sample_rate}"
            )
        
        # Validate channels (mono audio)
        if self.channels != 1:
            raise ValueError(
                f"Channels must be 1 (mono) to match LiveKit audio pipeline, "
                f"got {self.channels}"
            )
        
        # Validate connection timeout
        if self.connection_timeout_s <= 0:
            raise ValueError(
                f"Connection timeout must be positive, got {self.connection_timeout_s}"
            )
        
        # Validate reconnect attempts
        if self.reconnect_attempts < 0:
            raise ValueError(
                f"Reconnect attempts must be non-negative, got {self.reconnect_attempts}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'provider_type': self.provider_type,
            'api_key': self.api_key,
            'sample_rate': self.sample_rate,
            'encoding': self.encoding,
            'channels': self.channels,
            'connection_timeout_s': self.connection_timeout_s,
            'reconnect_attempts': self.reconnect_attempts,
            'enable_end_of_utterance': self.enable_end_of_utterance
        }
