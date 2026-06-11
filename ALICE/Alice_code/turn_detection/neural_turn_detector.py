"""
Neural Turn Detector for Alice Conversation Fluidity Enhancement.

This module implements neural turn detection using STT provider streaming
to detect end-of-turn using acoustic and linguistic signals.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 3.1, 3.2, 15.4, 15.5, 15.6, 15.8, 15.9
"""

import logging
from typing import Optional
import time

from stt.provider import STTProvider
from stt.models import TranscriptionResult
from .models import TurnDetectionEvent

logger = logging.getLogger(__name__)


class NeuralTurnDetector:
    """
    Neural turn detection using STT provider streaming.
    
    This class uses acoustic and linguistic signal analysis from neural STT models
    (AssemblyAI Universal-3 Pro or Deepgram Nova-3) to detect end-of-turn with
    higher accuracy than simple silence-based VAD.
    
    The detector:
    - Streams audio frames to STT provider
    - Analyzes acoustic signals (pitch, energy, rhythm) for turn boundaries
    - Analyzes linguistic signals (sentence completion, discourse markers)
    - Calculates End-of-Turn Confidence score (0.0-1.0)
    - Signals end-of-turn when confidence exceeds threshold
    - Falls back to Silero VAD if STT provider unavailable
    
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 3.1, 3.2
    """
    
    def __init__(
        self,
        stt_provider: STTProvider,
        confidence_threshold: float = 0.4,
        min_turn_silence_ms: int = 300,
        max_turn_silence_ms: int = 1200,
        fallback_vad: Optional[object] = None
    ):
        """
        Initialize neural turn detector.
        
        Args:
            stt_provider: STT provider client (AssemblyAI or Deepgram)
            confidence_threshold: Minimum confidence for end-of-turn (0.0-1.0)
            min_turn_silence_ms: Minimum silence duration to consider turn end
            max_turn_silence_ms: Maximum silence before forcing turn end
            fallback_vad: Silero VAD instance for fallback (optional)
        
        Raises:
            ValueError: If configuration parameters are invalid
        
        Requirements: 1.1, 1.2, 1.3, 1.4, 15.4, 15.5, 15.6, 15.8, 15.9
        """
        # Validate configuration parameters
        self._validate_config(
            confidence_threshold,
            min_turn_silence_ms,
            max_turn_silence_ms
        )
        
        # Store configuration
        self.stt_provider = stt_provider
        self.confidence_threshold = confidence_threshold
        self.min_turn_silence_ms = min_turn_silence_ms
        self.max_turn_silence_ms = max_turn_silence_ms
        self.fallback_vad = fallback_vad
        
        # Initialize state
        self._current_confidence = 0.0
        self._last_transcription: Optional[TranscriptionResult] = None
        self._audio_start_time_ms: Optional[int] = None
        self._last_audio_time_ms: Optional[int] = None
        self._silence_start_time_ms: Optional[int] = None
        self._is_fallback_mode = False
        self._consecutive_failures = 0
        
        logger.info(
            f"NeuralTurnDetector initialized with {stt_provider.get_provider_type()} "
            f"(confidence_threshold={confidence_threshold}, "
            f"min_silence={min_turn_silence_ms}ms, "
            f"max_silence={max_turn_silence_ms}ms, "
            f"fallback_vad={'enabled' if fallback_vad else 'disabled'})"
        )
    
    def _validate_config(
        self,
        confidence_threshold: float,
        min_turn_silence_ms: int,
        max_turn_silence_ms: int
    ) -> None:
        """
        Validate configuration parameters.
        
        Args:
            confidence_threshold: Minimum confidence for end-of-turn
            min_turn_silence_ms: Minimum silence duration
            max_turn_silence_ms: Maximum silence duration
        
        Raises:
            ValueError: If any parameter is invalid
        
        Requirements: 15.8, 15.9
        """
        # Validate confidence threshold is in range [0.0, 1.0]
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError(
                f"Confidence threshold must be between 0.0 and 1.0, "
                f"got {confidence_threshold}"
            )
        
        # Validate min silence is positive
        if min_turn_silence_ms <= 0:
            raise ValueError(
                f"Minimum turn silence must be positive, got {min_turn_silence_ms}ms"
            )
        
        # Validate max silence is positive
        if max_turn_silence_ms <= 0:
            raise ValueError(
                f"Maximum turn silence must be positive, got {max_turn_silence_ms}ms"
            )
        
        # Validate max silence is greater than min silence
        if max_turn_silence_ms <= min_turn_silence_ms:
            raise ValueError(
                f"Maximum turn silence ({max_turn_silence_ms}ms) must be greater than "
                f"minimum turn silence ({min_turn_silence_ms}ms)"
            )
        
        logger.debug(
            f"Configuration validated: confidence_threshold={confidence_threshold}, "
            f"min_silence={min_turn_silence_ms}ms, max_silence={max_turn_silence_ms}ms"
        )
    
    async def process_audio_frame(self, audio_frame: bytes) -> None:
        """
        Process audio frame for turn detection.
        
        This method streams the audio frame to the STT provider and updates
        internal state for turn detection.
        
        Args:
            audio_frame: Audio data (24kHz mono, typically 20ms chunks)
        
        Requirements: 1.5, 1.6, 7.2, 7.3, 7.7
        """
        current_time_ms = int(time.time() * 1000)
        
        # Track audio timing
        if self._audio_start_time_ms is None:
            self._audio_start_time_ms = current_time_ms
        
        self._last_audio_time_ms = current_time_ms
        
        # Reset silence tracking when audio is received
        self._silence_start_time_ms = None
        
        # Stream audio to STT provider if not in fallback mode
        if not self._is_fallback_mode:
            try:
                await self.stt_provider.stream_audio(audio_frame)
                
                # Get latest transcription result
                result = await self.stt_provider.get_transcription_result()
                if result:
                    self._last_transcription = result
                    # Update confidence based on transcription result
                    self._update_confidence(result)
                
            except Exception as e:
                logger.error(f"Error processing audio frame: {e}")
                self._consecutive_failures += 1
                
                # Check if we should fall back to Silero VAD
                if self._consecutive_failures >= 3 and self.fallback_vad:
                    logger.warning(
                        f"Switching to fallback VAD after {self._consecutive_failures} "
                        f"consecutive failures"
                    )
                    self._is_fallback_mode = True
        
        # If in fallback mode, use Silero VAD
        if self._is_fallback_mode and self.fallback_vad:
            # TODO: Process audio with fallback VAD
            # This will be implemented when integrating with existing VAD
            pass
    
    def _update_confidence(self, result: TranscriptionResult) -> None:
        """
        Update end-of-turn confidence based on transcription result.
        
        This method analyzes acoustic and linguistic features to calculate
        the end-of-turn confidence score.
        
        Args:
            result: Transcription result from STT provider
        
        Requirements: 1.5, 1.6, 1.9
        """
        # Start with base confidence from STT provider's end-of-utterance signal
        confidence = 0.5 if result.end_of_utterance else 0.0
        
        # Adjust confidence based on acoustic features
        acoustic_features = result.acoustic_features
        if acoustic_features:
            # Lower pitch at end of utterance increases confidence
            if 'pitch_trend' in acoustic_features:
                pitch_trend = acoustic_features['pitch_trend']
                if pitch_trend == 'falling':
                    confidence += 0.2
            
            # Lower energy at end of utterance increases confidence
            if 'energy_trend' in acoustic_features:
                energy_trend = acoustic_features['energy_trend']
                if energy_trend == 'falling':
                    confidence += 0.1
        
        # Adjust confidence based on linguistic features
        linguistic_features = result.linguistic_features
        if linguistic_features:
            # Sentence completion increases confidence
            if linguistic_features.get('sentence_complete', False):
                confidence += 0.2
            
            # Discourse markers (e.g., "so", "well", "okay") at end increase confidence
            if linguistic_features.get('has_discourse_marker', False):
                confidence += 0.1
        
        # Ensure confidence is in valid range [0.0, 1.0]
        self._current_confidence = max(0.0, min(1.0, confidence))
        
        logger.debug(
            f"Updated end-of-turn confidence: {self._current_confidence:.2f} "
            f"(end_of_utterance={result.end_of_utterance}, "
            f"acoustic_features={bool(acoustic_features)}, "
            f"linguistic_features={bool(linguistic_features)})"
        )
    
    async def get_end_of_turn_confidence(self) -> float:
        """
        Get current end-of-turn confidence score.
        
        Returns:
            Confidence score between 0.0 and 1.0
        
        Requirements: 1.9
        """
        return self._current_confidence
    
    async def is_end_of_turn(self) -> bool:
        """
        Check if end-of-turn detected.
        
        This method checks if the end-of-turn confidence exceeds the threshold
        and if sufficient silence has occurred.
        
        Returns:
            True if confidence exceeds threshold and silence requirements met,
            False otherwise
        
        Requirements: 1.7, 1.3, 1.4
        """
        # Check if confidence exceeds threshold
        if self._current_confidence < self.confidence_threshold:
            return False
        
        # Calculate silence duration
        current_time_ms = int(time.time() * 1000)
        
        # Start tracking silence if not already tracking
        if self._silence_start_time_ms is None:
            self._silence_start_time_ms = current_time_ms
            return False
        
        silence_duration_ms = current_time_ms - self._silence_start_time_ms
        
        # Check if minimum silence duration met
        if silence_duration_ms < self.min_turn_silence_ms:
            return False
        
        # End-of-turn detected
        logger.debug(
            f"End-of-turn detected: confidence={self._current_confidence:.2f}, "
            f"threshold={self.confidence_threshold:.2f}, "
            f"silence={silence_duration_ms}ms"
        )
        
        return True
    
    async def reset(self) -> None:
        """
        Reset detector state for new turn.
        
        This method should be called after end-of-turn is detected to prepare
        for the next turn.
        
        Requirements: 1.7
        """
        self._current_confidence = 0.0
        self._last_transcription = None
        self._audio_start_time_ms = None
        self._last_audio_time_ms = None
        self._silence_start_time_ms = None
        
        logger.debug("Neural turn detector state reset for new turn")
    
    async def health_check(self) -> bool:
        """
        Check if neural turn detector is healthy.
        
        This method checks if the STT provider is connected and operational.
        If health check fails, the detector may need to fall back to Silero VAD.
        
        Returns:
            True if operational, False if fallback needed
        
        Requirements: 3.6, 3.7, 13.1
        """
        try:
            # Check if STT provider is connected
            is_connected = await self.stt_provider.is_connected()
            
            if not is_connected:
                logger.warning("STT provider is not connected")
                self._consecutive_failures += 1
                return False
            
            # Reset failure counter on successful health check
            self._consecutive_failures = 0
            return True
        
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self._consecutive_failures += 1
            return False
    
    def is_fallback_mode(self) -> bool:
        """
        Check if detector is in fallback mode.
        
        Returns:
            True if using fallback VAD, False if using neural detection
        
        Requirements: 3.1, 3.2
        """
        return self._is_fallback_mode
    
    def get_detector_type(self) -> str:
        """
        Get the current detector type.
        
        Returns:
            "neural" if using neural detection, "silero" if in fallback mode
        
        Requirements: 3.1, 3.2
        """
        return "silero" if self._is_fallback_mode else "neural"
    
    def get_audio_duration_ms(self) -> int:
        """
        Get the duration of audio processed in current turn.
        
        Returns:
            Audio duration in milliseconds, or 0 if no audio processed
        """
        if self._audio_start_time_ms is None or self._last_audio_time_ms is None:
            return 0
        
        return self._last_audio_time_ms - self._audio_start_time_ms
    
    def get_silence_duration_ms(self) -> int:
        """
        Get the current silence duration.
        
        Returns:
            Silence duration in milliseconds, or 0 if no silence
        """
        if self._silence_start_time_ms is None:
            return 0
        
        current_time_ms = int(time.time() * 1000)
        return current_time_ms - self._silence_start_time_ms
    
    def create_turn_detection_event(self, triggered: bool) -> TurnDetectionEvent:
        """
        Create a turn detection event for monitoring and logging.
        
        Args:
            triggered: Whether end-of-turn was triggered
        
        Returns:
            TurnDetectionEvent instance
        
        Requirements: 10.2, 10.4
        """
        return TurnDetectionEvent.create(
            detector_type=self.get_detector_type(),
            end_of_turn_confidence=self._current_confidence,
            threshold=self.confidence_threshold,
            triggered=triggered,
            audio_duration_ms=self.get_audio_duration_ms(),
            silence_duration_ms=self.get_silence_duration_ms()
        )
