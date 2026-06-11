"""
Tests for VADThresholdManager — unit + property tests.

Property tests verify:
  Property 3: All thresholds stay in [min_threshold, max_threshold]
  Property 4: Higher noise → equal or higher threshold (monotonicity)

Requirements coverage: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

import sys
import os
import asyncio

_CODE = os.path.dirname(os.path.dirname(__file__))
if _CODE not in sys.path:
    sys.path.insert(0, _CODE)

import pytest

try:
    from vad_config import VADThresholdManager
    MANAGER_AVAILABLE = True
except ImportError:
    MANAGER_AVAILABLE = False
    pytest.skip("VADThresholdManager not available", allow_module_level=True)


class TestVADThresholdManagerInit:

    def test_init_default(self):
        mgr = VADThresholdManager(0.3, 0.6, 0.4)
        assert mgr.min_threshold == 0.3
        assert mgr.max_threshold == 0.6
        assert mgr.get_current_threshold_sync() == 0.4

    def test_init_validates_bounds(self):
        with pytest.raises(ValueError):
            VADThresholdManager(min_threshold=0.7, max_threshold=0.3)

    def test_init_validates_default_in_range(self):
        with pytest.raises(ValueError):
            VADThresholdManager(min_threshold=0.3, max_threshold=0.6, default_threshold=0.8)

    def test_init_equal_min_max_fails(self):
        with pytest.raises(ValueError):
            VADThresholdManager(min_threshold=0.4, max_threshold=0.4)

    def test_init_negative_min_fails(self):
        with pytest.raises(ValueError):
            VADThresholdManager(min_threshold=-0.1, max_threshold=0.6)


class TestPropertyThree:
    """Property 3: Threshold always in [min_threshold, max_threshold]."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("noise_level", [
        -1.0, -0.5, 0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0, 1.5, 2.0
    ])
    async def test_threshold_always_in_range(self, noise_level):
        mgr = VADThresholdManager(0.3, 0.6, 0.4)
        result = await mgr.adjust_threshold(noise_level)
        assert 0.3 <= result <= 0.6, (
            f"Threshold {result} out of range [0.3, 0.6] for noise_level={noise_level}"
        )

    @pytest.mark.asyncio
    async def test_extreme_noise_gives_max(self):
        mgr = VADThresholdManager(0.3, 0.6, 0.4)
        result = await mgr.adjust_threshold(1.0)
        assert abs(result - 0.6) < 1e-9

    @pytest.mark.asyncio
    async def test_zero_noise_gives_min(self):
        mgr = VADThresholdManager(0.3, 0.6, 0.4)
        result = await mgr.adjust_threshold(0.0)
        assert abs(result - 0.3) < 1e-9

    @pytest.mark.asyncio
    async def test_overflowing_noise_clamped_to_max(self):
        mgr = VADThresholdManager(0.3, 0.6, 0.4)
        result = await mgr.adjust_threshold(999.0)
        assert result <= 0.6

    @pytest.mark.asyncio
    async def test_negative_noise_clamped_to_min(self):
        mgr = VADThresholdManager(0.3, 0.6, 0.4)
        result = await mgr.adjust_threshold(-999.0)
        assert result >= 0.3


class TestPropertyFour:
    """Property 4: Higher noise level → equal or higher threshold (monotonicity)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("low,high", [
        (0.0, 0.1), (0.1, 0.5), (0.3, 0.7), (0.5, 1.0),
        (0.0, 1.0), (0.2, 0.8), (0.4, 0.6),
    ])
    async def test_monotonic_with_noise(self, low, high):
        mgr = VADThresholdManager(0.3, 0.6, 0.4)
        t_low = await mgr.adjust_threshold(low)
        mgr2 = VADThresholdManager(0.3, 0.6, 0.4)
        t_high = await mgr2.adjust_threshold(high)
        assert t_low <= t_high + 1e-9, (
            f"Monotonicity violated: noise {low}→{t_low:.4f}, "
            f"noise {high}→{t_high:.4f}"
        )


class TestDetectorTypes:

    @pytest.mark.asyncio
    async def test_neural_threshold(self):
        mgr = VADThresholdManager(0.3, 0.6, 0.4)
        result = await mgr.get_neural_threshold(0.5)
        assert 0.3 <= result <= 0.6

    @pytest.mark.asyncio
    async def test_silero_threshold(self):
        mgr = VADThresholdManager(0.3, 0.6, 0.4)
        result = await mgr.get_silero_threshold(0.5)
        assert 0.3 <= result <= 0.6

    @pytest.mark.asyncio
    async def test_both_types_give_same_result_for_same_noise(self):
        """Both detector types produce same threshold for same noise level."""
        noise = 0.6
        mgr_n = VADThresholdManager(0.3, 0.6, 0.4)
        mgr_s = VADThresholdManager(0.3, 0.6, 0.4)
        t_neural = await mgr_n.get_neural_threshold(noise)
        t_silero = await mgr_s.get_silero_threshold(noise)
        assert abs(t_neural - t_silero) < 1e-9


class TestCurrentThreshold:

    @pytest.mark.asyncio
    async def test_get_current_threshold(self):
        mgr = VADThresholdManager(0.3, 0.6, 0.4)
        threshold = await mgr.get_current_threshold()
        assert threshold == 0.4

    @pytest.mark.asyncio
    async def test_threshold_updates_after_adjust(self):
        mgr = VADThresholdManager(0.3, 0.6, 0.4)
        await mgr.adjust_threshold(1.0)
        threshold = await mgr.get_current_threshold()
        assert abs(threshold - 0.6) < 1e-9

    def test_sync_accessor(self):
        mgr = VADThresholdManager(0.3, 0.6, 0.45)
        assert mgr.get_current_threshold_sync() == 0.45


class TestStatus:

    def test_get_status_has_all_fields(self):
        mgr = VADThresholdManager(0.3, 0.6, 0.4)
        status = mgr.get_status()
        assert "current_threshold" in status
        assert "min_threshold" in status
        assert "max_threshold" in status
        assert "last_noise_level" in status

    @pytest.mark.asyncio
    async def test_status_reflects_last_noise(self):
        mgr = VADThresholdManager(0.3, 0.6, 0.4)
        await mgr.adjust_threshold(0.7)
        status = mgr.get_status()
        assert status["last_noise_level"] == 0.7

    @pytest.mark.asyncio
    async def test_custom_range(self):
        """Test with custom [0.2, 0.8] range."""
        mgr = VADThresholdManager(0.2, 0.8, 0.5)
        for noise in [0.0, 0.25, 0.5, 0.75, 1.0]:
            result = await mgr.adjust_threshold(noise)
            assert 0.2 <= result <= 0.8, f"Out of [0.2, 0.8] for noise={noise}"
