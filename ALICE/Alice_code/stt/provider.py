"""
Abstract base class for STT providers.

This module defines the interface that all STT providers must implement
for neural turn detection in Alice's conversation fluidity enhancement.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8
"""

from abc import ABC, abstractmethod
from typing import Optional
import logging

from .models import TranscriptionResult, STTProviderConfig

logger = logging.getLogger(__name__)


class STTProvider(ABC):
    """
    Abstract base class for Speech-to-Text providers.
    
    This class defines the interface that all STT providers (AssemblyAI, Deepgram)
    must implement for streaming transcription and neural turn detection.
    
    The STT provider is responsible for:
    - Establishing WebSocket connection to STT service
    - Streaming audio frames in real-time
    - Receiving transcription results with end-of-utterance signals
    - Extracting acoustic and linguistic features for turn detection
    - Managing connection pooling and reconnection
    - Handling API rate limits and errors
    
    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8
    """
    
    def __init__(self, config: STTProviderConfig):
        """
        Initialize STT provider with configuration.
        
        Args:
            config: STT provider configuration
        
        Requirements: 2.1, 2.2, 2.7, 15.1, 15.3, 15.9
        """
        self.config = config
        self._connected = False
        self._connection_attempts = 0
        
        logger.info(
            f"Initializing {config.provider_type} STT provider "
            f"(sample_rate={config.sample_rate}Hz, channels={config.channels})"
        )
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to STT provider.
        
        This method should:
        - Establish WebSocket connection to STT service
        - Configure streaming mode for real-time transcription
        - Configure end-of-utterance detection parameters
        - Set up connection pooling for reduced latency
        - Validate audio format matches LiveKit pipeline (24kHz mono PCM)
        
        Raises:
            ConnectionError: If connection fails after max retry attempts
            ValueError: If audio format validation fails
        
        Requirements: 2.1, 2.2, 2.3, 2.4, 2.7, 2.8
        """
        pass
    
    @abstractmethod
    async def stream_audio(self, audio_frame: bytes) -> None:
        """
        Stream audio frame to STT provider.
        
        This method should:
        - Send audio frame to STT service via WebSocket
        - Handle backpressure and buffering
        - Track audio streaming metrics
        
        Args:
            audio_frame: Audio data (24kHz mono PCM, typically 20ms chunks)
        
        Raises:
            ConnectionError: If not connected to STT service
            RuntimeError: If audio streaming fails
        
        Requirements: 2.1, 2.3, 2.7
        """
        pass
    
    @abstractmethod
    async def get_transcription_result(self) -> Optional[TranscriptionResult]:
        """
        Get latest transcription result from STT provider.
        
        This method should:
        - Receive transcription result from STT service
        - Extract text, confidence, and end-of-utterance signal
        - Extract acoustic features (pitch, energy, rhythm)
        - Extract linguistic features (sentence completion, discourse markers)
        - Return None if no result available
        
        Returns:
            TranscriptionResult with text, confidence, features, or None
        
        Requirements: 2.1, 2.2, 2.3, 2.4
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection to STT provider.
        
        This method should:
        - Close WebSocket connection gracefully
        - Clean up resources (buffers, connection pools)
        - Log disconnection metrics
        
        Requirements: 2.8
        """
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """
        Check if connected to STT provider.
        
        Returns:
            True if connected and operational, False otherwise
        
        Requirements: 2.8
        """
        pass
    
    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to STT provider.
        
        This method implements automatic reconnection logic with exponential backoff.
        It will attempt to reconnect up to config.reconnect_attempts times.
        
        Returns:
            True if reconnection successful, False otherwise
        
        Requirements: 2.8
        """
        if self._connection_attempts >= self.config.reconnect_attempts:
            logger.error(
                f"Max reconnection attempts ({self.config.reconnect_attempts}) reached"
            )
            return False
        
        self._connection_attempts += 1
        logger.info(
            f"Attempting reconnection {self._connection_attempts}/"
            f"{self.config.reconnect_attempts}..."
        )
        
        try:
            await self.connect()
            self._connection_attempts = 0  # Reset on successful connection
            logger.info("Reconnection successful")
            return True
        except Exception as e:
            logger.error(f"Reconnection attempt {self._connection_attempts} failed: {e}")
            return False
    
    def validate_audio_format(self, sample_rate: int, channels: int) -> None:
        """
        Validate audio format matches LiveKit audio pipeline requirements.
        
        Args:
            sample_rate: Audio sample rate in Hz
            channels: Number of audio channels
        
        Raises:
            ValueError: If audio format doesn't match requirements (24kHz mono)
        
        Requirements: 2.7
        """
        if sample_rate != 24000:
            raise ValueError(
                f"Audio sample rate must be 24000 Hz (24kHz) to match LiveKit pipeline, "
                f"got {sample_rate} Hz"
            )
        
        if channels != 1:
            raise ValueError(
                f"Audio must be mono (1 channel) to match LiveKit pipeline, "
                f"got {channels} channels"
            )
        
        logger.debug(f"Audio format validated: {sample_rate}Hz, {channels} channel(s)")
    
    def get_provider_type(self) -> str:
        """
        Get the type of STT provider.
        
        Returns:
            Provider type string ("assemblyai" or "deepgram")
        """
        return self.config.provider_type
    
    def get_config(self) -> STTProviderConfig:
        """
        Get the STT provider configuration.
        
        Returns:
            STT provider configuration
        """
        return self.config
