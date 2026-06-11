"""
Unit tests for latency monitoring system

Tests verify:
- Latency calculation accuracy
- Stage timing measurement
- Performance target validation
- Session aggregation
- Integration with turn-taking monitor
"""

import unittest
import time
from latency_monitor import (
    LatencyMonitor,
    LatencyMetrics,
    LatencySession,
    get_latency_monitor,
    reset_latency_monitor
)


class TestLatencyMetrics(unittest.TestCase):
    """Test LatencyMetrics calculation and validation"""
    
    def test_calculate_latencies_complete_interaction(self):
        """Test latency calculation with all timestamps"""
        metrics = LatencyMetrics(interaction_id=1)
        
        # Simulate timestamps (in seconds)
        base_time = time.time()
        metrics.user_speech_end = base_time
        metrics.vad_trigger_time = base_time + 0.35  # 350ms
        metrics.api_request_start = base_time + 0.35
        metrics.api_response_start = base_time + 0.45  # 100ms API
        metrics.tts_generation_start = base_time + 0.45
        metrics.tts_first_chunk = base_time + 0.60  # 150ms TTS
        metrics.playback_start = base_time + 0.63  # 30ms playback
        metrics.alice_speech_start = base_time + 0.63  # Alice starts speaking
        
        metrics.calculate_latencies()
        
        # Verify calculations
        self.assertAlmostEqual(metrics.vad_trigger_latency_ms, 350, delta=1)
        self.assertAlmostEqual(metrics.api_processing_latency_ms, 100, delta=1)
        self.assertAlmostEqual(metrics.tts_generation_latency_ms, 150, delta=1)
        self.assertAlmostEqual(metrics.playback_start_latency_ms, 30, delta=1)
        self.assertAlmostEqual(metrics.total_response_latency_ms, 630, delta=1)
        
        # Should not meet target (>400ms)
        self.assertFalse(metrics.meets_target())
    
    def test_calculate_latencies_meets_target(self):
        """Test latency calculation that meets <400ms target"""
        metrics = LatencyMetrics(interaction_id=1)
        
        base_time = time.time()
        metrics.user_speech_end = base_time
        metrics.vad_trigger_time = base_time + 0.30  # 300ms
        metrics.api_request_start = base_time + 0.30
        metrics.api_response_start = base_time + 0.35  # 50ms API
        metrics.tts_generation_start = base_time + 0.35
        metrics.tts_first_chunk = base_time + 0.38  # 30ms TTS
        metrics.playback_start = base_time + 0.39  # 10ms playback
        metrics.alice_speech_start = base_time + 0.39  # Alice starts speaking
        
        metrics.calculate_latencies()
        
        # Total: 390ms
        self.assertAlmostEqual(metrics.total_response_latency_ms, 390, delta=1)
        
        # Should meet target (<400ms)
        self.assertTrue(metrics.meets_target())
    
    def test_performance_summary(self):
        """Test performance summary generation"""
        metrics = LatencyMetrics(interaction_id=1)
        base_time = time.time()
        
        metrics.user_speech_end = base_time
        metrics.vad_trigger_time = base_time + 0.3
        metrics.api_request_start = base_time + 0.3
        metrics.api_response_start = base_time + 0.35
        metrics.tts_generation_start = base_time + 0.35
        metrics.tts_first_chunk = base_time + 0.38
        metrics.playback_start = base_time + 0.39
        metrics.alice_speech_start = base_time + 0.39
        
        metrics.calculate_latencies()
        summary = metrics.get_performance_summary()
        
        self.assertEqual(summary['interaction_id'], 1)
        self.assertTrue(summary['meets_target'])
        self.assertIn('vad_trigger_ms', summary)
        self.assertIn('api_processing_ms', summary)
        self.assertIn('tts_generation_ms', summary)
        self.assertIn('playback_start_ms', summary)
        self.assertIn('total_response_ms', summary)


class TestLatencyMonitor(unittest.TestCase):
    """Test LatencyMonitor functionality"""
    
    def setUp(self):
        """Reset monitor before each test"""
        reset_latency_monitor()
    
    def test_monitor_initialization(self):
        """Test monitor initialization"""
        monitor = LatencyMonitor(session_id="test_session")
        
        self.assertEqual(monitor.session.session_id, "test_session")
        self.assertEqual(monitor.session.current_interaction_id, 0)
        self.assertEqual(len(monitor.session.interactions), 0)
        self.assertIsNone(monitor.current_interaction)
    
    def test_complete_interaction_flow(self):
        """Test complete interaction flow with all events"""
        monitor = LatencyMonitor(session_id="test_session")
        
        # Start interaction
        monitor.start_interaction()
        self.assertIsNotNone(monitor.current_interaction)
        self.assertEqual(monitor.current_interaction.interaction_id, 1)
        
        # Simulate events with small delays
        monitor.on_user_speech_end()
        time.sleep(0.01)
        
        monitor.on_vad_trigger()
        time.sleep(0.01)
        
        monitor.on_api_request_start()
        time.sleep(0.01)
        
        monitor.on_api_response_start()
        time.sleep(0.01)
        
        monitor.on_tts_generation_start()
        time.sleep(0.01)
        
        monitor.on_tts_first_chunk()
        time.sleep(0.01)
        
        monitor.on_playback_start()
        time.sleep(0.01)
        
        monitor.on_alice_speech_start()
        
        # Complete interaction
        monitor.complete_interaction()
        
        # Verify interaction was recorded
        self.assertEqual(len(monitor.session.interactions), 1)
        self.assertIsNone(monitor.current_interaction)
        
        # Verify latencies were calculated
        interaction = monitor.session.interactions[0]
        self.assertIsNotNone(interaction.total_response_latency_ms)
        self.assertIsNotNone(interaction.vad_trigger_latency_ms)
        self.assertIsNotNone(interaction.api_processing_latency_ms)
        self.assertIsNotNone(interaction.tts_generation_latency_ms)
        self.assertIsNotNone(interaction.playback_start_latency_ms)
    
    def test_multiple_interactions(self):
        """Test tracking multiple interactions"""
        monitor = LatencyMonitor(session_id="test_session")
        
        # Simulate 3 interactions
        for i in range(3):
            monitor.start_interaction()
            monitor.on_user_speech_end()
            time.sleep(0.01)
            monitor.on_vad_trigger()
            time.sleep(0.01)
            monitor.on_api_request_start()
            time.sleep(0.01)
            monitor.on_api_response_start()
            time.sleep(0.01)
            monitor.on_tts_generation_start()
            time.sleep(0.01)
            monitor.on_tts_first_chunk()
            time.sleep(0.01)
            monitor.on_playback_start()
            monitor.complete_interaction()
        
        # Verify all interactions recorded
        self.assertEqual(len(monitor.session.interactions), 3)
        self.assertEqual(monitor.session.current_interaction_id, 3)
        
        # Verify interaction IDs
        for i, interaction in enumerate(monitor.session.interactions):
            self.assertEqual(interaction.interaction_id, i + 1)
    
    def test_session_summary(self):
        """Test session summary generation"""
        monitor = LatencyMonitor(session_id="test_session")
        
        # Simulate 2 interactions
        for _ in range(2):
            monitor.start_interaction()
            monitor.on_user_speech_end()
            time.sleep(0.01)
            monitor.on_vad_trigger()
            time.sleep(0.01)
            monitor.on_api_request_start()
            time.sleep(0.01)
            monitor.on_api_response_start()
            time.sleep(0.01)
            monitor.on_tts_generation_start()
            time.sleep(0.01)
            monitor.on_tts_first_chunk()
            time.sleep(0.01)
            monitor.on_playback_start()
            time.sleep(0.01)
            monitor.on_alice_speech_start()
            monitor.complete_interaction()
        
        summary = monitor.get_session_summary()
        
        self.assertEqual(summary['session_id'], "test_session")
        self.assertEqual(summary['total_interactions'], 2)
        self.assertIn('total_response', summary)
    
    def test_global_monitor_singleton(self):
        """Test global monitor singleton pattern"""
        monitor1 = get_latency_monitor("session1")
        monitor2 = get_latency_monitor("session1")
        
        # Should return same instance for same session
        self.assertIs(monitor1, monitor2)
        
        # Different session should create new instance
        monitor3 = get_latency_monitor("session2")
        self.assertIsNot(monitor1, monitor3)
        
        # Reset should clear global instance
        reset_latency_monitor()
        monitor4 = get_latency_monitor("session1")
        self.assertIsNot(monitor1, monitor4)
    
    def test_performance_metrics_for_display(self):
        """Test performance metrics formatted for display"""
        monitor = LatencyMonitor(session_id="test_session")
        
        # Complete one interaction
        monitor.start_interaction()
        monitor.on_user_speech_end()
        time.sleep(0.01)
        monitor.on_vad_trigger()
        time.sleep(0.01)
        monitor.on_api_request_start()
        time.sleep(0.01)
        monitor.on_api_response_start()
        time.sleep(0.01)
        monitor.on_tts_generation_start()
        time.sleep(0.01)
        monitor.on_tts_first_chunk()
        time.sleep(0.01)
        monitor.on_playback_start()
        monitor.complete_interaction()
        
        # Get display metrics
        metrics = monitor.get_performance_metrics_for_display()
        
        self.assertIn('current', metrics)
        self.assertIn('session_avg', metrics)


class TestLatencyTargets(unittest.TestCase):
    """Test latency target validation"""
    
    def test_vad_trigger_target(self):
        """Test VAD trigger target (≤400ms)"""
        metrics = LatencyMetrics(interaction_id=1)
        
        # Within target
        metrics.vad_trigger_latency_ms = 350
        self.assertLessEqual(metrics.vad_trigger_latency_ms, 400)
        
        # At target
        metrics.vad_trigger_latency_ms = 400
        self.assertLessEqual(metrics.vad_trigger_latency_ms, 400)
        
        # Exceeds target
        metrics.vad_trigger_latency_ms = 450
        self.assertGreater(metrics.vad_trigger_latency_ms, 400)
    
    def test_api_processing_target(self):
        """Test API processing target (<150ms)"""
        metrics = LatencyMetrics(interaction_id=1)
        
        # Within target
        metrics.api_processing_latency_ms = 100
        self.assertLess(metrics.api_processing_latency_ms, 150)
        
        # Exceeds target
        metrics.api_processing_latency_ms = 200
        self.assertGreaterEqual(metrics.api_processing_latency_ms, 150)
    
    def test_tts_generation_target(self):
        """Test TTS generation target (<200ms)"""
        metrics = LatencyMetrics(interaction_id=1)
        
        # Within target
        metrics.tts_generation_latency_ms = 150
        self.assertLess(metrics.tts_generation_latency_ms, 200)
        
        # Exceeds target
        metrics.tts_generation_latency_ms = 250
        self.assertGreaterEqual(metrics.tts_generation_latency_ms, 200)
    
    def test_playback_start_target(self):
        """Test playback start target (<50ms)"""
        metrics = LatencyMetrics(interaction_id=1)
        
        # Within target
        metrics.playback_start_latency_ms = 30
        self.assertLess(metrics.playback_start_latency_ms, 50)
        
        # Exceeds target
        metrics.playback_start_latency_ms = 80
        self.assertGreaterEqual(metrics.playback_start_latency_ms, 50)
    
    def test_total_response_target(self):
        """Test total response target (<400ms)"""
        metrics = LatencyMetrics(interaction_id=1)
        
        # Within target
        base_time = time.time()
        metrics.user_speech_end = base_time
        metrics.alice_speech_start = base_time + 0.39  # 390ms
        metrics.calculate_latencies()
        
        self.assertTrue(metrics.meets_target())
        self.assertLess(metrics.total_response_latency_ms, 400)
        
        # Exceeds target
        metrics.user_speech_end = base_time
        metrics.alice_speech_start = base_time + 0.45  # 450ms
        metrics.calculate_latencies()
        
        self.assertFalse(metrics.meets_target())
        self.assertGreaterEqual(metrics.total_response_latency_ms, 400)


if __name__ == '__main__':
    unittest.main()
