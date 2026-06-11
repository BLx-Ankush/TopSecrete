"""
Unified Configuration Manager for Alice Conversation Fluidity Enhancement.

Loads and validates ALL environment variables required by the fluidity feature:
  - Neural Turn Detector settings
  - STT Provider credentials and settings
  - Interruption Classifier settings
  - Cost Monitoring settings
  - A/B Testing settings
  - Multi-language support settings

All validation errors fall back to documented defaults so Alice never fails
to start due to a misconfigured optional parameter.

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8, 15.9
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _get_bool(key: str, default: bool) -> bool:
    val = os.getenv(key, str(default)).strip().lower()
    return val in ("true", "1", "yes", "on")


def _get_float(key: str, default: float, min_val: float = None, max_val: float = None) -> float:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        v = float(raw)
        if min_val is not None and v < min_val:
            logger.warning(f"[Config] {key}={v} < min {min_val}; using min")
            return min_val
        if max_val is not None and v > max_val:
            logger.warning(f"[Config] {key}={v} > max {max_val}; using max")
            return max_val
        return v
    except ValueError:
        logger.error(f"[Config] Invalid float for {key}={raw!r}; using default={default}")
        return default


def _get_int(key: str, default: int, min_val: int = None, max_val: int = None) -> int:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        v = int(raw)
        if min_val is not None and v < min_val:
            logger.warning(f"[Config] {key}={v} < min {min_val}; using min")
            return min_val
        if max_val is not None and v > max_val:
            logger.warning(f"[Config] {key}={v} > max {max_val}; using max")
            return max_val
        return v
    except ValueError:
        logger.error(f"[Config] Invalid int for {key}={raw!r}; using default={default}")
        return default


def _get_str(key: str, default: str, allowed: list = None) -> str:
    val = os.getenv(key, default).strip()
    if allowed and val not in allowed:
        logger.warning(f"[Config] {key}={val!r} not in {allowed}; using default={default!r}")
        return default
    return val


# ---------------------------------------------------------------------------
# Sub-configurations
# ---------------------------------------------------------------------------

@dataclass
class STTProviderConfig:
    """
    Configuration for STT provider connection.

    Requirements: 15.1, 15.3
    """
    provider_type: str = "deepgram"          # "assemblyai" | "deepgram"
    assemblyai_api_key: str = ""
    deepgram_api_key: str = ""
    sample_rate: int = 24000                 # Hz — must match LiveKit pipeline
    encoding: str = "pcm_s16le"
    channels: int = 1                        # Mono
    connection_timeout_s: int = 10
    reconnect_attempts: int = 3
    enabled: bool = False                    # Disabled when no API key available

    @classmethod
    def from_env(cls) -> "STTProviderConfig":
        assemblyai_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
        deepgram_key = os.getenv("DEEPGRAM_API_KEY", "").strip()
        provider = _get_str("STT_PROVIDER", "deepgram", ["assemblyai", "deepgram"])
        # Only enable if we have an API key
        enabled = bool(assemblyai_key) or bool(deepgram_key)
        if not enabled:
            logger.info("[Config] No STT API keys found — NeuralTurnDetector will use Silero VAD fallback")
        return cls(
            provider_type=provider,
            assemblyai_api_key=assemblyai_key,
            deepgram_api_key=deepgram_key,
            sample_rate=_get_int("STT_SAMPLE_RATE", 24000, 8000, 48000),
            encoding=_get_str("STT_ENCODING", "pcm_s16le"),
            channels=_get_int("STT_CHANNELS", 1, 1, 2),
            connection_timeout_s=_get_int("STT_CONNECTION_TIMEOUT_S", 10, 1, 60),
            reconnect_attempts=_get_int("STT_RECONNECT_ATTEMPTS", 3, 0, 10),
            enabled=enabled,
        )

    def get_active_api_key(self) -> str:
        """Return the API key for the configured provider."""
        if self.provider_type == "assemblyai":
            return self.assemblyai_api_key
        return self.deepgram_api_key


@dataclass
class NeuralTurnDetectorSettings:
    """
    Runtime settings for the NeuralTurnDetector.

    Requirements: 15.4, 15.5, 15.6
    """
    enabled: bool = True
    confidence_threshold: float = 0.4         # [0.0, 1.0]
    min_turn_silence_ms: int = 300            # ms
    max_turn_silence_ms: int = 1200          # ms
    health_check_interval_s: int = 30
    max_failures: int = 3

    @classmethod
    def from_env(cls) -> "NeuralTurnDetectorSettings":
        return cls(
            enabled=_get_bool("NEURAL_TURN_DETECTOR_ENABLED", True),
            confidence_threshold=_get_float(
                "END_OF_TURN_CONFIDENCE_THRESHOLD", 0.4, 0.0, 1.0),
            min_turn_silence_ms=_get_int("MIN_TURN_SILENCE_MS", 300, 100, 2000),
            max_turn_silence_ms=_get_int("MAX_TURN_SILENCE_MS", 1200, 200, 5000),
            health_check_interval_s=_get_int(
                "NEURAL_TURN_DETECTOR_HEALTH_CHECK_INTERVAL_S", 30, 5, 300),
            max_failures=_get_int("NEURAL_TURN_DETECTOR_MAX_FAILURES", 3, 1, 20),
        )


@dataclass
class InterruptionClassifierSettings:
    """
    Runtime settings for the InterruptionClassifier.

    Requirements: 15.2
    """
    enabled: bool = True
    min_interruption_duration_ms: int = 200   # < 200ms → noise
    speech_energy_threshold: float = 0.02     # below → background_sound
    classification_timeout_ms: int = 100      # must classify within 100ms
    fallback_enabled: bool = True             # Fall back to basic interruption handling

    @classmethod
    def from_env(cls) -> "InterruptionClassifierSettings":
        return cls(
            enabled=_get_bool("INTERRUPTION_CLASSIFIER_ENABLED", True),
            min_interruption_duration_ms=_get_int(
                "MIN_INTERRUPTION_DURATION_MS", 200, 50, 2000),
            speech_energy_threshold=_get_float(
                "SPEECH_ENERGY_THRESHOLD", 0.02, 0.0, 1.0),
            classification_timeout_ms=_get_int(
                "CLASSIFICATION_TIMEOUT_MS", 100, 10, 1000),
            fallback_enabled=_get_bool("INTERRUPTION_CLASSIFIER_FALLBACK_ENABLED", True),
        )


@dataclass
class CostMonitorSettings:
    """
    Runtime settings for the CostMonitor.

    Requirements: 12.3, 12.5
    """
    enabled: bool = True
    stt_cost_per_minute: float = 0.0015       # AssemblyAI Universal-3 Pro $/minute
    gemini_cost_per_minute: float = 0.0285    # Gemini 2.5 Flash audio $/minute
    target_cost_per_agent_minute: float = 0.030
    felicia_baseline_cost: float = 0.090

    @classmethod
    def from_env(cls) -> "CostMonitorSettings":
        return cls(
            enabled=_get_bool("COST_MONITORING_ENABLED", True),
            stt_cost_per_minute=_get_float("STT_COST_PER_MINUTE", 0.0015, 0.0),
            gemini_cost_per_minute=_get_float("GEMINI_COST_PER_MINUTE", 0.0285, 0.0),
            target_cost_per_agent_minute=_get_float(
                "TARGET_COST_PER_AGENT_MINUTE", 0.030, 0.001),
            felicia_baseline_cost=_get_float("FELICIA_BASELINE_COST", 0.090, 0.0),
        )


@dataclass
class ABTestingSettings:
    """
    A/B testing configuration for optional enhancement (Task 18).

    Requirements: 20.1, 20.2, 20.7
    """
    enabled: bool = False
    neural_vs_silero_split: float = 0.5       # fraction using neural turn detection
    adaptive_vs_basic_split: float = 0.5      # fraction using adaptive interruption

    @classmethod
    def from_env(cls) -> "ABTestingSettings":
        return cls(
            enabled=_get_bool("AB_TESTING_ENABLED", False),
            neural_vs_silero_split=_get_float("AB_NEURAL_SILERO_SPLIT", 0.5, 0.0, 1.0),
            adaptive_vs_basic_split=_get_float("AB_ADAPTIVE_BASIC_SPLIT", 0.5, 0.0, 1.0),
        )


@dataclass
class MultiLanguageSettings:
    """
    Multi-language support configuration for optional enhancement (Task 17).

    Requirements: 19.1, 19.2, 19.3
    """
    enabled: bool = False
    default_language: str = "en"
    supported_languages: list = field(default_factory=lambda: ["en"])
    auto_detect: bool = True

    @classmethod
    def from_env(cls) -> "MultiLanguageSettings":
        langs_raw = os.getenv("SUPPORTED_LANGUAGES", "en")
        langs = [l.strip() for l in langs_raw.split(",") if l.strip()]
        return cls(
            enabled=_get_bool("MULTI_LANGUAGE_ENABLED", False),
            default_language=_get_str("DEFAULT_LANGUAGE", "en"),
            supported_languages=langs,
            auto_detect=_get_bool("AUTO_LANGUAGE_DETECT", True),
        )


# ---------------------------------------------------------------------------
# Master configuration object
# ---------------------------------------------------------------------------

@dataclass
class FluidityConfig:
    """
    Master configuration for Alice Conversation Fluidity Enhancement.

    Aggregates all sub-configurations.  Load once at startup via from_env().

    Requirements: 15.1–15.9
    """
    stt: STTProviderConfig = field(default_factory=STTProviderConfig)
    neural_turn_detector: NeuralTurnDetectorSettings = field(
        default_factory=NeuralTurnDetectorSettings)
    interruption_classifier: InterruptionClassifierSettings = field(
        default_factory=InterruptionClassifierSettings)
    cost_monitor: CostMonitorSettings = field(default_factory=CostMonitorSettings)
    ab_testing: ABTestingSettings = field(default_factory=ABTestingSettings)
    multi_language: MultiLanguageSettings = field(default_factory=MultiLanguageSettings)

    @classmethod
    def from_env(cls) -> "FluidityConfig":
        """
        Load all configuration from environment variables.

        All sub-configurations use safe defaults on validation failure so Alice
        will always start successfully, even with missing or invalid env vars.

        Requirements: 15.1, 15.8, 15.9
        """
        logger.info("[FluidityConfig] Loading configuration from environment...")
        cfg = cls(
            stt=STTProviderConfig.from_env(),
            neural_turn_detector=NeuralTurnDetectorSettings.from_env(),
            interruption_classifier=InterruptionClassifierSettings.from_env(),
            cost_monitor=CostMonitorSettings.from_env(),
            ab_testing=ABTestingSettings.from_env(),
            multi_language=MultiLanguageSettings.from_env(),
        )
        cfg.log_configuration()
        return cfg

    def log_configuration(self) -> None:
        """Log full configuration for debugging and auditing. Requirements: 15.7, 15.9"""
        logger.info("=" * 70)
        logger.info("Alice Conversation Fluidity Enhancement — Configuration")
        logger.info("=" * 70)
        logger.info(f"STT Provider       : {self.stt.provider_type} "
                    f"(enabled={self.stt.enabled})")
        logger.info(f"Neural Turn Detector: enabled={self.neural_turn_detector.enabled}, "
                    f"threshold={self.neural_turn_detector.confidence_threshold}, "
                    f"min_silence={self.neural_turn_detector.min_turn_silence_ms}ms")
        logger.info(f"Interruption Cls   : enabled={self.interruption_classifier.enabled}, "
                    f"min_dur={self.interruption_classifier.min_interruption_duration_ms}ms, "
                    f"energy_thr={self.interruption_classifier.speech_energy_threshold}")
        logger.info(f"Cost Monitor       : enabled={self.cost_monitor.enabled}, "
                    f"target=${self.cost_monitor.target_cost_per_agent_minute:.3f}/agent-min")
        logger.info(f"A/B Testing        : enabled={self.ab_testing.enabled}")
        logger.info(f"Multi-Language     : enabled={self.multi_language.enabled}, "
                    f"langs={self.multi_language.supported_languages}")
        logger.info("=" * 70)

    def to_dict(self) -> Dict[str, Any]:
        """Export full config as nested dict."""
        from dataclasses import asdict
        return asdict(self)

    def supports_neural_turn_detection(self) -> bool:
        """True when neural turn detection can be used (API key + enabled flag)."""
        return self.stt.enabled and self.neural_turn_detector.enabled

    def update_neural_threshold(self, new_threshold: float) -> None:
        """
        Runtime update for confidence threshold (safe to call at any time).

        Requirements: 15.7
        """
        if not 0.0 <= new_threshold <= 1.0:
            logger.warning(f"[Config] Ignoring invalid threshold update: {new_threshold}")
            return
        old = self.neural_turn_detector.confidence_threshold
        self.neural_turn_detector.confidence_threshold = new_threshold
        logger.info(f"[Config] Confidence threshold updated: {old} → {new_threshold}")


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_global_config: Optional[FluidityConfig] = None


def get_fluidity_config() -> FluidityConfig:
    """
    Get or create the global FluidityConfig singleton.

    Requirements: 15.1
    """
    global _global_config
    if _global_config is None:
        _global_config = FluidityConfig.from_env()
    return _global_config


def reset_fluidity_config() -> None:
    """Reset global config (mainly for testing)."""
    global _global_config
    _global_config = None
