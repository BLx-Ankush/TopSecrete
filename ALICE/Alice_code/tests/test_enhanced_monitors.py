"""
Tests for enhanced monitoring components:
  - NeuralFluidityMonitor (vad_turn_taking_monitor.py)
  - FluidityLatencyTracker (latency_monitor.py)
  - FluidityErrorHandler (fluidity_error_handler.py)
  - FluidityConfig (fluidity_config.py)

Requirements coverage: 10.1-10.7, 11.1-11.7, 14.1-14.7, 15.1-15.9
"""

import sys
import os
import time
import asyncio

_CODE = os.path.dirname(os.path.dirname(__file__))
if _CODE not in sys.path:
    sys.path.insert(0, _CODE)

import pytest
import logging


# ===========================================================================
# NeuralFluidityMonitor tests
# ===========================================================================

class TestNeuralFluidityMonitor:

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from vad_turn_taking_monitor import (
                NeuralFluidityMonitor,
                get_neural_fluidity_monitor,
                reset_neural_fluidity_monitor,
            )
            self.Monitor = NeuralFluidityMonitor
            self.get_monitor = get_neural_fluidity_monitor
            self.reset_monitor = reset_neural_fluidity_monitor
            reset_neural_fluidity_monitor()
        except ImportError as e:
            pytest.skip(f"NeuralFluidityMonitor not available: {e}")

    def teardown_method(self, method):
        try:
            self.reset_monitor()
        except Exception:
            pass

    def _make_turn_event(self, triggered=True, confidence=0.7, is_false_trigger=False):
        import uuid
        return {
            "event_id": str(uuid.uuid4()),
            "triggered": triggered,
            "end_of_turn_confidence": confidence,
            "detector_type": "neural",
            "is_false_trigger": is_false_trigger,
        }

    def _make_interruption_event(self, classification="genuine_interruption", is_false=False):
        import uuid
        return {
            "event_id": str(uuid.uuid4()),
            "classification": classification,
            "is_false_interruption": is_false,
        }

    def test_init(self):
        monitor = self.Monitor("test-session")
        assert monitor.session_id == "test-session"

    def test_record_turn_events(self):
        monitor = self.Monitor("sess")
        for _ in range(5):
            monitor.on_neural_turn_detected(self._make_turn_event())
        metrics = monitor.export_metrics_to_dashboard()
        assert metrics["neural_turn_detection"]["total_events"] == 5

    def test_false_trigger_rate_zero_when_none(self):
        monitor = self.Monitor("sess")
        assert monitor.get_false_trigger_rate() == 0.0

    def test_false_trigger_rate_calculation(self):
        monitor = self.Monitor("sess")
        events = [self._make_turn_event(triggered=True) for _ in range(10)]
        for e in events:
            monitor.on_neural_turn_detected(e)
        # Mark 2 as false triggers
        monitor.mark_false_trigger(events[0]["event_id"])
        monitor.mark_false_trigger(events[1]["event_id"])
        rate = monitor.get_false_trigger_rate()
        assert abs(rate - 20.0) < 0.1   # 2/10 = 20%

    def test_mark_false_trigger_returns_true(self):
        monitor = self.Monitor("sess")
        evt = self._make_turn_event()
        monitor.on_neural_turn_detected(evt)
        result = monitor.mark_false_trigger(evt["event_id"])
        assert result is True

    def test_mark_false_trigger_returns_false_for_unknown(self):
        monitor = self.Monitor("sess")
        result = monitor.mark_false_trigger("nonexistent-id")
        assert result is False

    def test_false_trigger_rate_only_counts_triggered(self):
        """Un-triggered events are not counted in false trigger rate denominator."""
        monitor = self.Monitor("sess")
        # 3 triggered, 2 not triggered
        triggered_events = [self._make_turn_event(triggered=True) for _ in range(3)]
        untriggered_events = [self._make_turn_event(triggered=False) for _ in range(2)]
        for e in triggered_events + untriggered_events:
            monitor.on_neural_turn_detected(e)
        # Mark 1 triggered as false
        monitor.mark_false_trigger(triggered_events[0]["event_id"])
        rate = monitor.get_false_trigger_rate()
        assert abs(rate - 33.33) < 0.5   # 1/3 = 33.3%

    def test_record_interruption_events(self):
        monitor = self.Monitor("sess")
        for _ in range(3):
            monitor.on_interruption_classified(
                self._make_interruption_event("genuine_interruption")
            )
        monitor.on_interruption_classified(self._make_interruption_event("noise"))
        monitor.on_interruption_classified(self._make_interruption_event("background_sound"))
        metrics = monitor.export_metrics_to_dashboard()
        ic = metrics["interruption_classification"]
        assert ic["total_events"] == 5
        assert ic["genuine_interruptions"] == 3
        assert ic["noise_classifications"] == 1
        assert ic["background_classifications"] == 1

    def test_false_interruption_rate_zero_when_none(self):
        monitor = self.Monitor("sess")
        assert monitor.get_false_interruption_rate() == 0.0

    def test_false_interruption_rate_calculation(self):
        monitor = self.Monitor("sess")
        events = [
            self._make_interruption_event("genuine_interruption")
            for _ in range(4)
        ]
        for e in events:
            monitor.on_interruption_classified(e)
        monitor.mark_false_interruption(events[0]["event_id"])
        rate = monitor.get_false_interruption_rate()
        assert abs(rate - 25.0) < 0.1   # 1/4 = 25%

    def test_export_metrics_structure(self):
        monitor = self.Monitor("sess")
        metrics = monitor.export_metrics_to_dashboard()
        assert "session_id" in metrics
        assert "neural_turn_detection" in metrics
        assert "interruption_classification" in metrics
        nd = metrics["neural_turn_detection"]
        assert "total_events" in nd
        assert "triggered_events" in nd
        assert "false_trigger_count" in nd
        assert "false_trigger_rate_pct" in nd

    def test_singleton(self):
        m1 = self.get_monitor("sess-a")
        m2 = self.get_monitor("sess-a")
        assert m1 is m2

    def test_log_session_summary_runs(self):
        monitor = self.Monitor("sess")
        monitor.on_neural_turn_detected(self._make_turn_event())
        monitor.on_interruption_classified(self._make_interruption_event())
        # Should not raise
        monitor.log_session_summary()


# ===========================================================================
# FluidityLatencyTracker tests
# ===========================================================================

class TestFluidityLatencyTracker:

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from latency_monitor import (
                FluidityLatencyTracker,
                get_fluidity_latency_tracker,
                reset_fluidity_latency_tracker,
            )
            self.Tracker = FluidityLatencyTracker
            self.get_tracker = get_fluidity_latency_tracker
            self.reset_tracker = reset_fluidity_latency_tracker
            reset_fluidity_latency_tracker()
        except ImportError as e:
            pytest.skip(f"FluidityLatencyTracker not available: {e}")

    def test_init(self):
        tracker = self.Tracker("sess")
        assert tracker.session_id == "sess"

    def test_neural_detector_timing(self):
        tracker = self.Tracker("sess")
        tracker.on_neural_turn_detector_start("e1")
        time.sleep(0.01)  # 10ms
        latency = tracker.on_neural_turn_detector_end("e1")
        assert latency >= 10.0   # at least 10ms

    def test_interruption_classifier_timing(self):
        tracker = self.Tracker("sess")
        tracker.on_interruption_classifier_start("e1")
        time.sleep(0.005)
        latency = tracker.on_interruption_classifier_end("e1")
        assert latency >= 5.0

    def test_stt_provider_timing(self):
        tracker = self.Tracker("sess")
        tracker.on_stt_provider_start("e1")
        time.sleep(0.002)
        latency = tracker.on_stt_provider_end("e1")
        assert latency >= 2.0

    def test_end_to_end_direct(self):
        tracker = self.Tracker("sess")
        tracker.on_end_to_end_turn_detection_complete(150.0)
        pcts = tracker.calculate_percentiles("end_to_end")
        assert pcts["count"] == 1
        assert pcts["p50_ms"] == 150.0

    def test_percentiles_empty(self):
        tracker = self.Tracker("sess")
        pcts = tracker.calculate_percentiles("neural_turn_detector")
        assert pcts["count"] == 0
        assert pcts["p50_ms"] == 0.0

    def test_percentiles_with_data(self):
        tracker = self.Tracker("sess")
        for v in [100, 200, 300, 400, 500]:
            tracker.on_end_to_end_turn_detection_complete(float(v))
        pcts = tracker.calculate_percentiles("end_to_end")
        assert pcts["count"] == 5
        assert pcts["min_ms"] == 100.0
        assert pcts["max_ms"] == 500.0
        assert pcts["avg_ms"] == 300.0

    def test_p95_alert_emitted(self, caplog):
        """P95 > 400ms should emit WARNING."""
        tracker = self.Tracker("sess-alert")
        # Add 10 values, all 600ms (P95 = 600)
        for _ in range(10):
            tracker.on_end_to_end_turn_detection_complete(600.0)
        with caplog.at_level(logging.WARNING, logger="latency_monitor"):
            tracker._check_p95_alert("EndToEndTurnDetection", tracker._end_to_end_ms)
        assert any("LATENCY ALERT" in r.message for r in caplog.records)

    def test_p95_no_alert_when_ok(self, caplog):
        tracker = self.Tracker("sess-ok")
        for _ in range(10):
            tracker.on_end_to_end_turn_detection_complete(100.0)
        with caplog.at_level(logging.WARNING, logger="latency_monitor"):
            tracker._check_p95_alert("EndToEndTurnDetection", tracker._end_to_end_ms)
        assert not any("LATENCY ALERT" in r.message for r in caplog.records)

    def test_no_alert_with_fewer_than_5_samples(self, caplog):
        tracker = self.Tracker("sess")
        for _ in range(4):
            tracker.on_end_to_end_turn_detection_complete(1000.0)
        with caplog.at_level(logging.WARNING, logger="latency_monitor"):
            tracker._check_p95_alert("EndToEndTurnDetection", tracker._end_to_end_ms)
        assert not any("LATENCY ALERT" in r.message for r in caplog.records)

    def test_export_metrics_structure(self):
        tracker = self.Tracker("sess")
        export = tracker.export_metrics()
        assert "session_id" in export
        assert "neural_turn_detector" in export
        assert "interruption_classifier" in export
        assert "stt_provider" in export
        assert "end_to_end_turn_detection" in export
        assert "p95_alert_threshold_ms" in export

    def test_singleton(self):
        t1 = self.get_tracker("my-sess")
        t2 = self.get_tracker("my-sess")
        assert t1 is t2


# ===========================================================================
# FluidityErrorHandler tests
# ===========================================================================

class TestFluidityErrorHandler:

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from fluidity_error_handler import (
                FluidityErrorHandler,
                get_error_handler,
                reset_error_handler,
                ErrorType,
                ComponentType,
            )
            self.Handler = FluidityErrorHandler
            self.get_handler = get_error_handler
            self.reset = reset_error_handler
            self.ErrorType = ErrorType
            self.ComponentType = ComponentType
            reset_error_handler()
        except ImportError as e:
            pytest.skip(f"fluidity_error_handler not available: {e}")

    def test_init(self):
        handler = self.Handler(conversation_id="test-sess")
        assert handler.conversation_id == "test-sess"

    def test_handle_neural_detector_init_failure(self, caplog):
        handler = self.Handler("sess")
        exc = RuntimeError("Connection refused")
        with caplog.at_level(logging.ERROR, logger="fluidity_error_handler"):
            handler.handle_neural_detector_init_failure(exc)
        assert any("initialization_failure" in r.message.lower() or
                   "Connection refused" in r.message for r in caplog.records)

    def test_metrics_record_errors(self):
        handler = self.Handler("sess")
        for _ in range(3):
            handler.handle_stt_connection_failure(
                ConnectionError("timeout"), retry_count=1, provider="deepgram"
            )
        export = handler.export_metrics()
        assert export["total_errors"] == 3

    def test_conversation_id_in_errors(self):
        handler = self.Handler("unique-sess-id")
        handler.handle_generic("TestComponent", ValueError("oops"))
        recent = handler.get_recent_errors()
        assert len(recent) == 1
        assert recent[0]["conversation_id"] == "unique-sess-id"

    def test_get_recent_errors_filtered(self):
        handler = self.Handler("sess")
        handler.handle_neural_detector_init_failure(RuntimeError("fail"))
        handler.handle_stt_connection_failure(ConnectionError("timeout"))
        neural = handler.get_recent_errors(self.ComponentType.NEURAL_TURN_DETECTOR)
        stt = handler.get_recent_errors(self.ComponentType.STT_PROVIDER)
        assert len(neural) == 1
        assert len(stt) == 1

    def test_classifier_timeout_handled(self):
        handler = self.Handler("sess")
        handler.handle_classifier_timeout(timeout_ms=105.0, audio_duration_ms=500.0)
        export = handler.export_metrics()
        assert export["total_errors"] == 1

    def test_stack_trace_included_for_exceptions(self):
        handler = self.Handler("sess")
        try:
            raise ValueError("test error")
        except ValueError as e:
            handler.handle_generic("TestComp", e)
        recent = handler.get_recent_errors()
        assert recent[0]["stack_trace"] != ""

    def test_rate_limit_handler(self):
        handler = self.Handler("sess")
        handler.handle_stt_rate_limit(
            Exception("429"), retry_after_s=30.0, provider="assemblyai"
        )
        export = handler.export_metrics()
        assert export["total_errors"] == 1

    def test_auth_error_handler(self):
        handler = self.Handler("sess")
        handler.handle_stt_auth_error(Exception("401 Unauthorized"), provider="deepgram")
        recent = handler.get_recent_errors(self.ComponentType.STT_PROVIDER)
        assert len(recent) == 1
        assert recent[0]["error_type"] == self.ErrorType.AUTHENTICATION_ERROR


# ===========================================================================
# FluidityConfig tests
# ===========================================================================

class TestFluidityConfig:

    @pytest.fixture(autouse=True)
    def setup(self):
        try:
            from fluidity_config import (
                FluidityConfig,
                get_fluidity_config,
                reset_fluidity_config,
                STTProviderConfig,
                NeuralTurnDetectorSettings,
                InterruptionClassifierSettings,
                CostMonitorSettings,
                ABTestingSettings,
                MultiLanguageSettings,
            )
            self.Config = FluidityConfig
            self.get_config = get_fluidity_config
            self.reset_config = reset_fluidity_config
            reset_fluidity_config()
        except ImportError as e:
            pytest.skip(f"fluidity_config not available: {e}")

    def teardown_method(self, method):
        try:
            self.reset_config()
        except Exception:
            pass

    def test_from_env_no_crash(self):
        """Config loading must never crash, even with no env vars."""
        config = self.Config.from_env()
        assert config is not None

    def test_stt_disabled_without_keys(self, monkeypatch):
        monkeypatch.delenv("ASSEMBLYAI_API_KEY", raising=False)
        monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
        self.reset_config()
        config = self.Config.from_env()
        assert not config.stt.enabled
        assert not config.supports_neural_turn_detection()

    def test_supports_neural_detection_with_key(self, monkeypatch):
        monkeypatch.setenv("DEEPGRAM_API_KEY", "fake-key-12345")
        monkeypatch.setenv("NEURAL_TURN_DETECTOR_ENABLED", "true")
        self.reset_config()
        config = self.Config.from_env()
        assert config.stt.enabled
        assert config.supports_neural_turn_detection()

    def test_confidence_threshold_from_env(self, monkeypatch):
        monkeypatch.setenv("END_OF_TURN_CONFIDENCE_THRESHOLD", "0.7")
        self.reset_config()
        config = self.Config.from_env()
        assert abs(config.neural_turn_detector.confidence_threshold - 0.7) < 1e-9

    def test_bad_confidence_clamped_to_default(self, monkeypatch):
        monkeypatch.setenv("END_OF_TURN_CONFIDENCE_THRESHOLD", "99.0")
        self.reset_config()
        config = self.Config.from_env()
        assert config.neural_turn_detector.confidence_threshold == 1.0  # clamped to max

    def test_update_neural_threshold(self):
        config = self.Config.from_env()
        config.update_neural_threshold(0.65)
        assert abs(config.neural_turn_detector.confidence_threshold - 0.65) < 1e-9

    def test_update_neural_threshold_invalid_ignored(self):
        config = self.Config.from_env()
        old = config.neural_turn_detector.confidence_threshold
        config.update_neural_threshold(1.5)  # invalid
        assert config.neural_turn_detector.confidence_threshold == old

    def test_to_dict_complete(self):
        config = self.Config.from_env()
        d = config.to_dict()
        assert "stt" in d
        assert "neural_turn_detector" in d
        assert "interruption_classifier" in d
        assert "cost_monitor" in d
        assert "ab_testing" in d
        assert "multi_language" in d

    def test_singleton(self):
        c1 = self.get_config()
        c2 = self.get_config()
        assert c1 is c2

    def test_reset_clears_singleton(self):
        c1 = self.get_config()
        self.reset_config()
        c2 = self.get_config()
        assert c1 is not c2

    def test_ab_testing_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("AB_TESTING_ENABLED", raising=False)
        self.reset_config()
        config = self.Config.from_env()
        assert not config.ab_testing.enabled

    def test_multi_language_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("MULTI_LANGUAGE_ENABLED", raising=False)
        self.reset_config()
        config = self.Config.from_env()
        assert not config.multi_language.enabled
