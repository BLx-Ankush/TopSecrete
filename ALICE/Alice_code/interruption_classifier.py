"""
Interruption Classifier for Alice Conversation Fluidity Enhancement.

Classifies audio input detected during Alice's speech as:
  - genuine_interruption  → User is speaking, cancel Alice's current response
  - noise                 → Short/transient sound (<200ms), continue response
  - background_sound      → Low-energy ambient sound, ignore and continue

Classification algorithm:
  1. Duration check  — if audio < 200ms → noise (Property 6)
  2. Energy check    — if RMS energy < threshold → background_sound (Property 7)
  3. Spectral + temporal analysis → genuine_interruption vs background_sound

All classifications are produced within 100ms (async timeout enforced).
Fallback: on any failure → basic interruption handling (stop on any audio).

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7,
              6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7,
              7.4, 7.5, 7.6, 7.8, 13.2, 13.4, 13.5, 15.2
"""

from __future__ import annotations

import asyncio
import logging
import struct
import time
from enum import Enum
from typing import Dict, Optional, Tuple

import numpy as np

from fluidity_models import InterruptionEvent
from fluidity_error_handler import FluidityErrorHandler, get_error_handler

logger = logging.getLogger(__name__)

# Audio format constants (LiveKit pipeline — 24kHz mono PCM s16le)
SAMPLE_RATE = 24000
BYTES_PER_SAMPLE = 2          # s16le
SAMPLES_PER_MS = SAMPLE_RATE / 1000.0   # 24 samples per ms


def _pcm_to_float(audio_frame: bytes) -> np.ndarray:
    """Convert raw PCM s16le bytes to normalised float32 array [-1.0, 1.0]."""
    n_samples = len(audio_frame) // BYTES_PER_SAMPLE
    samples = struct.unpack(f"<{n_samples}h", audio_frame[:n_samples * BYTES_PER_SAMPLE])
    arr = np.array(samples, dtype=np.float32) / 32768.0
    return arr


def _duration_ms(audio_frame: bytes) -> float:
    """Return duration in milliseconds for a PCM s16le byte buffer."""
    n_samples = len(audio_frame) // BYTES_PER_SAMPLE
    return n_samples / SAMPLES_PER_MS


# ---------------------------------------------------------------------------
# Classification enum
# ---------------------------------------------------------------------------

class Classification(str, Enum):
    """
    Interruption classification result.

    Every audio input MUST produce exactly one of these values (Property 5).
    """
    GENUINE_INTERRUPTION = "genuine_interruption"
    NOISE = "noise"
    BACKGROUND_SOUND = "background_sound"


# ---------------------------------------------------------------------------
# Interruption Classifier
# ---------------------------------------------------------------------------

class InterruptionClassifier:
    """
    Classify audio input detected during Alice's speech output.

    The classifier uses a cascaded rule system:
      Rule 1 (duration)  → short clips are noise
      Rule 2 (energy)    → quiet clips are background
      Rule 3 (spectral)  → human-speech frequencies vs other
      Rule 4 (temporal)  → zero-crossing rate typical of voiced speech

    Produces exactly one Classification for every valid audio input.
    Falls back to basic interruption handling (treat as genuine) on error.

    Requirements: 5.1–5.7, 6.1–6.7, 13.2, 13.4, 13.5, 15.2
    """

    # Speech spectral ranges (Hz)
    SPEECH_CENTROID_MIN_HZ = 200
    SPEECH_CENTROID_MAX_HZ = 3400

    # Zero-crossing rate range for voiced speech (per second)
    VOICED_ZCR_MIN = 50
    VOICED_ZCR_MAX = 200

    def __init__(
        self,
        min_interruption_duration_ms: int = 200,
        speech_energy_threshold: float = 0.02,
        classification_timeout_ms: int = 100,
        fallback_enabled: bool = True,
        conversation_id: str = "",
        error_handler: Optional[FluidityErrorHandler] = None,
    ):
        """
        Initialize the InterruptionClassifier.

        Args:
            min_interruption_duration_ms: Audio shorter than this → noise (Property 6)
            speech_energy_threshold:      RMS below this → background_sound (Property 7)
            classification_timeout_ms:    Max time allowed for classify_audio()
            fallback_enabled:             Treat as genuine interruption on failure
            conversation_id:              For error logging
            error_handler:                Optional shared FluidityErrorHandler

        Requirements: 5.1, 6.1, 6.2, 6.3, 6.4, 15.2
        """
        self.min_interruption_duration_ms = min_interruption_duration_ms
        self.speech_energy_threshold = speech_energy_threshold
        self.classification_timeout_ms = classification_timeout_ms
        self.fallback_enabled = fallback_enabled
        self.conversation_id = conversation_id
        self._error_handler = error_handler or get_error_handler(conversation_id)

        self._initialized = False
        self._init_error: Optional[Exception] = None

        self._validate_config()

        try:
            self._initialized = True
            logger.info(
                f"[InterruptionClassifier] Initialized "
                f"(min_dur={min_interruption_duration_ms}ms, "
                f"energy_thr={speech_energy_threshold}, "
                f"timeout={classification_timeout_ms}ms, "
                f"fallback={fallback_enabled})"
            )
        except Exception as exc:
            self._init_error = exc
            self._error_handler.handle_classifier_init_failure(exc)
            logger.error(
                f"[InterruptionClassifier] Initialization failed: {exc}. "
                f"Will use fallback mode."
            )

    def _validate_config(self) -> None:
        if self.min_interruption_duration_ms <= 0:
            raise ValueError(
                f"min_interruption_duration_ms must be positive, "
                f"got {self.min_interruption_duration_ms}"
            )
        if not 0.0 <= self.speech_energy_threshold <= 1.0:
            raise ValueError(
                f"speech_energy_threshold must be in [0,1], "
                f"got {self.speech_energy_threshold}"
            )
        if self.classification_timeout_ms <= 0:
            raise ValueError(
                f"classification_timeout_ms must be positive, "
                f"got {self.classification_timeout_ms}"
            )

    # ------------------------------------------------------------------
    # Feature extraction methods
    # ------------------------------------------------------------------

    def _analyze_duration(self, audio_frame: bytes) -> float:
        """
        Analyze audio duration in milliseconds.

        Requirements: 6.1
        """
        return _duration_ms(audio_frame)

    def _analyze_energy(self, audio_frame: bytes) -> float:
        """
        Compute RMS energy of audio frame, normalised to [0.0, 1.0].

        Requirements: 6.2
        """
        if len(audio_frame) < BYTES_PER_SAMPLE:
            return 0.0
        samples = _pcm_to_float(audio_frame)
        if len(samples) == 0:
            return 0.0
        rms = float(np.sqrt(np.mean(samples ** 2)))
        return max(0.0, min(1.0, rms))

    def _analyze_spectral_characteristics(self, audio_frame: bytes) -> Dict[str, float]:
        """
        Compute spectral features using numpy FFT.

        Returns:
            centroid_hz:  Spectral centroid (energy-weighted mean frequency)
            rolloff_hz:   Frequency below which 85% of energy is concentrated
            bandwidth_hz: Spectral bandwidth (weighted std-dev around centroid)

        Requirements: 6.3
        """
        samples = _pcm_to_float(audio_frame)
        n = len(samples)
        if n < 8:
            return {"centroid_hz": 0.0, "rolloff_hz": 0.0, "bandwidth_hz": 0.0}

        # FFT — take one-sided spectrum
        fft_mag = np.abs(np.fft.rfft(samples))
        freqs = np.fft.rfftfreq(n, d=1.0 / SAMPLE_RATE)
        power = fft_mag ** 2
        total_power = float(np.sum(power))

        if total_power == 0:
            return {"centroid_hz": 0.0, "rolloff_hz": 0.0, "bandwidth_hz": 0.0}

        # Spectral centroid
        centroid = float(np.sum(freqs * power) / total_power)

        # Spectral rolloff (85% energy point)
        cumulative = np.cumsum(power)
        rolloff_idx = int(np.searchsorted(cumulative, 0.85 * total_power))
        rolloff_idx = min(rolloff_idx, len(freqs) - 1)
        rolloff = float(freqs[rolloff_idx])

        # Spectral bandwidth
        bandwidth = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * power) / total_power))

        return {
            "centroid_hz": centroid,
            "rolloff_hz": rolloff,
            "bandwidth_hz": bandwidth,
        }

    def _analyze_temporal_patterns(self, audio_frame: bytes) -> Dict[str, float]:
        """
        Compute temporal features: zero-crossing rate and rhythm regularity.

        Zero-crossing rate (ZCR) indicates voiced speech when in [50, 200]/sec.
        Higher ZCR suggests unvoiced fricatives or noise.

        Requirements: 6.4
        """
        samples = _pcm_to_float(audio_frame)
        n = len(samples)
        if n < 2:
            return {"zero_crossing_rate": 0.0, "rhythm_regularity": 0.0}

        # Zero-crossing rate (per second)
        signs = np.sign(samples)
        signs[signs == 0] = 1  # treat zero as positive to avoid false crossings
        crossings = float(np.sum(np.abs(np.diff(signs)) > 0))
        duration_s = n / SAMPLE_RATE
        zcr = crossings / duration_s if duration_s > 0 else 0.0

        # Rhythm regularity — variance of zero-crossing inter-event intervals
        crossing_indices = np.where(np.abs(np.diff(signs)) > 0)[0]
        if len(crossing_indices) > 1:
            intervals = np.diff(crossing_indices).astype(float)
            regularity = float(1.0 / (1.0 + np.std(intervals)))
        else:
            regularity = 0.0

        return {
            "zero_crossing_rate": zcr,
            "rhythm_regularity": regularity,
        }

    # ------------------------------------------------------------------
    # Speech detection logic
    # ------------------------------------------------------------------

    def _is_speech_spectral(self, spectral: Dict[str, float]) -> bool:
        """
        Return True if spectral features are consistent with human speech.

        Human voiced speech:  centroid typically 200–3400 Hz
        Human unvoiced speech: centroid 1000–5000 Hz (fricatives, etc.)
        Noise: wide-band, centroid can be anything
        """
        centroid = spectral.get("centroid_hz", 0.0)
        rolloff = spectral.get("rolloff_hz", 0.0)
        # Centroid in speech range AND rolloff < 4kHz (speech is band-limited)
        return (self.SPEECH_CENTROID_MIN_HZ <= centroid <= self.SPEECH_CENTROID_MAX_HZ
                and rolloff < 4500)

    def _is_speech_temporal(self, temporal: Dict[str, float]) -> bool:
        """
        Return True if temporal features are consistent with voiced speech.

        Voiced speech has ZCR in [VOICED_ZCR_MIN, VOICED_ZCR_MAX].
        """
        zcr = temporal.get("zero_crossing_rate", 0.0)
        return self.VOICED_ZCR_MIN <= zcr <= self.VOICED_ZCR_MAX

    # ------------------------------------------------------------------
    # Core classification
    # ------------------------------------------------------------------

    async def classify_audio(self, audio_frame: bytes) -> Classification:
        """
        Classify audio input during Alice's speech.

        Produces exactly one Classification from
        {GENUINE_INTERRUPTION, NOISE, BACKGROUND_SOUND} (Property 5).
        Enforces classification_timeout_ms limit.

        Args:
            audio_frame: Raw PCM s16le bytes at 24kHz mono

        Returns:
            Classification result

        Requirements: 5.2, 5.6, 6.5, 6.6, 6.7
        """
        # If classifier failed to initialize, use fallback
        if not self._initialized:
            logger.warning(
                "[InterruptionClassifier] Not initialized — using fallback (genuine interruption)"
            )
            return Classification.GENUINE_INTERRUPTION

        start_ms = time.time() * 1000
        timeout_s = self.classification_timeout_ms / 1000.0

        try:
            result = await asyncio.wait_for(
                self._classify_internal(audio_frame),
                timeout=timeout_s,
            )
            elapsed_ms = time.time() * 1000 - start_ms
            logger.debug(
                f"[InterruptionClassifier] → {result.value} "
                f"(latency={elapsed_ms:.1f}ms, "
                f"frame_len={len(audio_frame)}B)"
            )
            return result

        except asyncio.TimeoutError:
            elapsed_ms = time.time() * 1000 - start_ms
            self._error_handler.handle_classifier_timeout(
                timeout_ms=elapsed_ms,
                audio_duration_ms=_duration_ms(audio_frame),
            )
            if self.fallback_enabled:
                return Classification.GENUINE_INTERRUPTION
            return Classification.BACKGROUND_SOUND

        except Exception as exc:
            energy = 0.0
            try:
                energy = self._analyze_energy(audio_frame)
            except Exception:
                pass
            self._error_handler.handle_classifier_error(
                exc,
                audio_duration_ms=_duration_ms(audio_frame),
                audio_energy=energy,
            )
            if self.fallback_enabled:
                return Classification.GENUINE_INTERRUPTION
            return Classification.BACKGROUND_SOUND

    async def _classify_internal(self, audio_frame: bytes) -> Classification:
        """
        Internal classification logic (runs inside asyncio.wait_for).

        Pipeline:
          1. Duration rule  (Property 6)
          2. Energy rule    (Property 7)
          3. Spectral + temporal analysis

        Requirements: 6.5, 6.6, 6.7
        """
        # 1. Duration rule
        duration_ms = self._analyze_duration(audio_frame)
        if duration_ms < self.min_interruption_duration_ms:
            # Property 6: audio <200ms → noise
            return Classification.NOISE

        # 2. Energy rule
        energy = self._analyze_energy(audio_frame)
        if energy < self.speech_energy_threshold:
            # Property 7: low energy → background_sound
            return Classification.BACKGROUND_SOUND

        # 3. Spectral + temporal analysis
        spectral = self._analyze_spectral_characteristics(audio_frame)
        temporal = self._analyze_temporal_patterns(audio_frame)

        is_speech = (
            self._is_speech_spectral(spectral)
            or self._is_speech_temporal(temporal)
        )

        if is_speech:
            return Classification.GENUINE_INTERRUPTION
        else:
            return Classification.BACKGROUND_SOUND

    # ------------------------------------------------------------------
    # Event creation helpers
    # ------------------------------------------------------------------

    def create_interruption_event(
        self,
        audio_frame: bytes,
        classification: Classification,
        action_taken: str,
        classifier_latency_ms: float = 0.0,
    ) -> InterruptionEvent:
        """
        Build an InterruptionEvent for monitoring and logging.

        Requirements: 10.3, 10.5
        """
        duration_ms = self._analyze_duration(audio_frame)
        energy = self._analyze_energy(audio_frame) if len(audio_frame) >= BYTES_PER_SAMPLE else 0.0

        spectral: Dict[str, float] = {}
        temporal: Dict[str, float] = {}
        try:
            spectral = self._analyze_spectral_characteristics(audio_frame)
            temporal = self._analyze_temporal_patterns(audio_frame)
        except Exception:
            pass

        return InterruptionEvent.create(
            classification=classification.value,
            audio_duration_ms=duration_ms,
            audio_energy=energy,
            spectral_features=spectral,
            temporal_features=temporal,
            action_taken=action_taken,
            conversation_id=self.conversation_id,
            classifier_latency_ms=classifier_latency_ms,
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def is_healthy(self) -> bool:
        """Return True if classifier initialized successfully."""
        return self._initialized

    def get_config_summary(self) -> Dict[str, object]:
        """Return configuration summary for logging."""
        return {
            "min_interruption_duration_ms": self.min_interruption_duration_ms,
            "speech_energy_threshold": self.speech_energy_threshold,
            "classification_timeout_ms": self.classification_timeout_ms,
            "fallback_enabled": self.fallback_enabled,
            "initialized": self._initialized,
        }
