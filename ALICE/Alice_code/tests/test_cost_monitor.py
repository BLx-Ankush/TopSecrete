"""
Tests for CostMonitor — unit + alerting tests.

Requirements coverage: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7
"""

import sys
import os
import asyncio

_CODE = os.path.dirname(os.path.dirname(__file__))
if _CODE not in sys.path:
    sys.path.insert(0, _CODE)

import pytest
import logging

try:
    from cost_monitor import CostMonitor, get_cost_monitor, reset_cost_monitor
    COST_MONITOR_AVAILABLE = True
except ImportError as e:
    COST_MONITOR_AVAILABLE = False
    pytest.skip(f"cost_monitor not available: {e}", allow_module_level=True)


def make_monitor(**kwargs) -> CostMonitor:
    return CostMonitor(
        stt_cost_per_minute=0.0015,
        gemini_cost_per_minute=0.0285,
        target_cost_per_agent_minute=0.030,
        felicia_baseline_cost=0.090,
        conversation_id="test-session",
        **kwargs,
    )


class TestCostMonitorInit:

    def test_init(self):
        monitor = make_monitor()
        assert monitor.stt_cost_per_minute == 0.0015
        assert monitor.gemini_cost_per_minute == 0.0285
        assert monitor.target_cost_per_agent_minute == 0.030
        assert monitor.felicia_baseline_cost == 0.090

    def test_disabled(self):
        monitor = make_monitor(enabled=False)
        assert not monitor.enabled


class TestCostTracking:

    @pytest.mark.asyncio
    async def test_track_stt_usage_accumulates(self):
        monitor = make_monitor()
        await monitor.track_stt_usage(60.0)   # 1 minute
        await monitor.track_stt_usage(30.0)   # 0.5 minute
        # Total = 1.5 minutes of STT
        breakdown = await monitor.get_cost_breakdown()
        assert abs(breakdown["stt_minutes"] - 1.5) < 0.001

    @pytest.mark.asyncio
    async def test_track_gemini_usage_accumulates(self):
        monitor = make_monitor()
        await monitor.track_gemini_usage(120.0)   # 2 minutes
        breakdown = await monitor.get_cost_breakdown()
        assert abs(breakdown["gemini_minutes"] - 2.0) < 0.001

    @pytest.mark.asyncio
    async def test_zero_usage_ignored(self):
        monitor = make_monitor()
        await monitor.track_stt_usage(0.0)
        await monitor.track_gemini_usage(-10.0)
        breakdown = await monitor.get_cost_breakdown()
        assert breakdown["stt_minutes"] == 0.0
        assert breakdown["gemini_minutes"] == 0.0

    @pytest.mark.asyncio
    async def test_disabled_monitor_ignores_usage(self):
        monitor = make_monitor(enabled=False)
        await monitor.track_stt_usage(600.0)
        await monitor.track_gemini_usage(600.0)
        cost = await monitor.get_cost_per_agent_minute()
        assert cost == 0.0


class TestCostCalculations:

    @pytest.mark.asyncio
    async def test_cost_per_agent_minute_no_usage(self):
        monitor = make_monitor()
        cost = await monitor.get_cost_per_agent_minute()
        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_cost_only_gemini(self):
        """1 minute Gemini with no STT."""
        monitor = make_monitor()
        await monitor.track_gemini_usage(60.0)
        cost = await monitor.get_cost_per_agent_minute()
        assert abs(cost - 0.0285) < 1e-6

    @pytest.mark.asyncio
    async def test_cost_with_stt_and_gemini(self):
        """
        1 minute of Gemini + 1 minute of STT:
        STT: 1 min × $0.0015 = $0.0015
        Gemini: 1 min × $0.0285 = $0.0285
        Total: $0.0300 / 1 agent-minute = $0.0300
        """
        monitor = make_monitor()
        await monitor.track_stt_usage(60.0)
        await monitor.track_gemini_usage(60.0)
        cost = await monitor.get_cost_per_agent_minute()
        assert abs(cost - 0.030) < 1e-6

    @pytest.mark.asyncio
    async def test_cost_breakdown_complete(self):
        monitor = make_monitor()
        await monitor.track_stt_usage(60.0)
        await monitor.track_gemini_usage(60.0)
        breakdown = await monitor.get_cost_breakdown()
        required_keys = [
            "stt_minutes", "gemini_minutes", "stt_cost_usd",
            "gemini_cost_usd", "total_cost_usd", "cost_per_agent_minute_usd"
        ]
        for key in required_keys:
            assert key in breakdown, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_cost_breakdown_values(self):
        monitor = make_monitor()
        await monitor.track_stt_usage(60.0)
        await monitor.track_gemini_usage(60.0)
        breakdown = await monitor.get_cost_breakdown()
        assert abs(breakdown["stt_cost_usd"] - 0.0015) < 1e-6
        assert abs(breakdown["gemini_cost_usd"] - 0.0285) < 1e-6
        assert abs(breakdown["total_cost_usd"] - 0.030) < 1e-6


class TestCostComparison:

    @pytest.mark.asyncio
    async def test_within_budget_when_cheap(self):
        monitor = make_monitor()
        await monitor.track_gemini_usage(60.0)  # only Gemini, no STT
        comparison = await monitor.get_cost_comparison()
        assert comparison["within_budget"] is True

    @pytest.mark.asyncio
    async def test_comparison_has_savings(self):
        """Alice at $0.030/min vs Felicia at $0.090/min = 66.7% savings."""
        monitor = make_monitor()
        await monitor.track_stt_usage(60.0)
        await monitor.track_gemini_usage(60.0)
        comparison = await monitor.get_cost_comparison()
        assert abs(comparison["savings_percentage"] - 66.7) < 0.5

    @pytest.mark.asyncio
    async def test_comparison_over_budget(self):
        """Force an over-budget scenario."""
        monitor = CostMonitor(
            stt_cost_per_minute=0.020,    # expensive STT
            gemini_cost_per_minute=0.020,
            target_cost_per_agent_minute=0.030,
            felicia_baseline_cost=0.090,
            conversation_id="test",
        )
        await monitor.track_stt_usage(60.0)
        await monitor.track_gemini_usage(60.0)
        comparison = await monitor.get_cost_comparison()
        assert comparison["within_budget"] is False

    @pytest.mark.asyncio
    async def test_comparison_fields_present(self):
        monitor = make_monitor()
        await monitor.track_gemini_usage(60.0)
        comparison = await monitor.get_cost_comparison()
        expected_keys = [
            "alice_cost_per_agent_minute",
            "felicia_baseline_per_agent_minute",
            "target_per_agent_minute",
            "savings_usd",
            "savings_percentage",
            "within_budget",
        ]
        for key in expected_keys:
            assert key in comparison, f"Missing key: {key}"


class TestCostAlert:

    @pytest.mark.asyncio
    async def test_alert_logged_when_over_budget(self, caplog):
        """WARNING should be emitted when cost exceeds target."""
        monitor = CostMonitor(
            stt_cost_per_minute=0.020,
            gemini_cost_per_minute=0.020,
            target_cost_per_agent_minute=0.030,
            felicia_baseline_cost=0.090,
            conversation_id="test-alert",
        )
        with caplog.at_level(logging.WARNING, logger="cost_monitor"):
            await monitor.track_stt_usage(60.0)
            await monitor.track_gemini_usage(60.0)

        assert any("COST ALERT" in rec.message for rec in caplog.records)

    @pytest.mark.asyncio
    async def test_no_alert_when_within_budget(self, caplog):
        monitor = make_monitor()
        with caplog.at_level(logging.WARNING):
            await monitor.track_stt_usage(60.0)
            await monitor.track_gemini_usage(60.0)
        # At $0.030/agent-min exactly, should be within budget — no COST ALERT
        cost = await monitor.get_cost_per_agent_minute()
        assert cost <= monitor.target_cost_per_agent_minute + 1e-9
        assert not any("COST ALERT" in rec.message for rec in caplog.records)


class TestCostMetricsDataclass:

    @pytest.mark.asyncio
    async def test_get_cost_metrics(self):
        monitor = make_monitor()
        await monitor.track_stt_usage(60.0)
        await monitor.track_gemini_usage(60.0)
        metrics = await monitor.get_cost_metrics()
        assert metrics.conversation_id == "test-session"
        assert abs(metrics.stt_audio_minutes - 1.0) < 0.001
        assert abs(metrics.gemini_agent_minutes - 1.0) < 0.001
        assert metrics.timestamp_ms > 0

    @pytest.mark.asyncio
    async def test_export_metrics(self):
        monitor = make_monitor()
        await monitor.track_gemini_usage(60.0)
        export = await monitor.export_metrics()
        assert "enabled" in export
        assert "conversation_id" in export
        assert "breakdown" in export
        assert "comparison" in export
        assert "rates" in export


class TestGlobalMonitor:

    def setup_method(self):
        reset_cost_monitor()

    def teardown_method(self):
        reset_cost_monitor()

    def test_get_creates_singleton(self):
        m1 = get_cost_monitor("sess-1")
        m2 = get_cost_monitor("sess-1")
        assert m1 is m2

    def test_different_conversation_id_creates_new(self):
        m1 = get_cost_monitor("sess-a")
        m2 = get_cost_monitor("sess-b")
        assert m1 is not m2

    def test_reset_clears_singleton(self):
        m1 = get_cost_monitor("sess-1")
        reset_cost_monitor()
        m2 = get_cost_monitor("sess-1")
        assert m1 is not m2
