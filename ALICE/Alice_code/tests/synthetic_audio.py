"""
Synthetic Audio Generation Utilities for Testing.

All functions in this module generate raw PCM audio bytes in the format
expected by Alice's audio pipeline:

    Format : PCM signed 16-bit little-endian  (s16le)
    Rate   : 24 000 Hz  (24 kHz)
    Channels: 1  (mono)

This matches LiveKit's audio configuration and the STT provider requirements
documented in stt/provider.py.

Design notes
------------
* All public functions return ``bytes`` objects — ready to pass directly to
  ``MockSTTProvider.stream_audio()`` or any real STT provider.
* numpy is used internally for efficient signal generation.  The final step
  converts the float32 array to int16 samples and packs them as little-endian
  PCM via ``struct.pack``.
* ``generate_speech_like_audio`` targets a realistic Zero Crossing Rate (ZCR)
  of 50–200 crossings per second, mimicking voiced-fricative speech without
  requiring a real microphone or TTS call.

Usage example
-------------
    from synthetic_audio import (
        generate_silence,
        generate_sine_wave,
        generate_speech_like_audio,
    )

    silence_500ms = generate_silence(500)
    tone_1s       = generate_sine_wave(1000, frequency_hz=440)
    speech_2s     = generate_speech_like_audio(2000)

Requirements: 2.1, 2.3, 2.7  (audio format validation)
"""

from __future__ import annotations

import math
import os
import struct
import time
from typing import Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Sample rate used throughout Alice's audio pipeline.
SAMPLE_RATE: int = 24_000

#: Number of audio channels (mono).
CHANNELS: int = 1

#: Maximum amplitude of a signed 16-bit PCM sample.
INT16_MAX: int = 32_767

#: Minimum amplitude of a signed 16-bit PCM sample.
INT16_MIN: int = -32_768


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _ms_to_samples(duration_ms: int) -> int:
    """
    Convert a duration in milliseconds to a sample count.

    Parameters
    ----------
    duration_ms
        Duration in milliseconds (must be > 0).

    Returns
    -------
    int
        Number of audio samples at SAMPLE_RATE.

    Raises
    ------
    ValueError
        If *duration_ms* is not a positive integer.
    """
    if duration_ms <= 0:
        raise ValueError(
            f"duration_ms must be a positive integer, got {duration_ms!r}"
        )
    return int(SAMPLE_RATE * duration_ms / 1000)


def _float_array_to_pcm_bytes(samples: np.ndarray) -> bytes:
    """
    Convert a float32 NumPy array of normalised samples [-1.0, 1.0] to
    signed 16-bit little-endian PCM bytes.

    Parameters
    ----------
    samples
        1-D float32 array with values in [-1.0, 1.0].  Values outside this
        range are clipped silently.

    Returns
    -------
    bytes
        Raw PCM bytes (2 bytes per sample, little-endian).
    """
    # Clip to [-1.0, 1.0] then scale to int16 range
    clipped = np.clip(samples, -1.0, 1.0)
    int16_array = (clipped * INT16_MAX).astype(np.int16)

    # Pack as little-endian int16 (struct '<h')
    return struct.pack(f"<{len(int16_array)}h", *int16_array)


def _validate_amplitude(amplitude: float, name: str = "amplitude") -> None:
    """Raise ValueError if amplitude is outside [0.0, 1.0]."""
    if not 0.0 <= amplitude <= 1.0:
        raise ValueError(
            f"{name} must be in [0.0, 1.0], got {amplitude!r}"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_silence(duration_ms: int) -> bytes:
    """
    Generate zero-filled PCM silence.

    Parameters
    ----------
    duration_ms
        Duration of silence in milliseconds.

    Returns
    -------
    bytes
        Raw PCM s16le bytes at 24 kHz mono.  Every sample is 0x0000.

    Examples
    --------
    >>> data = generate_silence(20)
    >>> len(data)
    960   # 480 samples × 2 bytes per sample
    >>> set(data)
    {0}
    """
    n_samples = _ms_to_samples(duration_ms)
    return b"\x00\x00" * n_samples


def generate_sine_wave(
    duration_ms: int,
    frequency_hz: float = 440.0,
    amplitude: float = 0.5,
) -> bytes:
    """
    Generate a pure sinusoidal tone.

    A sine wave is the simplest non-silence audio signal.  It is useful for
    testing that audio is being received and processed (e.g., by checking that
    the VAD does *not* fire on a clean 440 Hz tone that is not voice-band
    energy, or that it *does* fire on a 200 Hz voice-fundamental tone).

    Parameters
    ----------
    duration_ms
        Duration of the tone in milliseconds.
    frequency_hz
        Frequency of the sine wave in Hz.  Default 440 Hz (concert A).
    amplitude
        Peak amplitude in the normalised range [0.0, 1.0].

    Returns
    -------
    bytes
        Raw PCM s16le bytes at 24 kHz mono.

    Raises
    ------
    ValueError
        If *amplitude* is outside [0.0, 1.0] or *frequency_hz* ≤ 0.

    Examples
    --------
    >>> data = generate_sine_wave(1000, frequency_hz=440, amplitude=0.5)
    >>> len(data) == 24000 * 2  # 1 s × 24 000 samples × 2 bytes
    True
    """
    if frequency_hz <= 0:
        raise ValueError(f"frequency_hz must be positive, got {frequency_hz!r}")
    _validate_amplitude(amplitude)

    n_samples = _ms_to_samples(duration_ms)
    t = np.linspace(0.0, duration_ms / 1000.0, n_samples, endpoint=False, dtype=np.float32)
    samples = (amplitude * np.sin(2.0 * np.pi * frequency_hz * t)).astype(np.float32)
    return _float_array_to_pcm_bytes(samples)


def generate_noise(duration_ms: int, amplitude: float = 0.1) -> bytes:
    """
    Generate uniformly-distributed random white noise.

    White noise is used to simulate background acoustic conditions, test
    noise-robustness of the VAD, or produce synthetic "click" artefacts.

    Parameters
    ----------
    duration_ms
        Duration of noise in milliseconds.
    amplitude
        Peak amplitude in [0.0, 1.0].  Amplitude 0.1 is subtle; 0.5 is loud.

    Returns
    -------
    bytes
        Raw PCM s16le bytes at 24 kHz mono.

    Raises
    ------
    ValueError
        If *amplitude* is outside [0.0, 1.0].

    Examples
    --------
    >>> data = generate_noise(100, amplitude=0.1)
    >>> len(data) == 100 * 24000 // 1000 * 2
    True
    """
    _validate_amplitude(amplitude)
    n_samples = _ms_to_samples(duration_ms)
    rng = np.random.default_rng()
    samples = (amplitude * rng.uniform(-1.0, 1.0, n_samples)).astype(np.float32)
    return _float_array_to_pcm_bytes(samples)


def generate_speech_like_audio(
    duration_ms: int,
    amplitude: float = 0.3,
    target_zcr_hz: float = 120.0,
) -> bytes:
    """
    Generate audio with a speech-like zero crossing rate (ZCR).

    Real voiced speech typically has a ZCR of 50–200 crossings per second,
    arising from a combination of periodic vocal-fold vibration and aperiodic
    frication.  This function creates a synthetic signal with a ZCR close to
    *target_zcr_hz* by summing a low-frequency fundamental (simulating voicing)
    with spectrally shaped noise (simulating the vocal tract filter and
    frication).

    This is more realistic than pure sine waves for testing voice activity
    detectors and turn-detection components.

    Parameters
    ----------
    duration_ms
        Duration of the signal in milliseconds.
    amplitude
        Peak amplitude in [0.0, 1.0].
    target_zcr_hz
        Desired zero crossing rate in crossings per second.  The default
        120 Hz sits in the middle of the typical speech ZCR range.

    Returns
    -------
    bytes
        Raw PCM s16le bytes at 24 kHz mono.

    Notes
    -----
    The ZCR of the returned audio will be *approximately* ``target_zcr_hz``
    but is not guaranteed to be exact because the noise component is random.

    Raises
    ------
    ValueError
        If *amplitude* is outside [0.0, 1.0].

    Examples
    --------
    >>> data = generate_speech_like_audio(500)
    >>> len(data) == 500 * 24000 // 1000 * 2
    True
    """
    _validate_amplitude(amplitude)
    n_samples = _ms_to_samples(duration_ms)
    rng = np.random.default_rng(seed=42)  # Deterministic for test reproducibility

    duration_s = duration_ms / 1000.0
    t = np.linspace(0.0, duration_s, n_samples, endpoint=False, dtype=np.float32)

    # ---- Component 1: voiced fundamental (100 Hz — typical male voice pitch)
    f0 = 100.0
    voiced = 0.6 * np.sin(2.0 * np.pi * f0 * t)

    # ---- Component 2: spectrally shaped noise to introduce ZCR
    # The noise frequency determines how often zero crossings occur.
    # We band-limit by summing a few harmonics of the target ZCR frequency.
    noise_fundamental = target_zcr_hz / 2.0  # ZCR ≈ 2× fundamental for band-limited signal
    noise = np.zeros(n_samples, dtype=np.float32)
    for harmonic in [1, 2, 3]:
        noise += (1.0 / harmonic) * np.sin(
            2.0 * np.pi * noise_fundamental * harmonic * t
            + rng.uniform(0, 2 * np.pi)  # random phase per harmonic
        )
    # Add a tiny random dither to avoid perfectly periodic ZCR
    noise += 0.05 * rng.standard_normal(n_samples).astype(np.float32)
    noise /= np.abs(noise).max() + 1e-9  # Normalise noise to [-1.0, 1.0]

    # Blend: 60 % voiced + 40 % noise → speech-like ZCR
    blended = (0.6 * voiced + 0.4 * noise).astype(np.float32)

    # Scale to requested amplitude
    peak = np.abs(blended).max() + 1e-9
    samples = (amplitude * blended / peak).astype(np.float32)

    return _float_array_to_pcm_bytes(samples)


def generate_short_click(amplitude: float = 0.8) -> bytes:
    """
    Generate a short 50 ms noise burst simulating a click or keystroke artefact.

    Clicks are common interruption-classifier test cases: they have high
    energy and a high ZCR but are much shorter than genuine speech.  The
    interruption classifier should label them as "noise" rather than
    "genuine_interruption".

    Parameters
    ----------
    amplitude
        Peak amplitude in [0.0, 1.0].  Default 0.8 (loud click).

    Returns
    -------
    bytes
        Raw PCM s16le bytes at 24 kHz mono.  Always 50 ms (2400 samples,
        4800 bytes).

    Raises
    ------
    ValueError
        If *amplitude* is outside [0.0, 1.0].

    Examples
    --------
    >>> data = generate_short_click()
    >>> len(data)
    4800  # 50 ms × 24 000 Hz × 2 bytes per sample
    """
    _validate_amplitude(amplitude)
    return generate_noise(duration_ms=50, amplitude=amplitude)


# ---------------------------------------------------------------------------
# Composite helpers
# ---------------------------------------------------------------------------

def generate_utterance_with_silence(
    speech_ms: int = 500,
    leading_silence_ms: int = 100,
    trailing_silence_ms: int = 300,
    speech_amplitude: float = 0.3,
) -> bytes:
    """
    Generate a complete utterance segment: silence → speech → silence.

    This is the typical pattern fed to a turn-detection system.

    Parameters
    ----------
    speech_ms
        Duration of the speech portion in ms.
    leading_silence_ms
        Duration of silence before speech starts.
    trailing_silence_ms
        Duration of silence after speech ends.
    speech_amplitude
        Amplitude of the speech signal.

    Returns
    -------
    bytes
        Concatenated PCM bytes: leading_silence + speech + trailing_silence.
    """
    leading = generate_silence(leading_silence_ms)
    speech = generate_speech_like_audio(speech_ms, amplitude=speech_amplitude)
    trailing = generate_silence(trailing_silence_ms)
    return leading + speech + trailing


def chunk_audio(audio_bytes: bytes, chunk_ms: int = 20) -> list[bytes]:
    """
    Split a flat PCM buffer into fixed-size chunks.

    Useful for simulating a real streaming audio source that delivers audio
    in fixed-size frames (LiveKit typically delivers 20 ms frames).

    Parameters
    ----------
    audio_bytes
        Source PCM bytes.
    chunk_ms
        Duration of each chunk in milliseconds.

    Returns
    -------
    list[bytes]
        List of PCM byte chunks.  The final chunk is zero-padded if the
        total length is not an exact multiple of *chunk_ms*.
    """
    bytes_per_chunk = _ms_to_samples(chunk_ms) * 2  # 2 bytes per sample
    chunks = []
    for i in range(0, max(len(audio_bytes), bytes_per_chunk), bytes_per_chunk):
        chunk = audio_bytes[i : i + bytes_per_chunk]
        if len(chunk) < bytes_per_chunk:
            chunk = chunk + b"\x00" * (bytes_per_chunk - len(chunk))
        if chunk:
            chunks.append(chunk)
    return chunks


def measure_zcr(audio_bytes: bytes) -> float:
    """
    Measure the zero crossing rate of a PCM buffer.

    Parameters
    ----------
    audio_bytes
        Raw PCM s16le bytes.

    Returns
    -------
    float
        Zero crossing rate in crossings per second.
    """
    n_samples = len(audio_bytes) // 2
    if n_samples < 2:
        return 0.0
    samples = struct.unpack(f"<{n_samples}h", audio_bytes[: n_samples * 2])
    arr = np.array(samples, dtype=np.float32)
    crossings = int(np.sum(np.diff(np.sign(arr)) != 0))
    duration_s = n_samples / SAMPLE_RATE
    return crossings / duration_s if duration_s > 0 else 0.0


def measure_rms(audio_bytes: bytes) -> float:
    """
    Measure the RMS energy of a PCM buffer, normalised to [0.0, 1.0].

    Parameters
    ----------
    audio_bytes
        Raw PCM s16le bytes.

    Returns
    -------
    float
        Normalised RMS value in [0.0, 1.0].
    """
    n_samples = len(audio_bytes) // 2
    if n_samples == 0:
        return 0.0
    samples = struct.unpack(f"<{n_samples}h", audio_bytes[: n_samples * 2])
    arr = np.array(samples, dtype=np.float64)
    rms = math.sqrt(np.mean(arr ** 2))
    return float(rms / INT16_MAX)


# ---------------------------------------------------------------------------
# Standalone demo / smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== synthetic_audio.py Demo ===\n")

    tests: list[tuple[str, bytes]] = [
        ("Silence 200 ms",         generate_silence(200)),
        ("Sine 440 Hz 200 ms",     generate_sine_wave(200, frequency_hz=440, amplitude=0.5)),
        ("Noise 200 ms",           generate_noise(200, amplitude=0.1)),
        ("Speech-like 500 ms",     generate_speech_like_audio(500, amplitude=0.3)),
        ("Short click 50 ms",      generate_short_click()),
        ("Utterance with silence", generate_utterance_with_silence()),
    ]

    expected_bytes = {
        "Silence 200 ms":         _ms_to_samples(200) * 2,
        "Sine 440 Hz 200 ms":     _ms_to_samples(200) * 2,
        "Noise 200 ms":           _ms_to_samples(200) * 2,
        "Speech-like 500 ms":     _ms_to_samples(500) * 2,
        "Short click 50 ms":      _ms_to_samples(50)  * 2,
    }

    header = f"{'Signal':<30} {'Bytes':>8}  {'RMS':>6}  {'ZCR (Hz)':>10}"
    print(header)
    print("-" * len(header))

    for name, data in tests:
        rms = measure_rms(data)
        zcr = measure_zcr(data)
        print(f"{name:<30} {len(data):>8}  {rms:>6.4f}  {zcr:>10.1f}")

    print("\nChunking utterance into 20 ms frames:")
    utterance = generate_utterance_with_silence(speech_ms=100)
    chunks = chunk_audio(utterance, chunk_ms=20)
    print(f"  Total bytes : {len(utterance)}")
    print(f"  Chunk count : {len(chunks)}")
    print(f"  Chunk size  : {len(chunks[0])} bytes each")

    print("\nAll checks passed ✓")
