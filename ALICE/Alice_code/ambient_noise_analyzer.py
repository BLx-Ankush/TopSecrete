"""
Ambient Noise Analyzer — Domain 2B (Phase 4)
=============================================
Samples a short burst of ambient audio at session start, computes the RMS
energy, and feeds a normalized noise_level [0.0 – 1.0] into
VADThresholdManager so the VAD silence cutoff is automatically raised in
loud environments (coffee shop, office) and lowered in quiet ones.

Usage (called once at agent startup, before the LiveKit room connects):

    from ambient_noise_analyzer import AmbientNoiseAnalyzer
    from vad_config import VADThresholdManager

    analyzer = AmbientNoiseAnalyzer()
    noise_level = await analyzer.measure()          # 0.0 = silent, 1.0 = very loud

    mgr = VADThresholdManager(min_threshold=0.25, max_threshold=0.55, default_threshold=0.35)
    threshold = await mgr.adjust_threshold(noise_level)
    print(f"Auto VAD threshold → {threshold * 1000:.0f}ms  (noise={noise_level:.2f})")
"""

import asyncio
import logging
import math
import struct
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ── Optional PyAudio (for live mic sampling) ─────────────────────────────────
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("⚠️  pyaudio not installed — AmbientNoiseAnalyzer will use simulated noise level. "
                   "Install with: pip install pyaudio")

# ── Optional sounddevice (lighter fallback) ───────────────────────────────────
try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


# ── Calibration constants ─────────────────────────────────────────────────────
SAMPLE_DURATION_S  = 1.5    # seconds of audio to sample
SAMPLE_RATE        = 16000  # Hz
CHANNELS           = 1

# RMS thresholds tuned for typical environments (16-bit audio, full range 0–32767)
RMS_QUIET_UPPER  = 300     # Below this → definitely quiet (library, bedroom)
RMS_NOISY_LOWER  = 1500    # Above this → clearly noisy (office, street)


class AmbientNoiseAnalyzer:
    """
    Measures ambient microphone noise and returns a normalised level [0, 1].
    Integrates with VADThresholdManager to auto-adjust the VAD silence cutoff.
    """

    def __init__(self, sample_duration: float = SAMPLE_DURATION_S):
        self.sample_duration = sample_duration
        self._last_noise_level: Optional[float] = None
        self._last_rms: Optional[float] = None

    # ── Core measurement ──────────────────────────────────────────────────────

    async def measure(self) -> float:
        """
        Sample the microphone and return normalised noise level [0.0, 1.0].
        0.0 = completely silent; 1.0 = extremely loud.

        Falls back to sounddevice → pyaudio → simulated 0.3 (mild ambient)
        if no audio input is available.
        """
        rms = await asyncio.get_event_loop().run_in_executor(None, self._measure_rms_blocking)

        if rms is None:
            logger.warning("[AmbientNoise] Could not sample audio — assuming mild ambient noise (0.3)")
            rms = RMS_QUIET_UPPER  # treat as quiet-ish

        self._last_rms = rms
        noise_level = self._rms_to_level(rms)
        self._last_noise_level = noise_level

        env_label = self._classify(noise_level)
        logger.info(
            f"[AmbientNoise] RMS={rms:.1f}  noise_level={noise_level:.3f}  "
            f"environment={env_label}"
        )
        return noise_level

    def _measure_rms_blocking(self) -> Optional[float]:
        """Blocking audio capture — run in executor to avoid blocking the event loop."""

        # --- sounddevice (preferred, no callback needed) ---
        if SOUNDDEVICE_AVAILABLE:
            try:
                frames = sd.rec(
                    int(self.sample_duration * SAMPLE_RATE),
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype="int16",
                    blocking=True
                )
                rms = float(np.sqrt(np.mean(frames.astype(np.float32) ** 2)))
                return rms
            except Exception as e:
                logger.debug(f"[AmbientNoise] sounddevice failed: {e}")

        # --- PyAudio fallback ---
        if PYAUDIO_AVAILABLE:
            pa = pyaudio.PyAudio()
            stream = None
            try:
                stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    input=True,
                    frames_per_buffer=1024
                )
                num_frames = int(SAMPLE_RATE * self.sample_duration / 1024)
                sq_sum = 0.0
                total_samples = 0
                for _ in range(num_frames):
                    raw = stream.read(1024, exception_on_overflow=False)
                    samples = struct.unpack(f"{len(raw)//2}h", raw)
                    sq_sum += sum(s * s for s in samples)
                    total_samples += len(samples)
                rms = math.sqrt(sq_sum / total_samples) if total_samples else 0.0
                return rms
            except Exception as e:
                logger.debug(f"[AmbientNoise] PyAudio failed: {e}")
                return None
            finally:
                if stream:
                    stream.stop_stream()
                    stream.close()
                pa.terminate()

        return None

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _rms_to_level(rms: float) -> float:
        """
        Map raw RMS (16-bit PCM scale) to a normalised [0, 1] noise level.
        Uses a log scale so moderate noise isn't compressed to near-zero.
        """
        rms = max(rms, 1.0)
        # Log scale: map [1, 32767] → [0, 1]
        level = math.log10(rms) / math.log10(32767)
        return max(0.0, min(1.0, level))

    @staticmethod
    def _classify(level: float) -> str:
        if level < 0.3:
            return "QUIET"
        elif level < 0.6:
            return "MODERATE"
        else:
            return "LOUD"

    def get_status(self) -> dict:
        return {
            "last_rms": self._last_rms,
            "last_noise_level": self._last_noise_level,
            "environment": self._classify(self._last_noise_level or 0.3),
            "sounddevice_available": SOUNDDEVICE_AVAILABLE,
            "pyaudio_available": PYAUDIO_AVAILABLE,
        }
