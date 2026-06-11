"""
Example: Integrating Latency Monitor with Turn-Taking Monitor

This example demonstrates how to use both monitors together for comprehensive
voice interaction tracking. The latency monitor tracks performance metrics
while the turn-taking monitor tracks conversation flow.

Usage in agent.py:
    from latency_monitor import get_latency_monitor
    from vad_turn_taking_monitor import get_turn_taking_monitor
    
    # Initialize both monitors
    latency_monitor = get_latency_monitor(session_id)
    turn_monitor = get_turn_taking_monitor(session_id)
    
    # On user speech end
    latency_monitor.start_interaction()
    latency_monitor.on_user_speech_end()
    turn_monitor.on_user_speech_end()
    
    # On VAD trigger
    latency_monitor.on_vad_trigger()
    turn_monitor.on_vad_trigger()
    
    # On API request/response
    latency_monitor.on_api_request_start()
    latency_monitor.on_api_response_start()
    
    # On TTS generation
    latency_monitor.on_tts_generation_start()
    latency_monitor.on_tts_first_chunk()
    
    # On playback start
    latency_monitor.on_playback_start()
    
    # On Alice speech start
    latency_monitor.on_alice_speech_start()
    turn_monitor.on_alice_speech_start()
    
    # On LLM response (for turn-taking)
    turn_monitor.on_llm_response_start()
    
    # Complete interaction
    latency_monitor.complete_interaction()
    turn_monitor.on_turn_complete()
    
    # Get performance metrics for display
    latency_metrics = latency_monitor.get_performance_metrics_for_display()
    turn_metrics = turn_monitor.get_session_summary()
    
    # Log combined summary
    logger.info(f"Latency: {latency_metrics['session_avg']['total_response_ms']:.1f}ms avg")
    logger.info(f"Turn-taking: {turn_metrics['avg_total_turn_latency_ms']:.1f}ms avg")
"""

import logging
import time
from latency_monitor import get_latency_monitor, reset_latency_monitor
from vad_turn_taking_monitor import get_turn_taking_monitor, reset_turn_taking_monitor

logger = logging.getLogger(__name__)


def simulate_voice_interaction():
    """
    Simulate a complete voice interaction with both monitors.
    
    This demonstrates the integration pattern for agent.py.
    """
    # Initialize monitors
    session_id = "example_session"
    latency_monitor = get_latency_monitor(session_id)
    turn_monitor = get_turn_taking_monitor(session_id)
    
    logger.info("=" * 70)
    logger.info("Starting voice interaction simulation")
    logger.info("=" * 70)
    
    # User starts speaking
    turn_monitor.on_user_speech_start()
    time.sleep(0.5)  # Simulate user speaking for 500ms
    
    # User stops speaking
    latency_monitor.start_interaction()
    latency_monitor.on_user_speech_end()
    turn_monitor.on_user_speech_end()
    
    # VAD detects end of speech (300ms later)
    time.sleep(0.3)
    latency_monitor.on_vad_trigger()
    turn_monitor.on_vad_trigger()
    
    # API request starts
    latency_monitor.on_api_request_start()
    
    # API response arrives (100ms later)
    time.sleep(0.1)
    latency_monitor.on_api_response_start()
    turn_monitor.on_llm_response_start()
    
    # TTS generation starts
    latency_monitor.on_tts_generation_start()
    
    # First TTS chunk ready (150ms later)
    time.sleep(0.15)
    latency_monitor.on_tts_first_chunk()
    
    # Playback starts (30ms later)
    time.sleep(0.03)
    latency_monitor.on_playback_start()
    
    # Alice starts speaking (user hears audio)
    latency_monitor.on_alice_speech_start()
    turn_monitor.on_alice_speech_start()
    
    # Complete interaction
    latency_monitor.complete_interaction()
    turn_monitor.on_turn_complete()
    
    # Get and display metrics
    logger.info("\n" + "=" * 70)
    logger.info("COMBINED METRICS")
    logger.info("=" * 70)
    
    latency_metrics = latency_monitor.get_performance_metrics_for_display()
    turn_metrics = turn_monitor.get_session_summary()
    
    if latency_metrics['session_avg']:
        logger.info(f"Average Response Latency: {latency_metrics['session_avg']['total_response_ms']:.1f}ms")
        logger.info(f"Target Compliance: {latency_metrics['session_avg']['compliance_rate']:.1%}")
    
    if turn_metrics['total_turns'] > 0:
        logger.info(f"Average Turn Latency: {turn_metrics['avg_total_turn_latency_ms']:.1f}ms")
        logger.info(f"Turn-Taking Compliance: {turn_metrics['requirement_compliance_rate']:.1%}")
    
    logger.info("=" * 70)
    
    # Log session summaries
    latency_monitor.log_session_summary()
    turn_monitor.log_session_summary()


def main():
    """Run the integration example"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Reset monitors
    reset_latency_monitor()
    reset_turn_taking_monitor()
    
    # Simulate multiple interactions
    for i in range(3):
        logger.info(f"\n\nInteraction {i+1}/3")
        simulate_voice_interaction()
        time.sleep(1)  # Pause between interactions


if __name__ == "__main__":
    main()
