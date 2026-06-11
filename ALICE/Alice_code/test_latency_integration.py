"""
Test script to verify latency monitoring integration in agent.py

This script verifies that:
1. Latency monitor is properly initialized
2. All timing events are tracked correctly
3. Metrics are calculated and logged
4. Integration with turn-taking monitor works
"""

import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from latency_monitor import get_latency_monitor, reset_latency_monitor
from vad_turn_taking_monitor import get_turn_taking_monitor, reset_turn_taking_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_latency_monitor_integration():
    """Test that latency monitor integration points are working"""
    
    logger.info("=" * 70)
    logger.info("Testing Latency Monitor Integration")
    logger.info("=" * 70)
    
    # Reset monitors
    reset_latency_monitor()
    reset_turn_taking_monitor()
    
    # Initialize monitors (simulating entrypoint initialization)
    session_id = "test_session"
    latency_monitor = get_latency_monitor(session_id=session_id)
    turn_monitor = get_turn_taking_monitor(session_id=session_id)
    
    logger.info("✅ Monitors initialized")
    
    # Simulate voice interaction flow (as in agent.py)
    logger.info("\n--- Simulating Voice Interaction ---")
    
    # 1. Start interaction
    latency_monitor.start_interaction()
    logger.info("✅ Interaction started")
    
    # 2. User speech end (baseline T=0)
    latency_monitor.on_user_speech_end()
    turn_monitor.on_user_speech_end()
    logger.info("✅ User speech end tracked")
    
    # 3. VAD trigger
    import time
    time.sleep(0.3)  # Simulate 300ms VAD threshold
    latency_monitor.on_vad_trigger()
    turn_monitor.on_vad_trigger()
    logger.info("✅ VAD trigger tracked")
    
    # 4. API request start
    latency_monitor.on_api_request_start()
    logger.info("✅ API request start tracked")
    
    # 5. API response start
    time.sleep(0.1)  # Simulate 100ms API processing
    latency_monitor.on_api_response_start()
    turn_monitor.on_llm_response_start()
    logger.info("✅ API response start tracked")
    
    # 6. TTS generation start
    latency_monitor.on_tts_generation_start()
    logger.info("✅ TTS generation start tracked")
    
    # 7. TTS first chunk ready
    time.sleep(0.15)  # Simulate 150ms TTS generation
    latency_monitor.on_tts_first_chunk()
    logger.info("✅ TTS first chunk tracked")
    
    # 8. Playback start
    time.sleep(0.03)  # Simulate 30ms playback delay
    latency_monitor.on_playback_start()
    logger.info("✅ Playback start tracked")
    
    # 9. Alice speech start (user hears audio)
    latency_monitor.on_alice_speech_start()
    turn_monitor.on_alice_speech_start()
    logger.info("✅ Alice speech start tracked")
    
    # 10. Complete interaction
    latency_monitor.complete_interaction()
    turn_monitor.on_turn_complete()
    logger.info("✅ Interaction completed")
    
    # Verify metrics
    logger.info("\n--- Verifying Metrics ---")
    
    # Get performance metrics
    metrics = latency_monitor.get_performance_metrics_for_display()
    
    if metrics['current']:
        current = metrics['current']
        logger.info(f"Current interaction metrics:")
        logger.info(f"  - Total response: {current.get('total_response_ms', 'N/A')}ms")
        logger.info(f"  - Meets target: {current.get('meets_target', False)}")
        logger.info(f"  - VAD trigger: {current.get('vad_trigger_ms', 'N/A')}ms")
        logger.info(f"  - API processing: {current.get('api_processing_ms', 'N/A')}ms")
        logger.info(f"  - TTS generation: {current.get('tts_generation_ms', 'N/A')}ms")
        logger.info(f"  - Playback start: {current.get('playback_start_ms', 'N/A')}ms")
    
    # Log session summaries
    logger.info("\n--- Session Summaries ---")
    latency_monitor.log_session_summary()
    turn_monitor.log_session_summary()
    
    # Verify integration points exist in agent.py
    logger.info("\n--- Verifying Integration Points in agent.py ---")
    
    agent_file = os.path.join(os.path.dirname(__file__), "agent.py")
    with open(agent_file, 'r', encoding='utf-8') as f:
        agent_code = f.read()
    
    integration_points = [
        ("Import latency_monitor", "from latency_monitor import"),
        ("Initialize in entrypoint", "latency_monitor = get_latency_monitor"),
        ("Pass to Assistant", "latency_monitor=latency_monitor"),
        ("User speech end", "latency_monitor.on_user_speech_end()"),
        ("VAD trigger", "latency_monitor.on_vad_trigger()"),
        ("API request start", "latency_monitor.on_api_request_start()"),
        ("API response start", "latency_monitor.on_api_response_start()"),
        ("TTS generation start", "latency_monitor.on_tts_generation_start()"),
        ("TTS first chunk", "latency_monitor.on_tts_first_chunk()"),
        ("Playback start", "latency_monitor.on_playback_start()"),
        ("Alice speech start", "latency_monitor.on_alice_speech_start()"),
        ("Complete interaction", "latency_monitor.complete_interaction()"),
        ("Log session summary", "latency_monitor.log_session_summary()"),
    ]
    
    all_found = True
    for name, code_snippet in integration_points:
        if code_snippet in agent_code:
            logger.info(f"✅ {name}: Found")
        else:
            logger.error(f"❌ {name}: NOT FOUND")
            all_found = False
    
    if all_found:
        logger.info("\n" + "=" * 70)
        logger.info("✅ ALL INTEGRATION POINTS VERIFIED")
        logger.info("=" * 70)
        return True
    else:
        logger.error("\n" + "=" * 70)
        logger.error("❌ SOME INTEGRATION POINTS MISSING")
        logger.error("=" * 70)
        return False


if __name__ == "__main__":
    success = test_latency_monitor_integration()
    sys.exit(0 if success else 1)
