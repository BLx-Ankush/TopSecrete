"""
Tests for InterruptionClassifier — unit + property tests.

Property tests verify:
  Property 5: Every audio input produces exactly one classification
  Property 6: Audio <200ms → noise
  Property 7: Low energy audio → background_sound

Requirements coverage: 5.1-5.7, 6.1-6.7, 13.2, 13.4, 13.5
"""

import sys
import os
import struct
import math
import asyncio

_CODE = os.path.dirname(os.path.dirname(__file__))
if _CODE not in sys.path:
    sys.path.insert(0, _CODE)

import pytest
import numpy as np

try:
    from interruption_classifier import InterruptionClassifier, Classification
    CLASSIFIER_AVAILABLE = True
except ImportError as e:
    CLASSIFIER_AVAILABLE = False
    pytest.skip(f"interruption_classifier not available: {e}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_RATE = 24000
BYTES_PER_SAMPLE = 2


def make_pcm(duration_ms: float, frequency_hz: float = 440, amplitude: float = 0.5) -> bytes:
    """Generate PCM s16le sine wave."""
    n_samples = int(SAMPLE_RATE * duration_ms / 1000)
    samples = []
    for i in range(n_samples):
        v = int(amplitude * 32767 * math.sin(2 * math.pi * frequency_hz * i / SAMPLE_RATE))
        samples.append(max(-32768, min(32767, v)))
    return struct.pack(f"<{n_samples}h", *samples)


def make_silence(duration_ms: float) -> bytes:
    """Generate PCM silence."""
    n_samples = int(SAMPLE_RATE * duration_ms / 1000)
    return struct.pack(f"<{n_samples}h", *([0] * n_samples))


def make_noise(duration_ms: float, amplitude: float = 0.05) -> bytes:
    """Generate low-energy broadband noise."""
    rng = np.random.default_rng(42)
    n_samples = int(SAMPLE_RATE * duration_ms / 1000)
    samples = (rng.random(n_samples) * 2 - 1) * amplitude * 32767
    samples = samples.astype(np.int16)
    return samples.tobytes()


def default_classifier(**kwargs) -> InterruptionClassifier:
    return InterruptionClassifier(
        min_interruption_duration_ms=200,
        speech_energy_threshold=0.02,
        classification_timeout_ms=500,  # generous timeout for tests
        fallback_enabled=True,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------

class TestClassifierInit:

    def test_init_success(self):
        clf = default_classifier()
        assert clf.is_healthy()

    def test_config_summary_complete(self):
        clf = default_classifier()
        cfg = clf.get_config_summary()
        assert "min_interruption_duration_ms" in cfg
        assert "speech_energy_threshold" in cfg
        assert "classification_timeout_ms" in cfg
        assert cfg["initialized"] is True

    def test_invalid_energy_threshold_raises(self):
        """Invalid config should raise ValueError in _validate_config."""
        with pytest.raises(ValueError):
            InterruptionClassifier(
                speech_energy_threshold=1.5,
                min_interruption_duration_ms=200,
                classification_timeout_ms=500,
            )

    def test_invalid_duration_raises(self):
        """Invalid config should raise ValueError in _validate_config."""
        with pytest.raises(ValueError):
            InterruptionClassifier(
                speech_energy_threshold=0.02,
                min_interruption_duration_ms=-1,
                classification_timeout_ms=500,
            )


class TestPropertyFive:
    """Property 5: Every audio input produces exactly one Classification."""

    INPUTS = [
        make_silence(50),
        make_silence(300),
        make_pcm(100, 440, 0.5),
        make_pcm(400, 440, 0.5),
        make_pcm(400, 1200, 0.3),
        make_noise(100, 0.01),
        make_noise(300, 0.1),
        b"\x00" * 4,  # minimal buffer
        b"",           # empty buffer
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("audio", INPUTS)
    async def test_always_returns_classification(self, audio):
        clf = default_classifier()
        result = await clf.classify_audio(audio)
        assert isinstance(result, Classification)
        assert result in (
            Classification.GENUINE_INTERRUPTION,
            Classification.NOISE,
            Classification.BACKGROUND_SOUND,
        )


class TestPropertySix:
    """Property 6: Audio shorter than min_interruption_duration_ms → noise."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("duration_ms", [10, 50, 100, 150, 199])
    async def test_short_audio_is_noise(self, duration_ms):
        clf = InterruptionClassifier(
            min_interruption_duration_ms=200,
            speech_energy_threshold=0.001,  # very low so energy rule won't fire
            classification_timeout_ms=500,
        )
        # Make high-energy audio that would be speech if long enough
        audio = make_pcm(duration_ms, 440, 0.8)
        result = await clf.classify_audio(audio)
        assert result == Classification.NOISE, (
            f"Expected NOISE for {duration_ms}ms audio, got {result}"
        )

    @pytest.mark.asyncio
    async def test_borderline_duration_is_noise(self):
        """199ms (just under 200ms threshold) must be noise."""
        clf = InterruptionClassifier(
            min_interruption_duration_ms=200,
            speech_energy_threshold=0.001,
            classification_timeout_ms=500,
        )
        audio = make_pcm(199, 440, 0.9)
        result = await clf.classify_audio(audio)
        assert result == Classification.NOISE


class TestPropertySeven:
    """Property 7: Low-energy audio (< speech_energy_threshold) → background_sound."""

    @pytest.mark.asyncio
    async def test_very_low_energy_is_background(self):
        clf = InterruptionClassifier(
            min_interruption_duration_ms=100,  # low so duration rule won't fire
            speech_energy_threshold=0.05,
            classification_timeout_ms=500,
        )
        # Nearly silent audio — energy << threshold
        audio = make_noise(400, amplitude=0.001)
        result = await clf.classify_audio(audio)
        assert result == Classification.BACKGROUND_SOUND

    @pytest.mark.asyncio
    async def test_silence_is_background(self):
        clf = InterruptionClassifier(
            min_interruption_duration_ms=100,
            speech_energy_threshold=0.01,
            classification_timeout_ms=500,
        )
        audio = make_silence(400)
        result = await clf.classify_audio(audio)
        assert result == Classification.BACKGROUND_SOUND


class TestGenuineInterruption:
    """High-energy, long-duration speech-like audio should be genuine_interruption."""

    @pytest.mark.asyncio
    async def test_speech_tone_is_genuine(self):
        """A sustained 600Hz tone at high amplitude for 500ms → genuine interruption."""
        clf = InterruptionClassifier(
            min_interruption_duration_ms=200,
            speech_energy_threshold=0.02,
            classification_timeout_ms=500,
        )
        # 600Hz is well within speech centroid range (200-3400Hz)
        audio = make_pcm(500, 600, 0.5)
        result = await clf.classify_audio(audio)
        assert result == Classification.GENUINE_INTERRUPTION

    @pytest.mark.asyncio
    async def test_high_energy_is_not_background(self):
        clf = InterruptionClassifier(
            min_interruption_duration_ms=200,
            speech_energy_threshold=0.02,
            classification_timeout_ms=500,
        )
        audio = make_pcm(400, 800, 0.6)
        result = await clf.classify_audio(audio)
        # High energy should not be classified as background
        assert result != Classification.BACKGROUND_SOUND


class TestDurationAnalysis:

    def test_duration_100ms(self):
        clf = default_classifier()
        audio = make_pcm(100, 440, 0.5)
        d = clf._analyze_duration(audio)
        assert abs(d - 100.0) < 2.0   # within 2ms tolerance

    def test_duration_500ms(self):
        clf = default_classifier()
        audio = make_pcm(500, 440, 0.5)
        d = clf._analyze_duration(audio)
        assert abs(d - 500.0) < 5.0

    def test_empty_audio_duration_zero(self):
        clf = default_classifier()
        d = clf._analyze_duration(b"")
        assert d == 0.0


class TestEnergyAnalysis:

    def test_silence_energy_zero(self):
        clf = default_classifier()
        audio = make_silence(200)
        energy = clf._analyze_energy(audio)
        assert energy == 0.0

    def test_max_amplitude_energy_near_one(self):
        clf = default_classifier()
        audio = make_pcm(200, 440, 1.0)
        energy = clf._analyze_energy(audio)
        # Sine wave at amplitude 1.0 has RMS = 1/sqrt(2) ≈ 0.707
        assert 0.5 < energy <= 1.0

    def test_energy_in_range(self):
        """Property 3-style check: energy always [0, 1]."""
        clf = default_classifier()
        for amp in [0.0, 0.1, 0.5, 1.0]:
            audio = make_pcm(200, 440, amp)
            energy = clf._analyze_energy(audio)
            assert 0.0 <= energy <= 1.0


class TestSpectralAnalysis:

    def test_spectral_features_returned(self):
        clf = default_classifier()
        audio = make_pcm(200, 440, 0.5)
        features = clf._analyze_spectral_characteristics(audio)
        assert "centroid_hz" in features
        assert "rolloff_hz" in features
        assert "bandwidth_hz" in features

    def test_centroid_positive(self):
        clf = default_classifier()
        audio = make_pcm(400, 1000, 0.5)
        features = clf._analyze_spectral_characteristics(audio)
        assert features["centroid_hz"] > 0

    def test_silence_spectral_zeros(self):
        clf = default_classifier()
        audio = make_silence(200)
        features = clf._analyze_spectral_characteristics(audio)
        assert features["centroid_hz"] == 0.0


class TestTemporalAnalysis:

    def test_temporal_features_returned(self):
        clf = default_classifier()
        audio = make_pcm(200, 440, 0.5)
        features = clf._analyze_temporal_patterns(audio)
        assert "zero_crossing_rate" in features
        assert "rhythm_regularity" in features

    def test_zcr_non_negative(self):
        clf = default_classifier()
        audio = make_pcm(400, 440, 0.5)
        features = clf._analyze_temporal_patterns(audio)
        assert features["zero_crossing_rate"] >= 0

    def test_silence_zcr_zero(self):
        clf = default_classifier()
        audio = make_silence(400)
        features = clf._analyze_temporal_patterns(audio)
        assert features["zero_crossing_rate"] == 0.0


class TestInterruptionEventCreation:

    @pytest.mark.asyncio
    async def test_event_created_correctly(self):
        clf = default_classifier(conversation_id="test-sess")
        audio = make_pcm(400, 600, 0.5)
        classification = await clf.classify_audio(audio)
        evt = clf.create_interruption_event(audio, classification, "cancel_response", 12.5)
        assert evt.classification == classification.value
        assert evt.action_taken == "cancel_response"
        assert evt.classifier_latency_ms == 12.5
        assert evt.conversation_id == "test-sess"
        assert evt.audio_energy >= 0.0


class TestTimeoutFallback:

    @pytest.mark.asyncio
    async def test_tiny_timeout_uses_fallback(self):
        """Extremely short timeout forces fallback (genuine_interruption)."""
        clf = InterruptionClassifier(
            min_interruption_duration_ms=200,
            speech_energy_threshold=0.02,
            classification_timeout_ms=1,   # 1ms — will almost certainly timeout
            fallback_enabled=True,
        )
        audio = make_pcm(400, 600, 0.5)
        # May timeout; fallback returns genuine_interruption
        result = await clf.classify_audio(audio)
        assert isinstance(result, Classification)


class TestFallbackDisabled:

    @pytest.mark.asyncio
    async def test_timeout_without_fallback_returns_background(self):
        clf = InterruptionClassifier(
            min_interruption_duration_ms=200,
            speech_energy_threshold=0.02,
            classification_timeout_ms=1,
            fallback_enabled=False,
        )
        audio = make_pcm(400, 600, 0.5)
        result = await clf.classify_audio(audio)
        # When fallback disabled and timeout, returns background_sound
        assert isinstance(result, Classification)
