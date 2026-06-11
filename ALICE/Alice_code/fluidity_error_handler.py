"""
Centralized Error Handler for Alice Conversation Fluidity Enhancement.

Provides structured error handling for all new components with:
  - Mandatory conversation_id in all logs
  - Stack traces for initialization failures
  - Error metrics tracking (count by type + component)
  - Dashboard export for alerting

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7
"""

from __future__ import annotations

import logging
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error type constants
# ---------------------------------------------------------------------------

class ErrorType:
    INITIALIZATION_FAILURE = "initialization_failure"
    CONNECTION_FAILURE = "connection_failure"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    AUDIO_FORMAT_ERROR = "audio_format_error"
    PROCESSING_ERROR = "processing_error"
    HEALTH_CHECK_FAILURE = "health_check_failure"
    CLASSIFICATION_TIMEOUT = "classification_timeout"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


class ComponentType:
    NEURAL_TURN_DETECTOR = "NeuralTurnDetector"
    INTERRUPTION_CLASSIFIER = "InterruptionClassifier"
    STT_PROVIDER = "STTProvider"
    COST_MONITOR = "CostMonitor"
    LATENCY_MONITOR = "LatencyMonitor"


# ---------------------------------------------------------------------------
# Error record
# ---------------------------------------------------------------------------

@dataclass
class FluidityError:
    """
    Structured error record with all required context.

    Requirements: 14.6, 14.7
    """
    timestamp_ms: int
    component: str
    error_type: str
    message: str
    conversation_id: str
    stack_trace: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_log_str(self) -> str:
        parts = [
            f"[{self.component}] {self.error_type.upper()}",
            f"conversation_id={self.conversation_id!r}",
            f"message={self.message!r}",
        ]
        if self.extra:
            for k, v in self.extra.items():
                parts.append(f"{k}={v!r}")
        if self.stack_trace:
            parts.append(f"stack_trace={self.stack_trace!r}")
        return " | ".join(parts)


# ---------------------------------------------------------------------------
# Error metrics tracker
# ---------------------------------------------------------------------------

@dataclass
class ErrorMetrics:
    """
    Tracks error counts by type and component for monitoring dashboard.

    Requirements: 14.7
    """
    counts: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    recent_errors: List[FluidityError] = field(default_factory=list)
    _max_recent: int = 100

    def record(self, error: FluidityError) -> None:
        self.counts[error.component][error.error_type] += 1
        self.recent_errors.append(error)
        if len(self.recent_errors) > self._max_recent:
            self.recent_errors = self.recent_errors[-self._max_recent:]

    def get_error_rate(self, component: str, window_s: float = 60.0) -> float:
        """Errors per second for component in last window_s seconds."""
        cutoff = int((time.time() - window_s) * 1000)
        count = sum(
            1 for e in self.recent_errors
            if e.component == component and e.timestamp_ms >= cutoff
        )
        return count / window_s

    def export_metrics(self) -> Dict[str, Any]:
        """Export for monitoring dashboard."""
        return {
            "counts": {
                comp: dict(types)
                for comp, types in self.counts.items()
            },
            "total_errors": sum(
                sum(t.values()) for t in self.counts.values()
            ),
            "recent_error_count": len(self.recent_errors),
        }


# ---------------------------------------------------------------------------
# Main error handler
# ---------------------------------------------------------------------------

class FluidityErrorHandler:
    """
    Centralized error handler for the fluidity enhancement feature.

    Usage::

        handler = FluidityErrorHandler(conversation_id="session-123")
        handler.handle_stt_error(exc, retry_count=2)

    Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7
    """

    def __init__(self, conversation_id: str = ""):
        self.conversation_id = conversation_id
        self.metrics = ErrorMetrics()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_error(
        self,
        component: str,
        error_type: str,
        exc: Exception,
        extra: Dict[str, Any],
    ) -> FluidityError:
        return FluidityError(
            timestamp_ms=int(time.time() * 1000),
            component=component,
            error_type=error_type,
            message=str(exc),
            conversation_id=self.conversation_id,
            stack_trace=traceback.format_exc(),
            extra=extra,
        )

    def _log_and_record(self, error: FluidityError, level: int = logging.ERROR) -> None:
        logger.log(level, error.to_log_str())
        self.metrics.record(error)

    # ------------------------------------------------------------------
    # NeuralTurnDetector errors  (Requirements: 14.1)
    # ------------------------------------------------------------------

    def handle_neural_detector_init_failure(
        self,
        exc: Exception,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Handle NeuralTurnDetector initialization failure with stack trace."""
        error = self._build_error(
            ComponentType.NEURAL_TURN_DETECTOR,
            ErrorType.INITIALIZATION_FAILURE,
            exc,
            extra or {},
        )
        self._log_and_record(error)

    def handle_neural_detector_processing_error(
        self,
        exc: Exception,
        audio_format_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Handle audio processing error with audio format context."""
        extra = audio_format_details or {}
        error = self._build_error(
            ComponentType.NEURAL_TURN_DETECTOR,
            ErrorType.PROCESSING_ERROR,
            exc,
            extra,
        )
        self._log_and_record(error)

    def handle_neural_detector_health_check_failure(
        self,
        exc: Exception,
        retry_count: int = 0,
    ) -> None:
        """Handle health check failure with retry count."""
        error = self._build_error(
            ComponentType.NEURAL_TURN_DETECTOR,
            ErrorType.HEALTH_CHECK_FAILURE,
            exc,
            {"retry_count": retry_count},
        )
        self._log_and_record(error, logging.WARNING)

    # ------------------------------------------------------------------
    # InterruptionClassifier errors  (Requirements: 14.2)
    # ------------------------------------------------------------------

    def handle_classifier_init_failure(
        self,
        exc: Exception,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Handle InterruptionClassifier initialization failure."""
        error = self._build_error(
            ComponentType.INTERRUPTION_CLASSIFIER,
            ErrorType.INITIALIZATION_FAILURE,
            exc,
            extra or {},
        )
        self._log_and_record(error)

    def handle_classifier_error(
        self,
        exc: Exception,
        audio_duration_ms: float = 0,
        audio_energy: float = 0,
    ) -> None:
        """Handle classification error with audio details."""
        error = self._build_error(
            ComponentType.INTERRUPTION_CLASSIFIER,
            ErrorType.PROCESSING_ERROR,
            exc,
            {
                "audio_duration_ms": audio_duration_ms,
                "audio_energy": audio_energy,
            },
        )
        self._log_and_record(error)

    def handle_classifier_timeout(
        self,
        timeout_ms: float,
        audio_duration_ms: float = 0,
    ) -> None:
        """Handle classification timeout."""
        error = FluidityError(
            timestamp_ms=int(time.time() * 1000),
            component=ComponentType.INTERRUPTION_CLASSIFIER,
            error_type=ErrorType.CLASSIFICATION_TIMEOUT,
            message=f"Classification exceeded {timeout_ms}ms timeout",
            conversation_id=self.conversation_id,
            extra={"timeout_ms": timeout_ms, "audio_duration_ms": audio_duration_ms},
        )
        self._log_and_record(error, logging.WARNING)

    # ------------------------------------------------------------------
    # STT Provider errors  (Requirements: 14.3, 14.4, 14.5)
    # ------------------------------------------------------------------

    def handle_stt_connection_failure(
        self,
        exc: Exception,
        retry_count: int = 0,
        provider: str = "unknown",
    ) -> None:
        """Handle STT connection failure with retry count."""
        error = self._build_error(
            ComponentType.STT_PROVIDER,
            ErrorType.CONNECTION_FAILURE,
            exc,
            {"retry_count": retry_count, "provider": provider},
        )
        self._log_and_record(error)

    def handle_stt_auth_error(
        self,
        exc: Exception,
        provider: str = "unknown",
    ) -> None:
        """Handle STT authentication error (invalid API key)."""
        error = self._build_error(
            ComponentType.STT_PROVIDER,
            ErrorType.AUTHENTICATION_ERROR,
            exc,
            {"provider": provider, "hint": "Check API key in .env file"},
        )
        self._log_and_record(error)

    def handle_stt_rate_limit(
        self,
        exc: Exception,
        retry_after_s: float = 0,
        provider: str = "unknown",
    ) -> None:
        """Handle STT rate limit error with retry-after time."""
        error = self._build_error(
            ComponentType.STT_PROVIDER,
            ErrorType.RATE_LIMIT_ERROR,
            exc,
            {"retry_after_s": retry_after_s, "provider": provider},
        )
        self._log_and_record(error, logging.WARNING)

    def handle_stt_audio_format_error(
        self,
        exc: Exception,
        expected_format: Dict[str, Any],
        actual_format: Dict[str, Any],
    ) -> None:
        """Handle audio format mismatch with format details."""
        error = self._build_error(
            ComponentType.STT_PROVIDER,
            ErrorType.AUDIO_FORMAT_ERROR,
            exc,
            {
                "expected": expected_format,
                "actual": actual_format,
            },
        )
        self._log_and_record(error)

    # ------------------------------------------------------------------
    # Generic handler
    # ------------------------------------------------------------------

    def handle_generic(
        self,
        component: str,
        exc: Exception,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Catch-all handler for unexpected errors."""
        error = self._build_error(
            component,
            ErrorType.UNKNOWN_ERROR,
            exc,
            extra or {},
        )
        self._log_and_record(error)

    # ------------------------------------------------------------------
    # Metrics export
    # ------------------------------------------------------------------

    def export_metrics(self) -> Dict[str, Any]:
        """Export error metrics for monitoring dashboard. Requirements: 14.7"""
        return self.metrics.export_metrics()

    def get_recent_errors(self, component: str = None) -> List[Dict[str, Any]]:
        """Return recent errors, optionally filtered by component."""
        errors = self.metrics.recent_errors
        if component:
            errors = [e for e in errors if e.component == component]
        return [e.to_dict() for e in errors]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_global_handler: Optional[FluidityErrorHandler] = None


def get_error_handler(conversation_id: str = "") -> FluidityErrorHandler:
    """Get or create the global error handler."""
    global _global_handler
    if _global_handler is None or (conversation_id and
                                    _global_handler.conversation_id != conversation_id):
        _global_handler = FluidityErrorHandler(conversation_id=conversation_id)
    return _global_handler


def reset_error_handler() -> None:
    """Reset global error handler (mainly for testing)."""
    global _global_handler
    _global_handler = None
