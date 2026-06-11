"""
Cost Monitor for Alice Conversation Fluidity Enhancement.

Tracks API usage and calculates cost per agent-minute for:
  - STT Provider (AssemblyAI or Deepgram)
  - Gemini Multimodal Live API

Compares cost against:
  - Target: $0.030/agent-minute
  - Felicia baseline: $0.090/agent-minute (3× Alice's target)

Emits WARNING logs when cost exceeds target.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

from fluidity_models import CostMetrics

logger = logging.getLogger(__name__)


@dataclass
class _UsageAccumulator:
    stt_audio_seconds: float = 0.0
    gemini_agent_seconds: float = 0.0
    conversation_start: float = field(default_factory=time.time)
    last_alert_time: float = 0.0

    def stt_minutes(self) -> float:
        return self.stt_audio_seconds / 60.0

    def gemini_minutes(self) -> float:
        return self.gemini_agent_seconds / 60.0

    def elapsed_agent_minutes(self) -> float:
        return (time.time() - self.conversation_start) / 60.0


class CostMonitor:
    """
    Monitor and alert on API costs per agent-minute.

    Usage::

        monitor = CostMonitor(conversation_id="session-abc")
        await monitor.track_stt_usage(20.0)          # 20 seconds of STT
        await monitor.track_gemini_usage(20.0)        # 20 seconds of Gemini
        cost = await monitor.get_cost_per_agent_minute()

    Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7
    """

    # Default cost rates (USD per minute)
    DEFAULT_STT_COST_PER_MINUTE = 0.0015       # AssemblyAI Universal-3 Pro
    DEFAULT_GEMINI_COST_PER_MINUTE = 0.0285    # Gemini 2.5 Flash audio
    DEFAULT_TARGET_COST = 0.030
    FELICIA_BASELINE_COST = 0.090

    # Alert cooldown: only alert once per this many seconds to avoid log spam
    ALERT_COOLDOWN_S = 60.0

    def __init__(
        self,
        stt_cost_per_minute: float = DEFAULT_STT_COST_PER_MINUTE,
        gemini_cost_per_minute: float = DEFAULT_GEMINI_COST_PER_MINUTE,
        target_cost_per_agent_minute: float = DEFAULT_TARGET_COST,
        felicia_baseline_cost: float = FELICIA_BASELINE_COST,
        conversation_id: str = "",
        enabled: bool = True,
    ):
        """
        Initialize cost monitor.

        Args:
            stt_cost_per_minute:           STT API cost per audio minute (USD)
            gemini_cost_per_minute:        Gemini API cost per agent minute (USD)
            target_cost_per_agent_minute:  Alert threshold (USD/agent-minute)
            felicia_baseline_cost:         Competitor baseline for comparison
            conversation_id:               For log context
            enabled:                       Set False to disable cost tracking

        Requirements: 12.3, 12.5
        """
        self.stt_cost_per_minute = stt_cost_per_minute
        self.gemini_cost_per_minute = gemini_cost_per_minute
        self.target_cost_per_agent_minute = target_cost_per_agent_minute
        self.felicia_baseline_cost = felicia_baseline_cost
        self.conversation_id = conversation_id
        self.enabled = enabled

        self._usage = _UsageAccumulator()

        logger.info(
            f"[CostMonitor] Initialized "
            f"(stt=${stt_cost_per_minute:.4f}/min, "
            f"gemini=${gemini_cost_per_minute:.4f}/min, "
            f"target=${target_cost_per_agent_minute:.3f}/agent-min, "
            f"enabled={enabled})"
        )

    # ------------------------------------------------------------------
    # Usage tracking
    # ------------------------------------------------------------------

    async def track_stt_usage(self, audio_duration_seconds: float) -> None:
        """
        Track STT provider audio processed.

        Args:
            audio_duration_seconds: Duration of audio sent to STT provider

        Requirements: 12.1, 12.6
        """
        if not self.enabled or audio_duration_seconds <= 0:
            return
        self._usage.stt_audio_seconds += audio_duration_seconds
        logger.debug(
            f"[CostMonitor] STT usage +{audio_duration_seconds:.2f}s "
            f"(total={self._usage.stt_audio_seconds:.1f}s)"
        )

    async def track_gemini_usage(self, agent_duration_seconds: float) -> None:
        """
        Track Gemini Multimodal Live API agent time.

        Args:
            agent_duration_seconds: Duration of agent conversation time

        Requirements: 12.2, 12.6
        """
        if not self.enabled or agent_duration_seconds <= 0:
            return
        self._usage.gemini_agent_seconds += agent_duration_seconds
        logger.debug(
            f"[CostMonitor] Gemini usage +{agent_duration_seconds:.2f}s "
            f"(total={self._usage.gemini_agent_seconds:.1f}s)"
        )
        # Check for budget alerts after each Gemini usage update
        await self._check_cost_alert()

    # ------------------------------------------------------------------
    # Cost calculations
    # ------------------------------------------------------------------

    async def get_cost_per_agent_minute(self) -> float:
        """
        Calculate current cost per agent-minute.

        Returns:
            Cost in USD per agent-minute (0.0 if no Gemini time tracked yet)

        Requirements: 12.3
        """
        gemini_minutes = self._usage.gemini_minutes()
        if gemini_minutes == 0:
            return 0.0

        stt_cost = self._usage.stt_minutes() * self.stt_cost_per_minute
        gemini_cost = gemini_minutes * self.gemini_cost_per_minute
        total_cost = stt_cost + gemini_cost

        return total_cost / gemini_minutes

    async def get_cost_breakdown(self) -> Dict[str, float]:
        """
        Get itemised cost breakdown by component.

        Returns:
            Dict with keys: stt_cost, gemini_cost, total_cost,
                            stt_minutes, gemini_minutes

        Requirements: 12.6
        """
        stt_min = self._usage.stt_minutes()
        gem_min = self._usage.gemini_minutes()
        stt_cost = stt_min * self.stt_cost_per_minute
        gem_cost = gem_min * self.gemini_cost_per_minute
        total = stt_cost + gem_cost

        return {
            "stt_minutes": round(stt_min, 4),
            "gemini_minutes": round(gem_min, 4),
            "stt_cost_usd": round(stt_cost, 6),
            "gemini_cost_usd": round(gem_cost, 6),
            "total_cost_usd": round(total, 6),
            "cost_per_agent_minute_usd": round(
                await self.get_cost_per_agent_minute(), 6
            ),
        }

    async def get_cost_comparison(self) -> Dict[str, Any]:
        """
        Compare Alice's cost against Felicia baseline.

        Returns:
            Dict with alice_cost, felicia_cost, savings_usd,
                  savings_percentage, within_budget

        Requirements: 12.4, 12.5, 12.7
        """
        alice_cost = await self.get_cost_per_agent_minute()
        felicia_cost = self.felicia_baseline_cost
        gem_min = self._usage.gemini_minutes()
        savings_usd = (felicia_cost - alice_cost) * gem_min
        within_budget = round(alice_cost, 6) <= self.target_cost_per_agent_minute

        savings_pct = 0.0
        if felicia_cost > 0:
            savings_pct = ((felicia_cost - alice_cost) / felicia_cost) * 100

        return {
            "alice_cost_per_agent_minute": round(alice_cost, 6),
            "felicia_baseline_per_agent_minute": round(felicia_cost, 6),
            "target_per_agent_minute": round(self.target_cost_per_agent_minute, 6),
            "savings_usd": round(savings_usd, 6),
            "savings_percentage": round(savings_pct, 1),
            "within_budget": within_budget,
            "total_gemini_minutes": round(gem_min, 3),
        }

    # ------------------------------------------------------------------
    # CostMetrics dataclass
    # ------------------------------------------------------------------

    async def get_cost_metrics(self) -> CostMetrics:
        """
        Build a CostMetrics dataclass for logging and monitoring dashboard.

        Requirements: 12.1, 12.2
        """
        gem_min = self._usage.gemini_minutes()
        stt_min = self._usage.stt_minutes()
        stt_cost = stt_min * self.stt_cost_per_minute
        gem_cost = gem_min * self.gemini_cost_per_minute
        total = stt_cost + gem_cost
        cost_per_min = await self.get_cost_per_agent_minute()
        savings = (self.felicia_baseline_cost - cost_per_min) * gem_min

        metrics = CostMetrics(
            conversation_id=self.conversation_id,
            timestamp_ms=int(time.time() * 1000),
            stt_audio_minutes=round(stt_min, 4),
            gemini_agent_minutes=round(gem_min, 4),
            stt_cost=round(stt_cost, 6),
            gemini_cost=round(gem_cost, 6),
            total_cost=round(total, 6),
            cost_per_agent_minute=round(cost_per_min, 6),
            felicia_baseline_cost=self.felicia_baseline_cost,
            cost_savings=round(savings, 6),
        )
        return metrics

    # ------------------------------------------------------------------
    # Alerting
    # ------------------------------------------------------------------

    async def _check_cost_alert(self) -> None:
        """
        Emit WARNING when cost exceeds target, with cooldown.

        Requirements: 12.4, 12.7
        """
        cost = await self.get_cost_per_agent_minute()
        if round(cost, 6) > self.target_cost_per_agent_minute:
            now = time.time()
            if now - self._usage.last_alert_time >= self.ALERT_COOLDOWN_S:
                self._usage.last_alert_time = now
                logger.warning(
                    f"[CostMonitor] COST ALERT: "
                    f"${cost:.4f}/agent-min exceeds target "
                    f"${self.target_cost_per_agent_minute:.3f}/agent-min "
                    f"(Felicia baseline: ${self.felicia_baseline_cost:.3f}/agent-min) "
                    f"[conversation_id={self.conversation_id!r}]"
                )

    # ------------------------------------------------------------------
    # Dashboard export
    # ------------------------------------------------------------------

    async def export_metrics(self) -> Dict[str, Any]:
        """
        Export all cost metrics for monitoring dashboard.

        Requirements: 12.7
        """
        breakdown = await self.get_cost_breakdown()
        comparison = await self.get_cost_comparison()
        return {
            "enabled": self.enabled,
            "conversation_id": self.conversation_id,
            "breakdown": breakdown,
            "comparison": comparison,
            "rates": {
                "stt_per_minute_usd": self.stt_cost_per_minute,
                "gemini_per_minute_usd": self.gemini_cost_per_minute,
                "target_per_agent_minute_usd": self.target_cost_per_agent_minute,
            },
        }

    def log_summary(self) -> None:
        """Log a human-readable cost summary."""
        import asyncio

        async def _inner():
            comparison = await self.get_cost_comparison()
            logger.info("=" * 60)
            logger.info("[CostMonitor] Cost Summary")
            logger.info("=" * 60)
            logger.info(f"  Alice cost/agent-min : ${comparison['alice_cost_per_agent_minute']:.4f}")
            logger.info(f"  Felicia baseline     : ${comparison['felicia_baseline_per_agent_minute']:.4f}")
            logger.info(f"  Target               : ${comparison['target_per_agent_minute']:.4f}")
            logger.info(f"  Savings vs Felicia   : ${comparison['savings_usd']:.4f} "
                        f"({comparison['savings_percentage']:.1f}%)")
            logger.info(f"  Within budget        : {comparison['within_budget']}")
            logger.info("=" * 60)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_inner())
            else:
                loop.run_until_complete(_inner())
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_global_cost_monitor: Optional[CostMonitor] = None


def get_cost_monitor(conversation_id: str = "") -> CostMonitor:
    """Get or create the global CostMonitor singleton."""
    global _global_cost_monitor
    if _global_cost_monitor is None or (
        conversation_id and _global_cost_monitor.conversation_id != conversation_id
    ):
        _global_cost_monitor = CostMonitor(conversation_id=conversation_id)
    return _global_cost_monitor


def reset_cost_monitor() -> None:
    """Reset the global cost monitor (mainly for testing)."""
    global _global_cost_monitor
    _global_cost_monitor = None
