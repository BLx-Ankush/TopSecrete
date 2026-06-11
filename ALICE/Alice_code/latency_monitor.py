"""
Latency Monitoring System

This module monitors voice interaction latency to validate optimization effectiveness.
Tracks timing for each stage of the voice pipeline:
- VAD trigger time
- API processing time
- TTS generation time
- Playback start time
- Total response time

Target: <400ms total response time from end of user speech to start of Alice's speech

Requirements: 2.7, 3.5
"""

import logging
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import statistics

logger = logging.getLogger(__name__)


@dataclass
class LatencyMetrics:
    """Metrics for a single voice interaction"""
    interaction_id: int
    
    # Timestamps
    user_speech_end: Optional[float] = None
    vad_trigger_time: Optional[float] = None
    api_request_start: Optional[float] = None
    api_response_start: Optional[float] = None
    tts_generation_start: Optional[float] = None
    tts_first_chunk: Optional[float] = None
    playback_start: Optional[float] = None
    alice_speech_start: Optional[float] = None
    
    # Calculated latencies (in milliseconds)
    vad_trigger_latency_ms: Optional[float] = None  # Time from speech end to VAD trigger
    api_processing_latency_ms: Optional[float] = None  # Time for API processing
    tts_generation_latency_ms: Optional[float] = None  # Time for TTS generation
    playback_start_latency_ms: Optional[float] = None  # Time to start playback
    total_response_latency_ms: Optional[float] = None  # Total time from speech end to Alice starts
    
    # Performance targets
    TARGET_TOTAL_LATENCY_MS = 400
    TARGET_VAD_LATENCY_MS = 400
    TARGET_API_LATENCY_MS = 150
    TARGET_TTS_LATENCY_MS = 200
    TARGET_PLAYBACK_LATENCY_MS = 50
    
    def calculate_latencies(self):
        """Calculate latency metrics from timestamps"""
        # VAD trigger latency
        if self.user_speech_end and self.vad_trigger_time:
            self.vad_trigger_latency_ms = (self.vad_trigger_time - self.user_speech_end) * 1000
        
        # API processing latency
        if self.api_request_start and self.api_response_start:
            self.api_processing_latency_ms = (self.api_response_start - self.api_request_start) * 1000
        
        # TTS generation latency
        if self.tts_generation_start and self.tts_first_chunk:
            self.tts_generation_latency_ms = (self.tts_first_chunk - self.tts_generation_start) * 1000
        
        # Playback start latency
        if self.tts_first_chunk and self.playback_start:
            self.playback_start_latency_ms = (self.playback_start - self.tts_first_chunk) * 1000
        
        # Total response latency
        if self.user_speech_end and self.alice_speech_start:
            self.total_response_latency_ms = (self.alice_speech_start - self.user_speech_end) * 1000
    
    def meets_target(self) -> bool:
        """Check if interaction meets the <400ms target"""
        if self.total_response_latency_ms is None:
            return False
        return self.total_response_latency_ms < self.TARGET_TOTAL_LATENCY_MS
    
    def get_performance_summary(self) -> Dict[str, any]:
        """Get performance summary with target comparisons"""
        summary = {
            'interaction_id': self.interaction_id,
            'meets_target': self.meets_target(),
        }
        
        if self.vad_trigger_latency_ms is not None:
            summary['vad_trigger_ms'] = round(self.vad_trigger_latency_ms, 1)
            summary['vad_target_ms'] = self.TARGET_VAD_LATENCY_MS
            summary['vad_meets_target'] = self.vad_trigger_latency_ms <= self.TARGET_VAD_LATENCY_MS
        
        if self.api_processing_latency_ms is not None:
            summary['api_processing_ms'] = round(self.api_processing_latency_ms, 1)
            summary['api_target_ms'] = self.TARGET_API_LATENCY_MS
            summary['api_meets_target'] = self.api_processing_latency_ms < self.TARGET_API_LATENCY_MS
        
        if self.tts_generation_latency_ms is not None:
            summary['tts_generation_ms'] = round(self.tts_generation_latency_ms, 1)
            summary['tts_target_ms'] = self.TARGET_TTS_LATENCY_MS
            summary['tts_meets_target'] = self.tts_generation_latency_ms < self.TARGET_TTS_LATENCY_MS
        
        if self.playback_start_latency_ms is not None:
            summary['playback_start_ms'] = round(self.playback_start_latency_ms, 1)
            summary['playback_target_ms'] = self.TARGET_PLAYBACK_LATENCY_MS
            summary['playback_meets_target'] = self.playback_start_latency_ms < self.TARGET_PLAYBACK_LATENCY_MS
        
        if self.total_response_latency_ms is not None:
            summary['total_response_ms'] = round(self.total_response_latency_ms, 1)
            summary['total_target_ms'] = self.TARGET_TOTAL_LATENCY_MS
        
        return summary


@dataclass
class LatencySession:
    """Session-level latency metrics with aggregation"""
    session_id: str
    start_time: float = field(default_factory=time.time)
    interactions: List[LatencyMetrics] = field(default_factory=list)
    current_interaction_id: int = 0
    
    def get_summary(self) -> Dict[str, any]:
        """Get session summary with aggregated metrics"""
        if not self.interactions:
            return {
                'session_id': self.session_id,
                'total_interactions': 0,
                'message': 'No interactions recorded'
            }
        
        # Collect all latency measurements
        vad_latencies = [i.vad_trigger_latency_ms for i in self.interactions if i.vad_trigger_latency_ms is not None]
        api_latencies = [i.api_processing_latency_ms for i in self.interactions if i.api_processing_latency_ms is not None]
        tts_latencies = [i.tts_generation_latency_ms for i in self.interactions if i.tts_generation_latency_ms is not None]
        playback_latencies = [i.playback_start_latency_ms for i in self.interactions if i.playback_start_latency_ms is not None]
        total_latencies = [i.total_response_latency_ms for i in self.interactions if i.total_response_latency_ms is not None]
        
        # Count interactions meeting targets
        interactions_meeting_target = sum(1 for i in self.interactions if i.meets_target())
        
        summary = {
            'session_id': self.session_id,
            'total_interactions': len(self.interactions),
            'interactions_meeting_target': interactions_meeting_target,
            'target_compliance_rate': interactions_meeting_target / len(self.interactions) if self.interactions else 0,
        }
        
        # Add aggregated statistics for each stage
        if vad_latencies:
            summary['vad_trigger'] = self._calculate_statistics(vad_latencies, LatencyMetrics.TARGET_VAD_LATENCY_MS)
        
        if api_latencies:
            summary['api_processing'] = self._calculate_statistics(api_latencies, LatencyMetrics.TARGET_API_LATENCY_MS)
        
        if tts_latencies:
            summary['tts_generation'] = self._calculate_statistics(tts_latencies, LatencyMetrics.TARGET_TTS_LATENCY_MS)
        
        if playback_latencies:
            summary['playback_start'] = self._calculate_statistics(playback_latencies, LatencyMetrics.TARGET_PLAYBACK_LATENCY_MS)
        
        if total_latencies:
            summary['total_response'] = self._calculate_statistics(total_latencies, LatencyMetrics.TARGET_TOTAL_LATENCY_MS)
        
        return summary
    
    def _calculate_statistics(self, latencies: List[float], target: float) -> Dict[str, float]:
        """Calculate statistical metrics for a set of latencies"""
        stats = {
            'avg_ms': round(statistics.mean(latencies), 1),
            'min_ms': round(min(latencies), 1),
            'max_ms': round(max(latencies), 1),
            'target_ms': target,
        }
        
        # Calculate percentiles if we have enough data
        if len(latencies) >= 3:
            sorted_latencies = sorted(latencies)
            stats['p50_ms'] = round(statistics.median(sorted_latencies), 1)
            
            if len(latencies) >= 10:
                # P90 and P99 for larger datasets
                p90_idx = int(len(sorted_latencies) * 0.9)
                p99_idx = int(len(sorted_latencies) * 0.99)
                stats['p90_ms'] = round(sorted_latencies[p90_idx], 1)
                stats['p99_ms'] = round(sorted_latencies[p99_idx], 1)
        
        # Calculate compliance rate
        meeting_target = sum(1 for l in latencies if l < target)
        stats['compliance_rate'] = meeting_target / len(latencies) if latencies else 0
        
        return stats


class LatencyMonitor:
    """
    Monitor for voice interaction latency.
    
    This class tracks latency across all stages of the voice pipeline:
    - VAD trigger time (target: ≤400ms)
    - API processing time (target: <150ms)
    - TTS generation time (target: <200ms)
    - Playback start time (target: <50ms)
    - Total response time (target: <400ms)
    
    Integrates with turn-taking monitor for comprehensive performance tracking.
    """
    
    def __init__(self, session_id: str = "default"):
        """
        Initialize latency monitor.
        
        Args:
            session_id: Unique identifier for this session
        """
        self.session = LatencySession(session_id=session_id)
        self.current_interaction: Optional[LatencyMetrics] = None
        
        logger.info(f"[Latency Monitor] Initialized for session: {session_id}")
        logger.info(f"[Latency Monitor] Performance targets: Total <{LatencyMetrics.TARGET_TOTAL_LATENCY_MS}ms, "
                   f"VAD ≤{LatencyMetrics.TARGET_VAD_LATENCY_MS}ms, "
                   f"API <{LatencyMetrics.TARGET_API_LATENCY_MS}ms, "
                   f"TTS <{LatencyMetrics.TARGET_TTS_LATENCY_MS}ms, "
                   f"Playback <{LatencyMetrics.TARGET_PLAYBACK_LATENCY_MS}ms")
    
    def start_interaction(self) -> None:
        """Start tracking a new voice interaction"""
        self.session.current_interaction_id += 1
        self.current_interaction = LatencyMetrics(interaction_id=self.session.current_interaction_id)
        
        logger.debug(f"[Latency Monitor] Started tracking interaction {self.current_interaction.interaction_id}")
    
    def on_user_speech_end(self) -> None:
        """Called when user stops speaking"""
        if self.current_interaction is None:
            logger.warning("[Latency Monitor] Speech end without active interaction")
            self.start_interaction()
        
        self.current_interaction.user_speech_end = time.time()
        logger.debug(f"[Latency Monitor] User speech ended at T=0ms (baseline)")
    
    def on_vad_trigger(self) -> None:
        """Called when VAD triggers end-of-speech detection"""
        if self.current_interaction is None:
            logger.warning("[Latency Monitor] VAD trigger without active interaction")
            return
        
        self.current_interaction.vad_trigger_time = time.time()
        
        # Calculate and log VAD trigger latency
        if self.current_interaction.user_speech_end:
            latency_ms = (self.current_interaction.vad_trigger_time - self.current_interaction.user_speech_end) * 1000
            target_met = latency_ms <= LatencyMetrics.TARGET_VAD_LATENCY_MS
            status = "✓" if target_met else "✗"
            
            logger.info(
                f"[Latency Monitor] {status} VAD triggered: {latency_ms:.1f}ms "
                f"(target: ≤{LatencyMetrics.TARGET_VAD_LATENCY_MS}ms)"
            )
            logger.debug(f"[Latency Monitor] VAD trigger at T={latency_ms:.1f}ms")
    
    def on_api_request_start(self) -> None:
        """Called when API request begins"""
        if self.current_interaction is None:
            logger.warning("[Latency Monitor] API request without active interaction")
            return
        
        self.current_interaction.api_request_start = time.time()
        
        if self.current_interaction.user_speech_end:
            elapsed_ms = (self.current_interaction.api_request_start - self.current_interaction.user_speech_end) * 1000
            logger.debug(f"[Latency Monitor] API request started at T={elapsed_ms:.1f}ms")
    
    def on_api_response_start(self) -> None:
        """Called when API response begins streaming"""
        if self.current_interaction is None:
            logger.warning("[Latency Monitor] API response without active interaction")
            return
        
        self.current_interaction.api_response_start = time.time()
        
        # Calculate and log API processing latency
        if self.current_interaction.api_request_start:
            latency_ms = (self.current_interaction.api_response_start - self.current_interaction.api_request_start) * 1000
            target_met = latency_ms < LatencyMetrics.TARGET_API_LATENCY_MS
            status = "✓" if target_met else "✗"
            
            logger.info(
                f"[Latency Monitor] {status} API response started: {latency_ms:.1f}ms "
                f"(target: <{LatencyMetrics.TARGET_API_LATENCY_MS}ms)"
            )
        
        if self.current_interaction.user_speech_end:
            elapsed_ms = (self.current_interaction.api_response_start - self.current_interaction.user_speech_end) * 1000
            logger.debug(f"[Latency Monitor] API response at T={elapsed_ms:.1f}ms")
    
    def on_tts_generation_start(self) -> None:
        """Called when TTS generation begins"""
        if self.current_interaction is None:
            logger.warning("[Latency Monitor] TTS generation without active interaction")
            return
        
        self.current_interaction.tts_generation_start = time.time()
        
        if self.current_interaction.user_speech_end:
            elapsed_ms = (self.current_interaction.tts_generation_start - self.current_interaction.user_speech_end) * 1000
            logger.debug(f"[Latency Monitor] TTS generation started at T={elapsed_ms:.1f}ms")
    
    def on_tts_first_chunk(self) -> None:
        """Called when first TTS audio chunk is ready"""
        if self.current_interaction is None:
            logger.warning("[Latency Monitor] TTS chunk without active interaction")
            return
        
        self.current_interaction.tts_first_chunk = time.time()
        
        # Calculate and log TTS generation latency
        if self.current_interaction.tts_generation_start:
            latency_ms = (self.current_interaction.tts_first_chunk - self.current_interaction.tts_generation_start) * 1000
            target_met = latency_ms < LatencyMetrics.TARGET_TTS_LATENCY_MS
            status = "✓" if target_met else "✗"
            
            logger.info(
                f"[Latency Monitor] {status} TTS first chunk ready: {latency_ms:.1f}ms "
                f"(target: <{LatencyMetrics.TARGET_TTS_LATENCY_MS}ms)"
            )
        
        if self.current_interaction.user_speech_end:
            elapsed_ms = (self.current_interaction.tts_first_chunk - self.current_interaction.user_speech_end) * 1000
            logger.debug(f"[Latency Monitor] TTS first chunk at T={elapsed_ms:.1f}ms")
    
    def on_playback_start(self) -> None:
        """Called when audio playback begins"""
        if self.current_interaction is None:
            logger.warning("[Latency Monitor] Playback start without active interaction")
            return
        
        self.current_interaction.playback_start = time.time()
        
        # Calculate and log playback start latency
        if self.current_interaction.tts_first_chunk:
            latency_ms = (self.current_interaction.playback_start - self.current_interaction.tts_first_chunk) * 1000
            target_met = latency_ms < LatencyMetrics.TARGET_PLAYBACK_LATENCY_MS
            status = "✓" if target_met else "✗"
            
            logger.info(
                f"[Latency Monitor] {status} Playback started: {latency_ms:.1f}ms "
                f"(target: <{LatencyMetrics.TARGET_PLAYBACK_LATENCY_MS}ms)"
            )
        
        if self.current_interaction.user_speech_end:
            elapsed_ms = (self.current_interaction.playback_start - self.current_interaction.user_speech_end) * 1000
            logger.debug(f"[Latency Monitor] Playback started at T={elapsed_ms:.1f}ms")
    
    def on_alice_speech_start(self) -> None:
        """Called when Alice starts speaking (user hears audio)"""
        if self.current_interaction is None:
            logger.warning("[Latency Monitor] Alice speech without active interaction")
            return
        
        self.current_interaction.alice_speech_start = time.time()
        
        # Calculate total response latency
        if self.current_interaction.user_speech_end:
            latency_ms = (self.current_interaction.alice_speech_start - self.current_interaction.user_speech_end) * 1000
            target_met = latency_ms < LatencyMetrics.TARGET_TOTAL_LATENCY_MS
            status = "✓" if target_met else "✗"
            
            logger.info(
                f"[Latency Monitor] {status} Alice speech started: {latency_ms:.1f}ms total "
                f"(target: <{LatencyMetrics.TARGET_TOTAL_LATENCY_MS}ms)"
            )
            logger.debug(f"[Latency Monitor] Alice speech at T={latency_ms:.1f}ms")
    
    def complete_interaction(self) -> None:
        """Complete the current interaction and calculate all metrics"""
        if self.current_interaction is None:
            logger.warning("[Latency Monitor] Complete interaction without active interaction")
            return
        
        # Calculate all latencies
        self.current_interaction.calculate_latencies()
        
        # Log detailed summary
        self._log_interaction_summary(self.current_interaction)
        
        # Add to session
        self.session.interactions.append(self.current_interaction)
        
        # Reset current interaction
        self.current_interaction = None
    
    def _log_interaction_summary(self, interaction: LatencyMetrics) -> None:
        """Log detailed summary of completed interaction"""
        logger.info("=" * 70)
        logger.info(f"Latency Summary - Interaction {interaction.interaction_id}")
        logger.info("=" * 70)
        
        # Log each stage with target comparison
        if interaction.vad_trigger_latency_ms is not None:
            status = "✓" if interaction.vad_trigger_latency_ms <= LatencyMetrics.TARGET_VAD_LATENCY_MS else "✗"
            logger.info(
                f"{status} VAD Trigger:      {interaction.vad_trigger_latency_ms:6.1f}ms "
                f"(target: ≤{LatencyMetrics.TARGET_VAD_LATENCY_MS}ms)"
            )
        
        if interaction.api_processing_latency_ms is not None:
            status = "✓" if interaction.api_processing_latency_ms < LatencyMetrics.TARGET_API_LATENCY_MS else "✗"
            logger.info(
                f"{status} API Processing:   {interaction.api_processing_latency_ms:6.1f}ms "
                f"(target: <{LatencyMetrics.TARGET_API_LATENCY_MS}ms)"
            )
        
        if interaction.tts_generation_latency_ms is not None:
            status = "✓" if interaction.tts_generation_latency_ms < LatencyMetrics.TARGET_TTS_LATENCY_MS else "✗"
            logger.info(
                f"{status} TTS Generation:   {interaction.tts_generation_latency_ms:6.1f}ms "
                f"(target: <{LatencyMetrics.TARGET_TTS_LATENCY_MS}ms)"
            )
        
        if interaction.playback_start_latency_ms is not None:
            status = "✓" if interaction.playback_start_latency_ms < LatencyMetrics.TARGET_PLAYBACK_LATENCY_MS else "✗"
            logger.info(
                f"{status} Playback Start:   {interaction.playback_start_latency_ms:6.1f}ms "
                f"(target: <{LatencyMetrics.TARGET_PLAYBACK_LATENCY_MS}ms)"
            )
        
        logger.info("-" * 70)
        
        if interaction.total_response_latency_ms is not None:
            status = "✓ PASS" if interaction.meets_target() else "✗ FAIL"
            logger.info(
                f"{status} TOTAL RESPONSE: {interaction.total_response_latency_ms:6.1f}ms "
                f"(target: <{LatencyMetrics.TARGET_TOTAL_LATENCY_MS}ms)"
            )
        
        logger.info("=" * 70)
    
    def get_session_summary(self) -> Dict[str, any]:
        """Get summary of all interactions in this session"""
        return self.session.get_summary()
    
    def log_session_summary(self) -> None:
        """Log session summary with aggregated metrics"""
        summary = self.get_session_summary()
        
        logger.info("\n" + "=" * 70)
        logger.info("LATENCY MONITORING SESSION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Session ID: {summary['session_id']}")
        logger.info(f"Total Interactions: {summary['total_interactions']}")
        
        if summary['total_interactions'] > 0:
            logger.info(f"Interactions Meeting Target (<400ms): {summary['interactions_meeting_target']}")
            logger.info(f"Target Compliance Rate: {summary['target_compliance_rate']:.1%}")
            
            # Log statistics for each stage
            stages = [
                ('vad_trigger', 'VAD Trigger'),
                ('api_processing', 'API Processing'),
                ('tts_generation', 'TTS Generation'),
                ('playback_start', 'Playback Start'),
                ('total_response', 'Total Response')
            ]
            
            for key, label in stages:
                if key in summary:
                    stats = summary[key]
                    logger.info(f"\n{label}:")
                    logger.info(f"  Average:    {stats['avg_ms']:6.1f}ms (target: <{stats['target_ms']}ms)")
                    logger.info(f"  Min:        {stats['min_ms']:6.1f}ms")
                    logger.info(f"  Max:        {stats['max_ms']:6.1f}ms")
                    
                    if 'p50_ms' in stats:
                        logger.info(f"  P50:        {stats['p50_ms']:6.1f}ms")
                    if 'p90_ms' in stats:
                        logger.info(f"  P90:        {stats['p90_ms']:6.1f}ms")
                    if 'p99_ms' in stats:
                        logger.info(f"  P99:        {stats['p99_ms']:6.1f}ms")
                    
                    logger.info(f"  Compliance: {stats['compliance_rate']:.1%}")
        
        logger.info("=" * 70 + "\n")
    
    def get_performance_metrics_for_display(self) -> Dict[str, any]:
        """
        Get current performance metrics formatted for turn-taking monitor display.
        
        Returns:
            Dictionary with current and session-average metrics
        """
        metrics = {
            'current': None,
            'session_avg': None
        }
        
        # Current interaction metrics
        if self.current_interaction and self.current_interaction.total_response_latency_ms:
            metrics['current'] = self.current_interaction.get_performance_summary()
        
        # Session average metrics
        if self.session.interactions:
            summary = self.get_session_summary()
            if 'total_response' in summary:
                metrics['session_avg'] = {
                    'total_response_ms': summary['total_response']['avg_ms'],
                    'target_ms': LatencyMetrics.TARGET_TOTAL_LATENCY_MS,
                    'compliance_rate': summary['target_compliance_rate']
                }
        
        return metrics


# Global monitor instance
_global_latency_monitor: Optional[LatencyMonitor] = None


def get_latency_monitor(session_id: str = "default") -> LatencyMonitor:
    """
    Get or create the global latency monitor.
    
    Args:
        session_id: Session identifier
    
    Returns:
        LatencyMonitor instance
    """
    global _global_latency_monitor
    
    if _global_latency_monitor is None or _global_latency_monitor.session.session_id != session_id:
        _global_latency_monitor = LatencyMonitor(session_id=session_id)
    
    return _global_latency_monitor


def reset_latency_monitor() -> None:
    """Reset the global latency monitor"""
    global _global_latency_monitor
    _global_latency_monitor = None


# ===========================================================================
# FluidityLatencyTracker
# Added for Alice Conversation Fluidity Enhancement (Task 10)
# Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7
# ===========================================================================

class FluidityLatencyTracker:
    """
    Track processing latency for all new fluidity components.

    Captures timing for:
      - NeuralTurnDetector audio frame processing
      - InterruptionClassifier classification
      - STT Provider transcription round-trip
      - End-to-end turn detection (audio-in → end-of-turn signal)

    Computes P50, P95, P99 percentiles and emits WARNING when P95 > 400ms.

    Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7
    """

    # P95 alert threshold
    P95_ALERT_THRESHOLD_MS = 400.0

    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self._active_timers: dict = {}

        # Latency lists per component
        self._neural_detector_ms: list = []
        self._interruption_classifier_ms: list = []
        self._stt_provider_ms: list = []
        self._end_to_end_ms: list = []

        self._p95_alerted: set = set()   # avoid repeat alerts per component

        logger.info(f"[FluidityLatencyTracker] Initialized for session: {session_id}")

    # ------------------------------------------------------------------
    # Timer helpers
    # ------------------------------------------------------------------

    def _start_timer(self, key: str) -> None:
        self._active_timers[key] = time.time()

    def _stop_timer(self, key: str) -> float:
        start = self._active_timers.pop(key, None)
        if start is None:
            return 0.0
        return (time.time() - start) * 1000.0   # ms

    # ------------------------------------------------------------------
    # Neural Turn Detector  (Requirements: 11.1)
    # ------------------------------------------------------------------

    def on_neural_turn_detector_start(self, event_id: str = "") -> None:
        """Start timing NeuralTurnDetector frame processing."""
        self._start_timer(f"ntd_{event_id or id(self)}")

    def on_neural_turn_detector_end(self, event_id: str = "") -> float:
        """Stop timing and record NeuralTurnDetector latency."""
        latency = self._stop_timer(f"ntd_{event_id or id(self)}")
        if latency > 0:
            self._neural_detector_ms.append(latency)
            self._check_p95_alert("NeuralTurnDetector", self._neural_detector_ms)
        return latency

    # ------------------------------------------------------------------
    # Interruption Classifier  (Requirements: 11.2)
    # ------------------------------------------------------------------

    def on_interruption_classifier_start(self, event_id: str = "") -> None:
        """Start timing InterruptionClassifier processing."""
        self._start_timer(f"ic_{event_id or id(self)}")

    def on_interruption_classifier_end(self, event_id: str = "") -> float:
        """Stop timing and record classifier latency."""
        latency = self._stop_timer(f"ic_{event_id or id(self)}")
        if latency > 0:
            self._interruption_classifier_ms.append(latency)
            self._check_p95_alert("InterruptionClassifier", self._interruption_classifier_ms)
        return latency

    # ------------------------------------------------------------------
    # STT Provider  (Requirements: 11.3)
    # ------------------------------------------------------------------

    def on_stt_provider_start(self, event_id: str = "") -> None:
        """Start timing STT provider transcription round-trip."""
        self._start_timer(f"stt_{event_id or id(self)}")

    def on_stt_provider_end(self, event_id: str = "") -> float:
        """Stop timing and record STT latency."""
        latency = self._stop_timer(f"stt_{event_id or id(self)}")
        if latency > 0:
            self._stt_provider_ms.append(latency)
            self._check_p95_alert("STTProvider", self._stt_provider_ms)
        return latency

    # ------------------------------------------------------------------
    # End-to-end turn detection  (Requirements: 11.4)
    # ------------------------------------------------------------------

    def on_end_to_end_turn_detection_complete(self, latency_ms: float) -> None:
        """Record end-to-end turn detection latency directly."""
        if latency_ms > 0:
            self._end_to_end_ms.append(latency_ms)
            self._check_p95_alert("EndToEndTurnDetection", self._end_to_end_ms)

    # ------------------------------------------------------------------
    # Percentile calculation  (Requirements: 11.5)
    # ------------------------------------------------------------------

    @staticmethod
    def _percentiles(values: list) -> dict:
        """Compute P50, P95, P99 for a list of latency values."""
        if not values:
            return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0,
                    "avg_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0, "count": 0}
        sorted_v = sorted(values)
        n = len(sorted_v)

        def _pct(p):
            idx = max(0, min(n - 1, int(p / 100 * n)))
            return round(sorted_v[idx], 2)

        return {
            "count": n,
            "avg_ms": round(sum(values) / n, 2),
            "min_ms": round(sorted_v[0], 2),
            "max_ms": round(sorted_v[-1], 2),
            "p50_ms": _pct(50),
            "p95_ms": _pct(95),
            "p99_ms": _pct(99),
        }

    def calculate_percentiles(self, component: str) -> dict:
        """
        Get P50/P95/P99 percentiles for a specific component.

        Args:
            component: One of "neural_turn_detector", "interruption_classifier",
                       "stt_provider", "end_to_end"

        Returns:
            Dict with p50_ms, p95_ms, p99_ms, avg_ms, min_ms, max_ms, count

        Requirements: 11.5
        """
        mapping = {
            "neural_turn_detector": self._neural_detector_ms,
            "interruption_classifier": self._interruption_classifier_ms,
            "stt_provider": self._stt_provider_ms,
            "end_to_end": self._end_to_end_ms,
        }
        data = mapping.get(component, [])
        return self._percentiles(data)

    # ------------------------------------------------------------------
    # P95 alerting  (Requirements: 11.6, 11.7)
    # ------------------------------------------------------------------

    def _check_p95_alert(self, component: str, values: list) -> None:
        """
        Emit WARNING if P95 latency exceeds threshold.

        Requirements: 11.6, 11.7
        """
        if len(values) < 5:   # need enough data for meaningful P95
            return
        pcts = self._percentiles(values)
        p95 = pcts["p95_ms"]
        if p95 > self.P95_ALERT_THRESHOLD_MS and component not in self._p95_alerted:
            self._p95_alerted.add(component)
            logger.warning(
                f"[FluidityLatencyTracker] LATENCY ALERT: "
                f"{component} P95={p95:.1f}ms exceeds "
                f"threshold {self.P95_ALERT_THRESHOLD_MS}ms "
                f"[session={self.session_id}]"
            )

    # ------------------------------------------------------------------
    # Dashboard export
    # ------------------------------------------------------------------

    def export_metrics(self) -> dict:
        """
        Export all latency metrics for monitoring dashboard.

        Requirements: 11.7
        """
        return {
            "session_id": self.session_id,
            "neural_turn_detector": self._percentiles(self._neural_detector_ms),
            "interruption_classifier": self._percentiles(self._interruption_classifier_ms),
            "stt_provider": self._percentiles(self._stt_provider_ms),
            "end_to_end_turn_detection": self._percentiles(self._end_to_end_ms),
            "p95_alert_threshold_ms": self.P95_ALERT_THRESHOLD_MS,
        }

    def log_summary(self) -> None:
        """Log human-readable latency summary."""
        metrics = self.export_metrics()
        logger.info("=" * 70)
        logger.info("FLUIDITY LATENCY SUMMARY")
        logger.info("=" * 70)
        for component, key in [
            ("NeuralTurnDetector", "neural_turn_detector"),
            ("InterruptionClassifier", "interruption_classifier"),
            ("STTProvider", "stt_provider"),
            ("EndToEndTurnDetection", "end_to_end_turn_detection"),
        ]:
            stats = metrics[key]
            if stats["count"] > 0:
                p95_ok = "✓" if stats["p95_ms"] <= self.P95_ALERT_THRESHOLD_MS else "✗"
                logger.info(
                    f"  {component:30s}: "
                    f"P50={stats['p50_ms']:6.1f}ms  "
                    f"P95={stats['p95_ms']:6.1f}ms {p95_ok}  "
                    f"P99={stats['p99_ms']:6.1f}ms  "
                    f"n={stats['count']}"
                )
        logger.info("=" * 70)


# Module-level tracker
_global_fluidity_latency_tracker: Optional[FluidityLatencyTracker] = None


def get_fluidity_latency_tracker(session_id: str = "default") -> FluidityLatencyTracker:
    """Get or create global FluidityLatencyTracker."""
    global _global_fluidity_latency_tracker
    if (_global_fluidity_latency_tracker is None
            or _global_fluidity_latency_tracker.session_id != session_id):
        _global_fluidity_latency_tracker = FluidityLatencyTracker(session_id=session_id)
    return _global_fluidity_latency_tracker


def reset_fluidity_latency_tracker() -> None:
    """Reset the tracker (mainly for testing)."""
    global _global_fluidity_latency_tracker
    _global_fluidity_latency_tracker = None
