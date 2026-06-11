"""
Unified Data Models for Alice Conversation Fluidity Enhancement.

This module provides all dataclasses used across the neural turn detection
and adaptive interruption handling feature, including:
  - TranscriptionResult    — STT provider output with acoustic/linguistic features
  - TurnDetectionEvent     — Neural turn detector trigger events for monitoring
  - InterruptionEvent      — Interruption classifier classification events
  - LatencyMetrics         — Extended latency measurements for all new components
  - CostMetrics            — API usage and cost tracking per conversation

All models include serialization methods for logging, monitoring dashboard
export, and regression test playback.

Requirements: 10.2, 10.3, 11.1, 11.2, 12.1, 12.2
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# TranscriptionResult
# ---------------------------------------------------------------------------

@dataclass
class TranscriptionResult:
    """
    Transcription result from STT provider with turn detection signals.

    Carries the raw transcribed text alongside acoustic and linguistic feature
    dictionaries extracted by the STT provider, which feed directly into the
    End-of-Turn confidence calculation.

    Requirements: 2.1, 2.2, 2.3, 2.4
    """

    text: str                                    # Transcribed text
    confidence: float                            # Transcription confidence (0.0–1.0)
    end_of_utterance: bool                       # End-of-utterance signal from STT
    is_final: bool                               # Whether this is a final result
    timestamp_ms: int                            # Timestamp in milliseconds
    acoustic_features: Dict[str, Any] = field(default_factory=dict)
    """
    Acoustic features extracted by the STT provider.
    Expected keys: 'pitch_trend' ('falling'|'rising'|'flat'),
                   'energy_trend' ('falling'|'rising'|'flat'),
                   'speech_rate'  (words per minute, float)
    """
    linguistic_features: Dict[str, Any] = field(default_factory=dict)
    """
    Linguistic features extracted from the transcription.
    Expected keys: 'sentence_complete' (bool),
                   'has_discourse_marker' (bool),
                   'question_detected' (bool)
    """
    provider_type: str = "unknown"               # "assemblyai" | "deepgram" | "mock"
    audio_duration_ms: int = 0                   # Duration of audio chunk that produced this result

    # ------------------------------------------------------------------
    @classmethod
    def create(
        cls,
        text: str,
        confidence: float,
        end_of_utterance: bool,
        is_final: bool,
        acoustic_features: Optional[Dict[str, Any]] = None,
        linguistic_features: Optional[Dict[str, Any]] = None,
        provider_type: str = "unknown",
        audio_duration_ms: int = 0,
    ) -> "TranscriptionResult":
        """Factory method with auto-populated timestamp."""
        return cls(
            text=text,
            confidence=confidence,
            end_of_utterance=end_of_utterance,
            is_final=is_final,
            timestamp_ms=int(time.time() * 1000),
            acoustic_features=acoustic_features or {},
            linguistic_features=linguistic_features or {},
            provider_type=provider_type,
            audio_duration_ms=audio_duration_ms,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for logging and dashboard export."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptionResult":
        """Deserialize from dictionary."""
        return cls(**data)

    def is_valid(self) -> bool:
        """Validate that the result has sane values."""
        return (
            isinstance(self.text, str)
            and 0.0 <= self.confidence <= 1.0
            and isinstance(self.end_of_utterance, bool)
            and isinstance(self.is_final, bool)
            and self.timestamp_ms > 0
        )


# ---------------------------------------------------------------------------
# TurnDetectionEvent
# ---------------------------------------------------------------------------

@dataclass
class TurnDetectionEvent:
    """
    Turn detection event for monitoring and logging.

    Created each time the NeuralTurnDetector makes an end-of-turn decision
    (whether triggered or not). Supports post-hoc false trigger labeling for
    accuracy measurement.

    Requirements: 10.2, 10.4
    """

    event_id: str                                # Unique event ID (UUID)
    timestamp_ms: int                            # Event timestamp in milliseconds
    detector_type: str                           # "neural" | "silero"
    end_of_turn_confidence: float                # Confidence score (0.0–1.0)
    threshold: float                             # Threshold used for detection
    triggered: bool                              # Whether end-of-turn was triggered
    audio_duration_ms: int                       # Duration of user audio in ms
    silence_duration_ms: int                     # Duration of silence before trigger
    is_false_trigger: bool = False               # Labeled post-hoc by caller
    conversation_id: str = ""                    # Conversation / session identifier
    stt_text: str = ""                           # Transcription text at time of event
    fallback_reason: str = ""                    # Non-empty if detector fell back to Silero

    # ------------------------------------------------------------------
    @classmethod
    def create(
        cls,
        detector_type: str,
        end_of_turn_confidence: float,
        threshold: float,
        triggered: bool,
        audio_duration_ms: int,
        silence_duration_ms: int,
        conversation_id: str = "",
        stt_text: str = "",
        fallback_reason: str = "",
    ) -> "TurnDetectionEvent":
        """Factory method with auto-generated ID and timestamp."""
        return cls(
            event_id=str(uuid.uuid4()),
            timestamp_ms=int(time.time() * 1000),
            detector_type=detector_type,
            end_of_turn_confidence=end_of_turn_confidence,
            threshold=threshold,
            triggered=triggered,
            audio_duration_ms=audio_duration_ms,
            silence_duration_ms=silence_duration_ms,
            conversation_id=conversation_id,
            stt_text=stt_text,
            fallback_reason=fallback_reason,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for dashboard export."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TurnDetectionEvent":
        """Deserialize from dictionary."""
        return cls(**data)

    def mark_false_trigger(self) -> None:
        """Post-hoc label this event as a false trigger."""
        self.is_false_trigger = True


# ---------------------------------------------------------------------------
# InterruptionEvent
# ---------------------------------------------------------------------------

@dataclass
class InterruptionEvent:
    """
    Interruption classification event for monitoring and logging.

    Created each time the InterruptionClassifier processes audio input detected
    during Alice's speech output. Supports post-hoc false interruption labeling.

    Requirements: 10.3, 10.5
    """

    event_id: str                                # Unique event ID (UUID)
    timestamp_ms: int                            # Event timestamp in milliseconds
    classification: str                          # "genuine_interruption" | "noise" | "background_sound"
    audio_duration_ms: float                     # Duration of interrupting audio in ms
    audio_energy: float                          # RMS energy level (0.0–1.0)
    spectral_features: Dict[str, Any] = field(default_factory=dict)
    """
    Spectral characteristics of the interrupting audio.
    Keys: 'centroid_hz' (float), 'rolloff_hz' (float), 'bandwidth_hz' (float)
    """
    temporal_features: Dict[str, Any] = field(default_factory=dict)
    """
    Temporal patterns of the interrupting audio.
    Keys: 'zero_crossing_rate' (float), 'rhythm_regularity' (float)
    """
    action_taken: str = ""                       # "cancel_response" | "continue_response" | "ignore"
    is_false_interruption: bool = False          # Labeled post-hoc
    conversation_id: str = ""                    # Conversation / session identifier
    classifier_latency_ms: float = 0.0          # Time taken to produce classification

    # ------------------------------------------------------------------
    @classmethod
    def create(
        cls,
        classification: str,
        audio_duration_ms: float,
        audio_energy: float,
        spectral_features: Optional[Dict[str, Any]] = None,
        temporal_features: Optional[Dict[str, Any]] = None,
        action_taken: str = "",
        conversation_id: str = "",
        classifier_latency_ms: float = 0.0,
    ) -> "InterruptionEvent":
        """Factory method with auto-generated ID and timestamp."""
        return cls(
            event_id=str(uuid.uuid4()),
            timestamp_ms=int(time.time() * 1000),
            classification=classification,
            audio_duration_ms=audio_duration_ms,
            audio_energy=audio_energy,
            spectral_features=spectral_features or {},
            temporal_features=temporal_features or {},
            action_taken=action_taken,
            conversation_id=conversation_id,
            classifier_latency_ms=classifier_latency_ms,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for dashboard export."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterruptionEvent":
        """Deserialize from dictionary."""
        return cls(**data)

    def mark_false_interruption(self) -> None:
        """Post-hoc label this event as a false interruption."""
        self.is_false_interruption = True


# ---------------------------------------------------------------------------
# FluidityLatencyMetrics  (extends the existing LatencyMetrics concept)
# ---------------------------------------------------------------------------

@dataclass
class FluidityLatencyMetrics:
    """
    Extended latency measurements for the fluidity enhancement components.

    Captures processing time for each new pipeline stage added by this feature,
    alongside the existing VAD/API/TTS measurements tracked in latency_monitor.py.

    Requirements: 11.1, 11.2, 11.3, 11.4
    """

    conversation_id: str                                    # Conversation identifier
    timestamp_ms: int                                       # Measurement timestamp
    neural_turn_detector_latency_ms: float = 0.0           # NeuralTurnDetector processing time
    interruption_classifier_latency_ms: float = 0.0        # InterruptionClassifier processing time
    stt_provider_latency_ms: float = 0.0                   # STT provider transcription round-trip
    end_to_end_turn_detection_latency_ms: float = 0.0      # Total: audio-in → end-of-turn signal
    vad_trigger_time_ms: float = 0.0                       # Existing: end-of-speech → trigger
    total_response_time_ms: float = 0.0                    # Existing: end-of-speech → Alice speaks

    # ------------------------------------------------------------------
    @classmethod
    def create(cls, conversation_id: str) -> "FluidityLatencyMetrics":
        """Factory with auto-populated timestamp."""
        return cls(
            conversation_id=conversation_id,
            timestamp_ms=int(time.time() * 1000),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging."""
        return asdict(self)

    def meets_latency_targets(self) -> Dict[str, bool]:
        """Check which latency targets are met."""
        return {
            "neural_turn_detector_ok": self.neural_turn_detector_latency_ms <= 400,
            "interruption_classifier_ok": self.interruption_classifier_latency_ms <= 100,
            "stt_provider_ok": self.stt_provider_latency_ms <= 300,
            "total_response_ok": self.total_response_time_ms <= 400,
        }


# ---------------------------------------------------------------------------
# CostMetrics
# ---------------------------------------------------------------------------

@dataclass
class CostMetrics:
    """
    Cost measurements per conversation for cost monitoring.

    Tracks STT provider and Gemini API usage to calculate total cost per
    agent-minute and compare against the Felicia baseline ($0.090/agent-min).

    Requirements: 12.1, 12.2
    """

    conversation_id: str                    # Conversation identifier
    timestamp_ms: int                       # Measurement timestamp
    stt_audio_minutes: float = 0.0          # STT provider audio minutes processed
    gemini_agent_minutes: float = 0.0       # Gemini Multimodal Live API agent minutes
    stt_cost: float = 0.0                   # STT provider cost in USD
    gemini_cost: float = 0.0               # Gemini API cost in USD
    total_cost: float = 0.0               # Total cost in USD
    cost_per_agent_minute: float = 0.0    # Total cost / gemini_agent_minutes
    felicia_baseline_cost: float = 0.090  # Felicia baseline $/agent-minute
    cost_savings: float = 0.0             # (felicia_baseline - alice_cost) * agent_minutes

    # ------------------------------------------------------------------
    @classmethod
    def create(cls, conversation_id: str) -> "CostMetrics":
        """Factory with auto-populated timestamp."""
        return cls(
            conversation_id=conversation_id,
            timestamp_ms=int(time.time() * 1000),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging and dashboard."""
        return asdict(self)

    def is_within_budget(self, target: float = 0.030) -> bool:
        """Check whether cost_per_agent_minute is within target."""
        return round(self.cost_per_agent_minute, 6) <= target

    def get_savings_percentage(self) -> float:
        """Calculate savings vs Felicia as a percentage."""
        if self.felicia_baseline_cost == 0:
            return 0.0
        return ((self.felicia_baseline_cost - self.cost_per_agent_minute)
                / self.felicia_baseline_cost) * 100


# ---------------------------------------------------------------------------
# FallbackEvent  (for Property 9 logging)
# ---------------------------------------------------------------------------

@dataclass
class FallbackEvent:
    """
    Fallback event logged whenever the NeuralTurnDetector falls back to Silero VAD.

    Every fallback event MUST include a reason code and timestamp (Property 9).

    Requirements: 3.3, 13.1
    """

    event_id: str
    timestamp_ms: int
    reason_code: str                        # e.g. "STT_CONNECTION_LOST", "HEALTH_CHECK_FAILED"
    reason_details: str = ""               # Human-readable details
    conversation_id: str = ""
    consecutive_failures: int = 0          # How many failures triggered the fallback
    restored: bool = False                 # Set to True when neural detection restored

    # ------------------------------------------------------------------
    REASON_STT_CONNECTION_LOST = "STT_CONNECTION_LOST"
    REASON_HEALTH_CHECK_FAILED = "HEALTH_CHECK_FAILED"
    REASON_INITIALIZATION_FAILED = "INITIALIZATION_FAILED"
    REASON_AUDIO_FORMAT_ERROR = "AUDIO_FORMAT_ERROR"
    REASON_RATE_LIMIT = "RATE_LIMIT_EXCEEDED"
    REASON_AUTH_ERROR = "AUTH_ERROR"

    @classmethod
    def create(
        cls,
        reason_code: str,
        reason_details: str = "",
        conversation_id: str = "",
        consecutive_failures: int = 0,
    ) -> "FallbackEvent":
        return cls(
            event_id=str(uuid.uuid4()),
            timestamp_ms=int(time.time() * 1000),
            reason_code=reason_code,
            reason_details=reason_details,
            conversation_id=conversation_id,
            consecutive_failures=consecutive_failures,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def mark_restored(self) -> None:
        self.restored = True
