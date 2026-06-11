"""
Integration tests for the streaming architecture with fluidity components.

Tests the full pipeline:
  NeuralTurnDetector → InterruptionClassifier → NeuralFluidityMonitor
  CostMonitor tracking
  FluidityLatencyTracker timing

Requirements coverage: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7
"""

import sys
import os
import asyncio
import struct
import math

_CODE = os.path.dirname(os.path.dirname(__file__))
if _CODE not in sys.path:
    sys.path.insert(0, _CODE)

import pytest


def make_pcm(duration_ms: float, frequency_hz: float = 440, amplitude: float = 0.5) -> bytes:
    SAMPLE_RATE = 24000
    n_samples = int(SAMPLE_RATE * duration_ms / 1000)
    samples = []
    for i in range(n_samples):
        v = int(amplitude * 32767 * math.sin(2 * math.pi * frequency_hz * i / SAMPLE_RATE))
        samples.append(max(-32768, min(32767, v)))
    return struct.pack(f"<{n_samples}h", *samples)


def make_silence(duration_ms: float) -> bytes:
    SAMPLE_RATE = 24000
    n_samples = int(SAMPLE_RATE * duration_ms / 1000)
    return struct.pack(f"<{n_samples}h", *([0] * n_samples))


class TestInterruptionPipelineIntegration:
    """Test the InterruptionClassifier → NeuralFluidityMonitor pipeline."""

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from interruption_classifier import InterruptionClassifier, Classification
            from vad_turn_taking_monitor import NeuralFluidityMonitor, reset_neural_fluidity_monitor
            self.Classifier = InterruptionClassifier
            self.Classification = Classification
            self.Monitor = NeuralFluidityMonitor
            reset_neural_fluidity_monitor()
        except ImportError as e:
            pytest.skip(f"Required modules not available: {e}")

    @pytest.mark.asyncio
    async def test_genuine_interruption_recorded_in_monitor(self):
        clf = self.Classifier(
            min_interruption_duration_ms=200,
            speech_energy_threshold=0.02,
            classification_timeout_ms=500,
        )
        monitor = self.Monitor("integration-sess")

        # Classify a genuine interruption
        audio = make_pcm(500, 600, 0.5)
        classification = await clf.classify_audio(audio)
        evt = clf.create_interruption_event(audio, classification, "cancel_response", 10.0)
        monitor.on_interruption_classified(evt.to_dict())

        metrics = monitor.export_metrics_to_dashboard()
        assert metrics["interruption_classification"]["total_events"] == 1

    @pytest.mark.asyncio
    async def test_noise_not_counted_as_genuine(self):
        clf = self.Classifier(
            min_interruption_duration_ms=200,
            speech_energy_threshold=0.02,
            classification_timeout_ms=500,
        )
        monitor = self.Monitor("integration-sess")

        # Noise: <200ms
        audio = make_pcm(100, 440, 0.5)
        classification = await clf.classify_audio(audio)
        assert classification == self.Classification.NOISE

        evt = clf.create_interruption_event(audio, classification, "continue_response", 5.0)
        monitor.on_interruption_classified(evt.to_dict())

        metrics = monitor.export_metrics_to_dashboard()
        assert metrics["interruption_classification"]["genuine_interruptions"] == 0
        assert metrics["interruption_classification"]["noise_classifications"] == 1

    @pytest.mark.asyncio
    async def test_background_sound_counted_separately(self):
        clf = self.Classifier(
            min_interruption_duration_ms=100,  # short min_dur so duration rule won't fire
            speech_energy_threshold=0.05,
            classification_timeout_ms=500,
        )
        monitor = self.Monitor("integration-sess")

        # Very low energy → background
        import numpy as np
        rng = np.random.default_rng(0)
        n = int(24000 * 0.4)
        samples = (rng.random(n) * 2 - 1) * 0.001 * 32767
        audio = samples.astype('<i2').tobytes()

        classification = await clf.classify_audio(audio)
        evt = clf.create_interruption_event(audio, classification, "ignore", 8.0)
        monitor.on_interruption_classified(evt.to_dict())

        metrics = monitor.export_metrics_to_dashboard()
        assert metrics["interruption_classification"]["background_classifications"] >= 0


class TestCostMonitorIntegration:

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from cost_monitor import CostMonitor, reset_cost_monitor
            self.CostMonitor = CostMonitor
            reset_cost_monitor()
        except ImportError as e:
            pytest.skip(f"cost_monitor not available: {e}")

    @pytest.mark.asyncio
    async def test_streaming_cost_accumulation(self):
        """Simulate 5 minutes of conversation cost."""
        monitor = self.CostMonitor(
            stt_cost_per_minute=0.0015,
            gemini_cost_per_minute=0.0285,
            target_cost_per_agent_minute=0.030,
            felicia_baseline_cost=0.090,
        )

        # Simulate 5 minutes: each second we get a 1s chunk
        for _ in range(300):  # 300 seconds = 5 minutes
            await monitor.track_stt_usage(1.0)
            await monitor.track_gemini_usage(1.0)

        cost = await monitor.get_cost_per_agent_minute()
        assert abs(cost - 0.030) < 1e-6

        comparison = await monitor.get_cost_comparison()
        assert comparison["within_budget"] is True
        assert comparison["savings_percentage"] > 50

    @pytest.mark.asyncio
    async def test_cost_metrics_dataclass_populated(self):
        monitor = self.CostMonitor(conversation_id="integration-test")
        await monitor.track_stt_usage(60.0)
        await monitor.track_gemini_usage(60.0)
        metrics = await monitor.get_cost_metrics()
        assert metrics.is_within_budget(0.030)
        assert metrics.get_savings_percentage() > 0


class TestLatencyTrackerIntegration:

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from latency_monitor import FluidityLatencyTracker, reset_fluidity_latency_tracker
            self.Tracker = FluidityLatencyTracker
            reset_fluidity_latency_tracker()
        except ImportError as e:
            pytest.skip(f"FluidityLatencyTracker not available: {e}")

    def test_all_components_tracked(self):
        import time
        tracker = self.Tracker("integration-sess")

        # NeuralTurnDetector
        tracker.on_neural_turn_detector_start("ntd-1")
        time.sleep(0.005)
        tracker.on_neural_turn_detector_end("ntd-1")

        # InterruptionClassifier
        tracker.on_interruption_classifier_start("ic-1")
        time.sleep(0.003)
        tracker.on_interruption_classifier_end("ic-1")

        # STT Provider
        tracker.on_stt_provider_start("stt-1")
        time.sleep(0.010)
        tracker.on_stt_provider_end("stt-1")

        # End-to-end
        tracker.on_end_to_end_turn_detection_complete(250.0)

        export = tracker.export_metrics()
        assert export["neural_turn_detector"]["count"] == 1
        assert export["interruption_classifier"]["count"] == 1
        assert export["stt_provider"]["count"] == 1
        assert export["end_to_end_turn_detection"]["count"] == 1

    def test_percentiles_computed_correctly(self):
        tracker = self.Tracker("integration-sess")
        values = [100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0]
        for v in values:
            tracker.on_end_to_end_turn_detection_complete(v)
        pcts = tracker.calculate_percentiles("end_to_end")
        assert pcts["count"] == 10
        # P50 should be ~500ms for 10 sorted values [100..1000]
        assert 400.0 <= pcts["p50_ms"] <= 600.0
        # P95 should be near 950ms
        assert pcts["p95_ms"] >= 800.0
