"""
Deepgram Nova-3 provider implementation.

This module implements the STT provider interface for Deepgram's
Nova-3 model for neural turn detection.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 2.7, 2.8
"""

import asyncio
import json
import logging
import time
from typing import Optional
import websockets
from websockets.exceptions import WebSocketException

from .provider import STTProvider
from .models import TranscriptionResult, STTProviderConfig

logger = logging.getLogger(__name__)


class DeepgramProvider(STTProvider):
    """
    Deepgram Nova-3 implementation.
    
    This provider implements streaming transcription using Deepgram's
    Nova-3 model with end-of-utterance detection for neural turn
    detection in Alice's conversation fluidity enhancement.
    
    Features:
    - Real-time streaming transcription
    - End-of-utterance detection with endpointing
    - Acoustic and linguistic feature extraction
    - Connection pooling and automatic reconnection
    - Audio format validation (24kHz mono PCM)
    
    Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 2.7, 2.8
    """
    
    # Deepgram WebSocket endpoint
    WEBSOCKET_URL = "wss://api.deepgram.com/v1/listen"
    
    def __init__(self, config: STTProviderConfig):
        """
        Initialize Deepgram provider.
        
        Args:
            config: STT provider configuration with Deepgram API key
        
        Requirements: 2.1, 2.2, 2.6, 2.7
        """
        super().__init__(config)
        
        # Validate provider type
        if config.provider_type != "deepgram":
            raise ValueError(
                f"Invalid provider type for Deepgram: {config.provider_type}"
            )
        
        # Validate audio format matches LiveKit pipeline
        self.validate_audio_format(config.sample_rate, config.channels)
        
        # WebSocket connection
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        
        # Transcription result queue
        self._result_queue: asyncio.Queue = asyncio.Queue()
        
        # Connection state
        self._connected = False
        self._request_id: Optional[str] = None
        
        logger.info(
            f"Deepgram provider initialized "
            f"(sample_rate={config.sample_rate}Hz, model=Nova-3)"
        )
    
    async def connect(self) -> None:
        """
        Establish connection to Deepgram streaming service.
        
        This method:
        - Establishes WebSocket connection with API key authentication
        - Configures Nova-3 model for streaming
        - Enables end-of-utterance detection (endpointing)
        - Validates audio format (24kHz mono PCM)
        - Starts background task to receive transcription results
        
        Raises:
            ConnectionError: If connection fails after timeout
            ValueError: If audio format validation fails
        
        Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 2.7, 2.8
        """
        if self._connected:
            logger.warning("Already connected to Deepgram")
            return
        
        try:
            logger.info("Connecting to Deepgram streaming service...")
            
            # Build WebSocket URL with query parameters
            # Configure Nova-3 model with endpointing for turn detection
            params = {
                "model": "nova-3",
                "encoding": "linear16",  # PCM 16-bit
                "sample_rate": str(self.config.sample_rate),
                "channels": str(self.config.channels),
                "interim_results": "true",  # Enable partial transcripts
                "endpointing": "true",  # Enable end-of-utterance detection
                "utterance_end_ms": "300",  # 300ms silence for utterance end
                "vad_events": "true",  # Enable VAD events
                "punctuate": "true",  # Enable punctuation
            }
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{self.WEBSOCKET_URL}?{query_string}"
            
            # Establish WebSocket connection with timeout
            self._websocket = await asyncio.wait_for(
                websockets.connect(
                    url,
                    extra_headers={
                        "Authorization": f"Token {self.config.api_key}"
                    },
                    ping_interval=20,
                    ping_timeout=10
                ),
                timeout=self.config.connection_timeout_s
            )
            
            self._connected = True
            
            logger.info("Connected to Deepgram")
            
            # Start background task to receive transcription results
            self._receive_task = asyncio.create_task(self._receive_loop())
        
        except asyncio.TimeoutError:
            raise ConnectionError(
                f"Connection to Deepgram timed out after "
                f"{self.config.connection_timeout_s}s"
            )
        
        except WebSocketException as e:
            raise ConnectionError(f"WebSocket connection failed: {e}")
        
        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {e}")
            raise ConnectionError(f"Connection failed: {e}")
    
    async def stream_audio(self, audio_frame: bytes) -> None:
        """
        Stream audio frame to Deepgram.
        
        This method sends audio frames to Deepgram's streaming service
        in real-time for transcription and turn detection.
        
        Args:
            audio_frame: Audio data (24kHz mono PCM, typically 20ms chunks)
        
        Raises:
            ConnectionError: If not connected to Deepgram
            RuntimeError: If audio streaming fails
        
        Requirements: 2.1, 2.3, 2.7
        """
        if not self._connected or not self._websocket:
            raise ConnectionError("Not connected to Deepgram")
        
        try:
            # Send audio frame as binary message
            await self._websocket.send(audio_frame)
        
        except WebSocketException as e:
            logger.error(f"Failed to stream audio to Deepgram: {e}")
            self._connected = False
            raise RuntimeError(f"Audio streaming failed: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error streaming audio: {e}")
            raise RuntimeError(f"Audio streaming failed: {e}")
    
    async def get_transcription_result(self) -> Optional[TranscriptionResult]:
        """
        Get latest transcription result from Deepgram.
        
        This method retrieves transcription results from the result queue,
        which is populated by the background receive loop.
        
        Returns:
            TranscriptionResult with text, confidence, features, or None if no result
        
        Requirements: 2.1, 2.2, 2.3, 2.4
        """
        try:
            # Non-blocking get from queue
            result = self._result_queue.get_nowait()
            return result
        
        except asyncio.QueueEmpty:
            return None
    
    async def disconnect(self) -> None:
        """
        Close connection to Deepgram.
        
        This method:
        - Sends close frame to Deepgram
        - Closes WebSocket connection gracefully
        - Cancels background receive task
        - Cleans up resources
        
        Requirements: 2.8
        """
        if not self._connected:
            logger.warning("Not connected to Deepgram")
            return
        
        try:
            logger.info("Disconnecting from Deepgram...")
            
            # Send close frame (empty byte string signals end of stream)
            if self._websocket:
                await self._websocket.send(b"")
                await self._websocket.close()
            
            # Cancel receive task
            if self._receive_task and not self._receive_task.done():
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass
            
            self._connected = False
            self._websocket = None
            self._request_id = None
            
            logger.info("Disconnected from Deepgram")
        
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            self._connected = False
    
    async def is_connected(self) -> bool:
        """
        Check if connected to Deepgram.
        
        Returns:
            True if connected and operational, False otherwise
        
        Requirements: 2.8
        """
        return self._connected and self._websocket is not None
    
    async def _receive_loop(self) -> None:
        """
        Background task to receive transcription results from Deepgram.
        
        This method runs in the background and continuously receives
        transcription results from the WebSocket connection, parsing
        them into TranscriptionResult objects and adding them to the queue.
        """
        logger.info("Starting Deepgram receive loop")
        
        try:
            while self._connected and self._websocket:
                try:
                    # Receive message from WebSocket
                    message = await self._websocket.recv()
                    data = json.loads(message)
                    
                    # Check message type
                    if "channel" in data:
                        # Transcription result
                        result = self._parse_transcription_result(data)
                        if result:
                            await self._result_queue.put(result)
                    
                    elif data.get("type") == "Metadata":
                        # Metadata message (connection info)
                        self._request_id = data.get("request_id")
                        logger.debug(f"Deepgram request_id: {self._request_id}")
                    
                    elif data.get("type") == "UtteranceEnd":
                        # Utterance end event (explicit end-of-utterance signal)
                        logger.debug("Deepgram utterance end event received")
                        # This event is used by Neural Turn Detector
                    
                    elif data.get("type") == "SpeechStarted":
                        # Speech started event
                        logger.debug("Deepgram speech started event received")
                    
                    else:
                        logger.debug(f"Received message type: {data.get('type')}")
                
                except WebSocketException as e:
                    logger.error(f"WebSocket error in receive loop: {e}")
                    self._connected = False
                    break
                
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON message: {e}")
                    continue
        
        except asyncio.CancelledError:
            logger.info("Receive loop cancelled")
        
        except Exception as e:
            logger.error(f"Unexpected error in receive loop: {e}")
            self._connected = False
        
        finally:
            logger.info("Deepgram receive loop stopped")
    
    def _parse_transcription_result(self, data: dict) -> Optional[TranscriptionResult]:
        """
        Parse Deepgram transcription message into TranscriptionResult.
        
        Args:
            data: JSON data from Deepgram message
        
        Returns:
            TranscriptionResult or None if parsing fails
        """
        try:
            # Extract channel data
            channel = data.get("channel", {})
            alternatives = channel.get("alternatives", [])
            
            if not alternatives:
                return None
            
            # Get best alternative (highest confidence)
            best_alternative = alternatives[0]
            
            text = best_alternative.get("transcript", "")
            
            # Skip empty transcriptions
            if not text or not text.strip():
                return None
            
            confidence = best_alternative.get("confidence", 0.0)
            
            # Check if this is a final transcript
            is_final = data.get("is_final", False)
            
            # Deepgram provides explicit speech_final flag for end-of-utterance
            speech_final = data.get("speech_final", False)
            end_of_utterance = is_final and speech_final
            
            timestamp_ms = int(time.time() * 1000)
            
            # Extract acoustic features
            acoustic_features = {}
            
            # Duration information
            if "duration" in data:
                acoustic_features["duration"] = data["duration"]
            
            if "start" in data:
                acoustic_features["start"] = data["start"]
            
            # Extract linguistic features
            linguistic_features = {
                "word_count": len(text.split()),
            }
            
            # Add words with timestamps and confidence if available
            words = best_alternative.get("words", [])
            if words:
                linguistic_features["words"] = [
                    {
                        "word": w.get("word"),
                        "start": w.get("start"),
                        "end": w.get("end"),
                        "confidence": w.get("confidence"),
                        "punctuated_word": w.get("punctuated_word")
                    }
                    for w in words
                ]
            
            return TranscriptionResult(
                text=text,
                confidence=confidence,
                end_of_utterance=end_of_utterance,
                is_final=is_final,
                timestamp_ms=timestamp_ms,
                acoustic_features=acoustic_features,
                linguistic_features=linguistic_features
            )
        
        except Exception as e:
            logger.error(f"Failed to parse transcription result: {e}")
            return None
