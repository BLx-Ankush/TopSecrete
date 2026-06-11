"""
Unit tests for fluidity_models.py

Tests all dataclasses: TranscriptionResult, TurnDetectionEvent,
InterruptionEvent, FluidityLatencyMetrics, CostMetrics, FallbackEvent.

Requirements coverage: 10.2, 10.3, 11.1, 11.2, 12.1, 12.2
"""

import sys
import os

# Ensure Alice_code directory is on sys.path
_THIS = os.path.dirname(__file__)
_CODE = os.path.dirname(_THIS)
if _CODE not in sys.path:
    sys.path.insert(0, _CODE)

import time
import pytest

try:
    from fluidity_models import (
        TranscriptionResult,
        TurnDetectionEvent,
        InterruptionEvent,
        FluidityLatencyMetrics,
        CostMetrics,
        FallbackEvent,
    )
    MODELS_AVAILABLE = True
except ImportError as e:
    MODELS_AVAILABLE = False
    pytest.skip(f"fluidity_models not available: {e}", allow_module_level=True)


# ===========================================================================
# TranscriptionResult
# ===========================================================================

class TestTranscriptionResult:

    def test_create_factory(self):
        """create() populates timestamp_ms automatically."""
        result = TranscriptionResult.create(
            text="Hello there",
            confidence=0.92,
            end_of_utterance=True,
            is_final=True,
            provider_type="mock",
        )
        assert result.text == "Hello there"
        assert result.confidence == 0.92
        assert result.end_of_utterance is True
        assert result.is_final is True
        assert result.timestamp_ms > 0
        assert result.provider_type == "mock"

    def test_is_valid_good(self):
        result = TranscriptionResult.create("test", 0.5, False, False)
        assert result.is_valid()

    @pytest.mark.parametrize("confidence", [-0.1, 1.1, float("inf")])
    def test_is_valid_bad_confidence(self, confidence):
        result = TranscriptionResult.create("test", 0.5, False, False)
        result.confidence = confidence
        assert not result.is_valid()

    def test_to_dict_from_dict_roundtrip(self):
        original = TranscriptionResult.create(
            text="Hello",
            confidence=0.8,
            end_of_utterance=False,
            is_final=True,
            acoustic_features={"pitch_trend": "falling"},
            linguistic_features={"sentence_complete": True},
            provider_type="deepgram",
            audio_duration_ms=240,
        )
        d = original.to_dict()
        restored = TranscriptionResult.from_dict(d)
        assert restored.text == original.text
        assert restored.confidence == original.confidence
        assert restored.acoustic_features == original.acoustic_features
        assert restored.linguistic_features == original.linguistic_features

    def test_default_features_empty(self):
        result = TranscriptionResult.create("hi", 0.9, True, True)
        assert result.acoustic_features == {}
        assert result.linguistic_features == {}


# ===========================================================================
# TurnDetectionEvent
# ===========================================================================

class TestTurnDetectionEvent:

    def test_create_generates_unique_ids(self):
        e1 = TurnDetectionEvent.create("neural", 0.7, 0.4, True, 500, 300)
        e2 = TurnDetectionEvent.create("neural", 0.7, 0.4, True, 500, 300)
        assert e1.event_id != e2.event_id

    def test_mark_false_trigger(self):
        event = TurnDetectionEvent.create("neural", 0.7, 0.4, True, 500, 300)
        assert event.is_false_trigger is False
        event.mark_false_trigger()
        assert event.is_false_trigger is True

    def test_to_dict_from_dict_roundtrip(self):
        event = TurnDetectionEvent.create(
            "silero", 0.3, 0.4, False, 1000, 600,
            conversation_id="sess-abc",
            stt_text="Hello",
            fallback_reason="STT_CONNECTION_LOST",
        )
        d = event.to_dict()
        restored = TurnDetectionEvent.from_dict(d)
        assert restored.event_id == event.event_id
        assert restored.fallback_reason == "STT_CONNECTION_LOST"
        assert restored.stt_text == "Hello"

    def test_confidence_stored_correctly(self):
        for conf in [0.0, 0.4, 0.99, 1.0]:
            e = TurnDetectionEvent.create("neural", conf, 0.4, conf >= 0.4, 100, 50)
            assert e.end_of_turn_confidence == conf


# ===========================================================================
# InterruptionEvent
# ===========================================================================

class TestInterruptionEvent:

    def test_create_factory(self):
        evt = InterruptionEvent.create(
            classification="genuine_interruption",
            audio_duration_ms=350.0,
            audio_energy=0.45,
            spectral_features={"centroid_hz": 1200.0},
            temporal_features={"zero_crossing_rate": 120.0},
            action_taken="cancel_response",
            conversation_id="sess-xyz",
            classifier_latency_ms=12.5,
        )
        assert evt.classification == "genuine_interruption"
        assert evt.action_taken == "cancel_response"
        assert evt.classifier_latency_ms == 12.5
        assert evt.timestamp_ms > 0

    def test_mark_false_interruption(self):
        evt = InterruptionEvent.create("genuine_interruption", 300.0, 0.3)
        assert evt.is_false_interruption is False
        evt.mark_false_interruption()
        assert evt.is_false_interruption is True

    def test_roundtrip(self):
        evt = InterruptionEvent.create("noise", 50.0, 0.01)
        d = evt.to_dict()
        restored = InterruptionEvent.from_dict(d)
        assert restored.event_id == evt.event_id
        assert restored.classification == "noise"

    @pytest.mark.parametrize("classification", [
        "genuine_interruption", "noise", "background_sound"
    ])
    def test_all_classifications_accepted(self, classification):
        evt = InterruptionEvent.create(classification, 200.0, 0.1)
        assert evt.classification == classification


# ===========================================================================
# FluidityLatencyMetrics
# ===========================================================================

class TestFluidityLatencyMetrics:

    def test_create(self):
        m = FluidityLatencyMetrics.create("sess-1")
        assert m.conversation_id == "sess-1"
        assert m.timestamp_ms > 0
        assert m.neural_turn_detector_latency_ms == 0.0

    def test_meets_latency_targets_all_good(self):
        m = FluidityLatencyMetrics.create("sess-1")
        m.neural_turn_detector_latency_ms = 100.0
        m.interruption_classifier_latency_ms = 50.0
        m.stt_provider_latency_ms = 200.0
        m.total_response_time_ms = 300.0
        targets = m.meets_latency_targets()
        assert all(targets.values())

    def test_meets_latency_targets_some_fail(self):
        m = FluidityLatencyMetrics.create("sess-1")
        m.neural_turn_detector_latency_ms = 500.0   # exceeds 400ms
        m.interruption_classifier_latency_ms = 200.0  # exceeds 100ms
        targets = m.meets_latency_targets()
        assert not targets["neural_turn_detector_ok"]
        assert not targets["interruption_classifier_ok"]


# ===========================================================================
# CostMetrics
# ===========================================================================

class TestCostMetrics:

    def test_create(self):
        m = CostMetrics.create("sess-cost")
        assert m.conversation_id == "sess-cost"
        assert m.stt_audio_minutes == 0.0
        assert m.felicia_baseline_cost == 0.090

    def test_is_within_budget(self):
        m = CostMetrics.create("sess")
        m.cost_per_agent_minute = 0.025
        assert m.is_within_budget(0.030)

    def test_exceeds_budget(self):
        m = CostMetrics.create("sess")
        m.cost_per_agent_minute = 0.040
        assert not m.is_within_budget(0.030)

    def test_savings_percentage(self):
        m = CostMetrics.create("sess")
        m.felicia_baseline_cost = 0.090
        m.cost_per_agent_minute = 0.030
        pct = m.get_savings_percentage()
        assert abs(pct - 66.67) < 0.1

    def test_to_dict_has_all_fields(self):
        m = CostMetrics.create("sess")
        d = m.to_dict()
        assert "conversation_id" in d
        assert "stt_audio_minutes" in d
        assert "cost_per_agent_minute" in d


# ===========================================================================
# FallbackEvent
# ===========================================================================

class TestFallbackEvent:

    def test_create(self):
        evt = FallbackEvent.create(
            reason_code=FallbackEvent.REASON_STT_CONNECTION_LOST,
            reason_details="WebSocket closed unexpectedly",
            conversation_id="sess-fb",
            consecutive_failures=3,
        )
        assert evt.reason_code == "STT_CONNECTION_LOST"
        assert evt.consecutive_failures == 3
        assert evt.restored is False
        assert evt.timestamp_ms > 0

    def test_mark_restored(self):
        evt = FallbackEvent.create(FallbackEvent.REASON_HEALTH_CHECK_FAILED)
        evt.mark_restored()
        assert evt.restored is True

    def test_all_reason_codes_exist(self):
        codes = [
            FallbackEvent.REASON_STT_CONNECTION_LOST,
            FallbackEvent.REASON_HEALTH_CHECK_FAILED,
            FallbackEvent.REASON_INITIALIZATION_FAILED,
            FallbackEvent.REASON_AUDIO_FORMAT_ERROR,
            FallbackEvent.REASON_RATE_LIMIT,
            FallbackEvent.REASON_AUTH_ERROR,
        ]
        for code in codes:
            assert isinstance(code, str) and len(code) > 0

    def test_to_dict_roundtrip(self):
        evt = FallbackEvent.create(FallbackEvent.REASON_RATE_LIMIT, "429 Too Many Requests")
        d = evt.to_dict()
        assert d["reason_code"] == "RATE_LIMIT_EXCEEDED"
