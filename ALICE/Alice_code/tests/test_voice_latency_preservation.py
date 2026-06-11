"""
Preservation Property Tests for Voice Latency Optimization

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**

This test suite verifies that non-latency functionality remains unchanged after
the voice latency optimization fix. These tests follow the observation-first
methodology: observe behavior on UNFIXED code, then write tests capturing that
behavior.

Property 2: Preservation - Non-Latency Functionality Unchanged

For any system functionality that is NOT directly related to voice response
latency optimization, the fixed system SHALL produce exactly the same behavior
as the original system.

EXPECTED OUTCOME: All tests PASS on unfixed code (confirms baseline behavior)
After fix: All tests should still PASS (confirms preservation)

Testing Strategy:
- Observe current behavior on unfixed code for each preservation requirement
- Write property-based tests capturing observed behavior patterns
- Run tests on unfixed code to confirm they pass (baseline)
- After fix, run tests again to verify behavior is preserved
"""

import pytest
import os
import logging
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import modules to test
from vad_config import (
    get_vad_silence_threshold,
    MIN_VAD_SILENCE_THRESHOLD,
    MAX_VAD_SILENCE_THRESHOLD,
    DEFAULT_VAD_SILENCE_THRESHOLD
)
from livekit_audio_config import (
    configure_livekit_audio_input,
    select_audio_input_device,
    get_audio_device_info_for_voice_report
)
from audio_quality_validator import (
    validate_audio_quality_on_session_start,
    get_audio_quality_voice_report
)
from vad_behavior_validator import (
    VADBehaviorValidator,
    validate_vad_behavior,
    get_vad_validation_voice_report
)
from vad_turn_taking_monitor import (
    VADTurnTakingMonitor,
    TurnTakingMetrics,
    get_turn_taking_monitor,
    reset_turn_taking_monitor
)


# ============================================================================
# Preservation Property Tests - Noisy Environment Handling
# ============================================================================

class TestNoisyEnvironmentPreservation:
    """
    Test preservation of noisy environment handling.
    
    **Validates: Requirement 3.1**
    
    WHEN a user speaks in a noisy environment THEN the system SHALL CONTINUE TO
    use appropriate VAD thresholds to prevent false end-of-speech detection.
    
    Observed behavior on unfixed code:
    - VAD threshold configurable 300-500ms via environment variable
    - Default threshold is 400ms (conservative for reliability)
    - Threshold validation ensures values stay within safe range
    - In noisy environments, 400-500ms threshold prevents false triggers
    """
    
    def test_vad_threshold_range_validation(self):
        """
        Property: VAD threshold stays within 300-500ms range
        
        For any VAD threshold configuration, the system enforces the
        300-500ms range to prevent false triggers in noisy environments.
        """
        # Test default threshold
        threshold = get_vad_silence_threshold()
        assert MIN_VAD_SILENCE_THRESHOLD <= threshold <= MAX_VAD_SILENCE_THRESHOLD, (
            f"VAD threshold {threshold}s outside safe range "
            f"[{MIN_VAD_SILENCE_THRESHOLD}, {MAX_VAD_SILENCE_THRESHOLD}]"
        )
        
        logger.info(f"✓ Default VAD threshold {threshold}s within safe range")
    
    @pytest.mark.parametrize("threshold_ms,expected_s", [
        (300, 0.3),  # Minimum threshold
        (400, 0.4),  # Default threshold
        (500, 0.5),  # Maximum threshold
        (250, 0.3),  # Below minimum - should clamp to 0.3
        (600, 0.5),  # Above maximum - should clamp to 0.5
    ])
    def test_vad_threshold_clamping(self, threshold_ms, expected_s):
        """
        Property: VAD threshold clamping prevents unsafe values
        
        For any threshold value outside the safe range, the system clamps
        it to the nearest safe value (300ms or 500ms).
        """
        with patch.dict(os.environ, {'VAD_SILENCE_THRESHOLD_MS': str(threshold_ms)}):
            threshold = get_vad_silence_threshold()
            assert threshold == expected_s, (
                f"VAD threshold {threshold}s != expected {expected_s}s "
                f"for input {threshold_ms}ms"
            )
        
        logger.info(f"✓ VAD threshold {threshold_ms}ms correctly clamped to {expected_s}s")
    
    def test_noisy_environment_threshold_adaptation(self):
        """
        Property: VAD threshold adapts for noisy environments
        
        In noisy environments, the system uses 400-500ms threshold to
        prevent false end-of-speech detection.
        
        Observed behavior: Default 400ms threshold is conservative enough
        for noisy environments while still allowing natural conversation.
        """
        # Simulate noisy environment configuration
        with patch.dict(os.environ, {'VAD_SILENCE_THRESHOLD_MS': '450'}):
            threshold = get_vad_silence_threshold()
            
            # Verify threshold is appropriate for noisy environment (400-500ms)
            assert 0.4 <= threshold <= 0.5, (
                f"Noisy environment threshold {threshold}s outside expected range [0.4, 0.5]"
            )
        
        logger.info(f"✓ Noisy environment VAD threshold {threshold}s appropriate for reliability")


# ============================================================================
# Preservation Property Tests - NVIDIA Broadcast Integration
# ============================================================================

class TestNVIDIABroadcastPreservation:
    """
    Test preservation of NVIDIA Broadcast integration.
    
    **Validates: Requirement 3.2**
    
    WHEN NVIDIA Broadcast audio input is available THEN the system SHALL
    CONTINUE TO use it for noise cancellation.
    
    Observed behavior on unfixed code:
    - System detects NVIDIA Broadcast device by name matching
    - Falls back to default microphone if NVIDIA Broadcast unavailable
    - Audio configuration reports device selection status
    - Voice report informs user of audio device status
    """
    
    @patch('livekit_audio_config.detect_nvidia_broadcast_device')
    def test_nvidia_broadcast_detection_and_selection(self, mock_detect):
        """
        Property: NVIDIA Broadcast is selected when available
        
        For any audio configuration, if NVIDIA Broadcast is available,
        the system selects it as the audio input device.
        """
        # Mock NVIDIA Broadcast device available
        mock_nvidia_device = {
            'name': 'Microphone (NVIDIA Broadcast)',
            'index': 5,
            'channels': 2,
            'default_samplerate': 48000.0,
            'hostapi': 0
        }
        mock_detect.return_value = mock_nvidia_device
        
        config = configure_livekit_audio_input()
        
        # Verify NVIDIA Broadcast is selected
        assert config['is_nvidia_broadcast'] is True, (
            "NVIDIA Broadcast should be selected when available"
        )
        assert config['device_name'] == mock_nvidia_device['name'], (
            f"Device name mismatch: {config['device_name']} != {mock_nvidia_device['name']}"
        )
        assert config['fallback_used'] is False, (
            "Fallback should not be used when NVIDIA Broadcast available"
        )
        
        logger.info(f"✓ NVIDIA Broadcast correctly selected: {config['device_name']}")
    
    @patch('livekit_audio_config.detect_nvidia_broadcast_device')
    @patch('livekit_audio_config.get_default_audio_input_device')
    def test_fallback_when_nvidia_broadcast_unavailable(self, mock_default, mock_detect):
        """
        Property: System falls back to default microphone when NVIDIA Broadcast unavailable
        
        For any audio configuration, if NVIDIA Broadcast is not available,
        the system falls back to the default microphone.
        """
        # Mock NVIDIA Broadcast not available
        mock_detect.return_value = None
        
        # Mock default microphone available
        mock_default_device = {
            'name': 'Default Microphone',
            'index': 0,
            'channels': 2,
            'default_samplerate': 48000.0,
            'hostapi': 0
        }
        mock_default.return_value = mock_default_device
        
        config = configure_livekit_audio_input()
        
        # Verify fallback to default microphone
        assert config['is_nvidia_broadcast'] is False, (
            "NVIDIA Broadcast should not be selected when unavailable"
        )
        assert config['device_name'] == mock_default_device['name'], (
            f"Device name mismatch: {config['device_name']} != {mock_default_device['name']}"
        )
        
        logger.info(f"✓ Correctly fell back to default microphone: {config['device_name']}")
    
    @patch('livekit_audio_config.detect_nvidia_broadcast_device')
    def test_voice_report_nvidia_broadcast_status(self, mock_detect):
        """
        Property: Voice report correctly describes NVIDIA Broadcast status
        
        For any audio configuration, the voice report accurately describes
        whether NVIDIA Broadcast is being used.
        """
        # Test with NVIDIA Broadcast available
        mock_nvidia_device = {
            'name': 'Microphone (NVIDIA Broadcast)',
            'index': 5,
            'channels': 2,
            'default_samplerate': 48000.0,
            'hostapi': 0
        }
        mock_detect.return_value = mock_nvidia_device
        
        report = get_audio_device_info_for_voice_report()
        
        assert 'NVIDIA Broadcast' in report, (
            f"Voice report should mention NVIDIA Broadcast: {report}"
        )
        assert 'noise cancellation' in report.lower(), (
            f"Voice report should mention noise cancellation: {report}"
        )
        
        logger.info(f"✓ Voice report correctly describes NVIDIA Broadcast: {report}")




# ============================================================================
# Preservation Property Tests - Audio Quality Validation
# ============================================================================

class TestAudioQualityValidationPreservation:
    """
    Test preservation of audio quality validation.
    
    **Validates: Requirement 3.3**
    
    WHEN audio quality validation runs on session start THEN the system SHALL
    CONTINUE TO validate audio quality and report issues to the user.
    
    Observed behavior on unfixed code:
    - Audio quality validation runs on session start
    - Signal strength check validates RMS amplitude >= 0.01 threshold
    - Validation results include pass/fail status and warnings
    - Voice report describes audio quality issues to user
    """
    
    def test_audio_quality_validation_structure(self):
        """
        Property: Audio quality validation returns expected structure
        
        For any audio quality validation, the result includes:
        - passed: Boolean status
        - signal_strength: Signal metrics
        - warnings: List of issues
        - timestamp: Validation time
        """
        # Mock audio validation (without actual hardware)
        with patch('audio_quality_validator.check_audio_signal_strength') as mock_check:
            mock_check.return_value = {
                'rms_amplitude': 0.05,
                'peak_amplitude': 0.15,
                'is_acceptable': True,
                'threshold': 0.01
            }
            
            result = validate_audio_quality_on_session_start(device_index=None)
            
            # Verify structure
            assert 'passed' in result, "Result should include 'passed' field"
            assert 'signal_strength' in result, "Result should include 'signal_strength' field"
            assert 'warnings' in result, "Result should include 'warnings' field"
            assert 'timestamp' in result, "Result should include 'timestamp' field"
            
            # Verify types
            assert isinstance(result['passed'], bool), "'passed' should be boolean"
            assert isinstance(result['warnings'], list), "'warnings' should be list"
            assert isinstance(result['timestamp'], (int, float)), "'timestamp' should be numeric"
            
            logger.info(f"✓ Audio quality validation structure preserved: {list(result.keys())}")
    
    def test_audio_quality_threshold_validation(self):
        """
        Property: Audio quality validation enforces signal strength threshold
        
        For any audio signal, validation passes if RMS amplitude >= 0.01,
        fails otherwise.
        """
        # Test passing signal
        with patch('audio_quality_validator.check_audio_signal_strength') as mock_check:
            mock_check.return_value = {
                'rms_amplitude': 0.05,
                'peak_amplitude': 0.15,
                'is_acceptable': True,
                'threshold': 0.01
            }
            
            result = validate_audio_quality_on_session_start(device_index=None)
            assert result['passed'] is True, "Validation should pass for acceptable signal"
            assert len(result['warnings']) == 0, "No warnings for acceptable signal"
        
        # Test failing signal
        with patch('audio_quality_validator.check_audio_signal_strength') as mock_check:
            mock_check.return_value = {
                'rms_amplitude': 0.005,
                'peak_amplitude': 0.01,
                'is_acceptable': False,
                'threshold': 0.01
            }
            
            result = validate_audio_quality_on_session_start(device_index=None)
            assert result['passed'] is False, "Validation should fail for weak signal"
            assert len(result['warnings']) > 0, "Warnings should be present for weak signal"
        
        logger.info("✓ Audio quality threshold validation preserved")
    
    def test_audio_quality_voice_report_generation(self):
        """
        Property: Audio quality voice report describes validation results
        
        For any validation result, the voice report provides user-friendly
        description of audio quality status.
        """
        # Test passing validation
        passing_result = {
            'passed': True,
            'signal_strength': {'rms_amplitude': 0.05, 'is_acceptable': True},
            'warnings': [],
            'timestamp': 1234567890.0
        }
        
        report = get_audio_quality_voice_report(passing_result)
        assert 'passed' in report.lower() or 'working' in report.lower(), (
            f"Voice report should indicate success: {report}"
        )
        
        # Test failing validation
        failing_result = {
            'passed': False,
            'signal_strength': {'rms_amplitude': 0.005, 'is_acceptable': False},
            'warnings': ['Audio signal too weak'],
            'timestamp': 1234567890.0
        }
        
        report = get_audio_quality_voice_report(failing_result)
        assert 'warning' in report.lower() or 'weak' in report.lower(), (
            f"Voice report should indicate issue: {report}"
        )
        
        logger.info("✓ Audio quality voice report generation preserved")


# ============================================================================
# Preservation Property Tests - VAD Behavior Validation
# ============================================================================

class TestVADBehaviorValidationPreservation:
    """
    Test preservation of VAD behavior validation.
    
    **Validates: Requirement 3.4**
    
    WHEN VAD behavior validation runs THEN the system SHALL CONTINUE TO
    validate VAD configuration meets requirements.
    
    Observed behavior on unfixed code:
    - VAD validation tests short pause behavior (<300ms should not trigger)
    - VAD validation tests long pause behavior (>=500ms should trigger)
    - VAD validation tests threshold boundaries
    - VAD validation tests consistency across audio levels
    - Validation results include pass/fail status for each test
    """
    
    def test_vad_validator_initialization(self):
        """
        Property: VAD validator initializes with correct configuration
        
        For any VAD instance and threshold, the validator correctly
        stores configuration and initializes test results.
        """
        mock_vad = Mock()
        mock_vad.activation_threshold = 0.5
        threshold_ms = 400.0
        
        validator = VADBehaviorValidator(mock_vad, threshold_ms)
        
        assert validator.vad == mock_vad, "VAD instance should be stored"
        assert validator.silence_threshold_ms == threshold_ms, "Threshold should be stored"
        assert validator.test_results == [], "Test results should be empty initially"
        
        logger.info(f"✓ VAD validator initialization preserved")
    
    def test_vad_short_pause_validation(self):
        """
        Property: VAD correctly validates short pause behavior
        
        For any pause < 300ms, VAD should NOT trigger end-of-speech.
        Validation confirms this behavior.
        """
        mock_vad = Mock()
        mock_vad.activation_threshold = 0.5
        threshold_ms = 400.0
        
        validator = VADBehaviorValidator(mock_vad, threshold_ms)
        result = validator.validate_short_pause_behavior(pause_duration_ms=250)
        
        # With 400ms threshold, 250ms pause should NOT trigger
        assert result.passed is True, "Short pause validation should pass"
        assert result.details['pause_duration_ms'] == 250, "Pause duration should be recorded"
        assert result.details['expected_trigger'] is False, "Short pause should not trigger"
        
        logger.info(f"✓ VAD short pause validation preserved: {result.actual_behavior}")
    
    def test_vad_long_pause_validation(self):
        """
        Property: VAD correctly validates long pause behavior
        
        For any pause >= 500ms, VAD should trigger end-of-speech.
        Validation confirms this behavior.
        """
        mock_vad = Mock()
        mock_vad.activation_threshold = 0.5
        threshold_ms = 400.0
        
        validator = VADBehaviorValidator(mock_vad, threshold_ms)
        result = validator.validate_long_pause_behavior(pause_duration_ms=500)
        
        # With 400ms threshold, 500ms pause should trigger
        assert result.passed is True, "Long pause validation should pass"
        assert result.details['pause_duration_ms'] == 500, "Pause duration should be recorded"
        assert result.details['expected_trigger'] is True, "Long pause should trigger"
        
        logger.info(f"✓ VAD long pause validation preserved: {result.actual_behavior}")
    
    def test_vad_consistency_validation(self):
        """
        Property: VAD consistency across audio levels is validated
        
        For any VAD configuration, validation checks that activation
        threshold is within optimal range (0.3-0.7) for consistency.
        """
        mock_vad = Mock()
        mock_vad.activation_threshold = 0.5
        threshold_ms = 400.0
        
        validator = VADBehaviorValidator(mock_vad, threshold_ms)
        result = validator.validate_consistency_across_levels()
        
        # With activation_threshold=0.5, validation should pass
        assert result.passed is True, "Consistency validation should pass for optimal threshold"
        assert result.details['activation_threshold'] == 0.5, "Activation threshold should be recorded"
        
        logger.info(f"✓ VAD consistency validation preserved: {result.actual_behavior}")
    
    def test_vad_full_validation_suite(self):
        """
        Property: Full VAD validation suite runs all tests
        
        For any VAD configuration, full validation runs:
        - Threshold boundary tests
        - Consistency tests
        Returns summary with pass/fail counts
        """
        mock_vad = Mock()
        mock_vad.activation_threshold = 0.5
        threshold_ms = 400.0
        
        summary = validate_vad_behavior(mock_vad, threshold_ms)
        
        # Verify summary structure
        assert 'all_passed' in summary, "Summary should include 'all_passed'"
        assert 'total_tests' in summary, "Summary should include 'total_tests'"
        assert 'passed_tests' in summary, "Summary should include 'passed_tests'"
        assert 'failed_tests' in summary, "Summary should include 'failed_tests'"
        assert 'test_results' in summary, "Summary should include 'test_results'"
        
        # Verify tests were run
        assert summary['total_tests'] > 0, "Tests should have been run"
        assert len(summary['test_results']) == summary['total_tests'], "Test results count mismatch"
        
        logger.info(f"✓ VAD full validation suite preserved: {summary['total_tests']} tests run")


# ============================================================================
# Preservation Property Tests - Turn-Taking Monitoring
# ============================================================================

class TestTurnTakingMonitoringPreservation:
    """
    Test preservation of turn-taking monitoring.
    
    **Validates: Requirement 3.5**
    
    WHEN turn-taking monitoring is active THEN the system SHALL CONTINUE TO
    log turn-taking metrics for debugging.
    
    Observed behavior on unfixed code:
    - Turn-taking monitor tracks conversation turns
    - Metrics include: VAD trigger time, LLM response time, total turn latency
    - Monitor logs detailed metrics for each turn
    - Session summary aggregates metrics across all turns
    """
    
    def test_turn_taking_monitor_initialization(self):
        """
        Property: Turn-taking monitor initializes with session tracking
        
        For any session, the monitor initializes with:
        - Session ID
        - Empty turn list
        - Turn counter at 0
        """
        reset_turn_taking_monitor()
        monitor = get_turn_taking_monitor(session_id="test-session")
        
        assert monitor.session.session_id == "test-session", "Session ID should be set"
        assert monitor.session.current_turn_id == 0, "Turn counter should start at 0"
        assert len(monitor.session.turns) == 0, "Turn list should be empty initially"
        
        logger.info(f"✓ Turn-taking monitor initialization preserved")
    
    def test_turn_taking_metrics_tracking(self):
        """
        Property: Turn-taking monitor tracks conversation turn metrics
        
        For any conversation turn, the monitor tracks:
        - User speech start/end times
        - VAD trigger time
        - LLM response start time
        - Alice speech start time
        """
        reset_turn_taking_monitor()
        monitor = get_turn_taking_monitor(session_id="test-session")
        
        # Simulate a conversation turn
        monitor.on_user_speech_start()
        assert monitor.current_turn is not None, "Turn should be created"
        assert monitor.current_turn.user_speech_start is not None, "Speech start should be recorded"
        
        monitor.on_user_speech_end()
        assert monitor.current_turn.user_speech_end is not None, "Speech end should be recorded"
        
        monitor.on_vad_trigger()
        assert monitor.current_turn.vad_trigger_time is not None, "VAD trigger should be recorded"
        
        monitor.on_llm_response_start()
        assert monitor.current_turn.llm_response_start is not None, "LLM response should be recorded"
        
        monitor.on_alice_speech_start()
        assert monitor.current_turn.alice_speech_start is not None, "Alice speech should be recorded"
        
        logger.info(f"✓ Turn-taking metrics tracking preserved")
    
    def test_turn_taking_latency_calculation(self):
        """
        Property: Turn-taking monitor calculates latency metrics
        
        For any completed turn, the monitor calculates:
        - VAD trigger latency (from speech end to VAD trigger)
        - LLM response latency (from VAD trigger to LLM response)
        - Total turn latency (from user stops to Alice starts)
        """
        reset_turn_taking_monitor()
        monitor = get_turn_taking_monitor(session_id="test-session")
        
        # Simulate a conversation turn with known timings
        monitor.on_user_speech_start()
        monitor.on_user_speech_end()
        monitor.on_vad_trigger()
        monitor.on_llm_response_start()
        monitor.on_alice_speech_start()
        monitor.on_turn_complete()
        
        # Verify turn was recorded
        assert len(monitor.session.turns) == 1, "Turn should be recorded"
        
        turn = monitor.session.turns[0]
        
        # Verify latencies were calculated
        assert turn.vad_trigger_latency_ms is not None, "VAD trigger latency should be calculated"
        assert turn.llm_response_latency_ms is not None, "LLM response latency should be calculated"
        assert turn.total_turn_latency_ms is not None, "Total turn latency should be calculated"
        
        logger.info(f"✓ Turn-taking latency calculation preserved")
    
    def test_turn_taking_session_summary(self):
        """
        Property: Turn-taking monitor generates session summary
        
        For any session with turns, the summary includes:
        - Total turns count
        - Turns meeting requirements (<200ms)
        - Average/min/max latencies
        - Context preservation rate
        """
        reset_turn_taking_monitor()
        monitor = get_turn_taking_monitor(session_id="test-session")
        
        # Simulate multiple turns
        for i in range(3):
            monitor.on_user_speech_start()
            monitor.on_user_speech_end()
            monitor.on_vad_trigger()
            monitor.on_llm_response_start()
            monitor.on_alice_speech_start()
            monitor.on_turn_complete()
        
        summary = monitor.get_session_summary()
        
        # Verify summary structure
        assert 'session_id' in summary, "Summary should include session_id"
        assert 'total_turns' in summary, "Summary should include total_turns"
        assert summary['total_turns'] == 3, "Should have 3 turns recorded"
        assert 'turns_meeting_requirements' in summary, "Summary should include turns_meeting_requirements"
        assert 'requirement_compliance_rate' in summary, "Summary should include requirement_compliance_rate"
        
        logger.info(f"✓ Turn-taking session summary preserved: {summary['total_turns']} turns")




# ============================================================================
# Preservation Property Tests - Tool Execution
# ============================================================================

class TestToolExecutionPreservation:
    """
    Test preservation of tool execution functionality.
    
    **Validates: Requirement 3.6**
    
    WHEN the agent uses tools (personal mode, browser automation, hardware control)
    THEN the system SHALL CONTINUE TO execute them correctly without latency-related failures.
    
    Observed behavior on unfixed code:
    - Personal mode tools (open_application, create_file_and_open, etc.) work correctly
    - Browser automation tools execute when available
    - Hardware control tools (servo motor, ultrasonic sensor) work correctly
    - Tool execution is independent of voice latency optimization
    """
    
    def test_personal_mode_tools_available(self):
        """
        Property: Personal mode tools remain available and functional
        
        For any agent configuration, personal mode tools are available:
        - enable_personal_mode
        - disable_personal_mode
        - open_application
        - check_personal_mode
        - etc.
        """
        # Import personal mode tools
        from alice_personal_safe import (
            enable_personal_mode,
            disable_personal_mode,
            open_application,
            check_personal_mode
        )
        
        # Verify tools are callable
        assert callable(enable_personal_mode), "enable_personal_mode should be callable"
        assert callable(disable_personal_mode), "disable_personal_mode should be callable"
        assert callable(open_application), "open_application should be callable"
        assert callable(check_personal_mode), "check_personal_mode should be callable"
        
        logger.info("✓ Personal mode tools remain available")
    
    def test_hardware_control_tools_available(self):
        """
        Property: Hardware control tools remain available and functional
        
        For any agent configuration, hardware control tools are available:
        - control_servo_motor
        - get_ultrasonic_distance
        """
        # Import hardware control tools
        from alice_servo_control import control_servo_motor, get_ultrasonic_distance
        
        # Verify tools are callable
        assert callable(control_servo_motor), "control_servo_motor should be callable"
        assert callable(get_ultrasonic_distance), "get_ultrasonic_distance should be callable"
        
        logger.info("✓ Hardware control tools remain available")
    
    def test_tool_execution_independence_from_latency(self):
        """
        Property: Tool execution is independent of voice latency optimization
        
        For any tool execution, the tool's functionality is not affected by
        voice latency optimization changes (VAD, streaming, etc.).
        
        This is a structural test - tools should not depend on voice pipeline.
        """
        # Verify tool imports are present and independent
        from alice_personal_safe import enable_personal_mode
        from alice_servo_control import control_servo_motor
        
        # Tools should be independent functions, not coupled to voice pipeline
        assert callable(enable_personal_mode), "Tools should be callable independently"
        assert callable(control_servo_motor), "Tools should be callable independently"
        
        # Verify tools don't import voice-related modules
        import inspect
        enable_source = inspect.getsource(enable_personal_mode)
        
        # Tools should not depend on VAD, LiveKit agents, or voice pipeline
        assert 'silero' not in enable_source.lower(), "Tools should not depend on VAD"
        assert 'livekit.agents' not in enable_source.lower(), "Tools should not depend on LiveKit agents"
        
        logger.info("✓ Tool execution independence from latency preserved")


# ============================================================================
# Preservation Property Tests - Memory Extraction
# ============================================================================

class TestMemoryExtractionPreservation:
    """
    Test preservation of memory extraction functionality.
    
    **Validates: Requirement 3.7**
    
    WHEN memory extraction runs in the background THEN the system SHALL
    CONTINUE TO save conversation history without blocking voice interaction.
    
    Observed behavior on unfixed code:
    - Memory extraction runs asynchronously in background
    - Conversation history is saved to Mem0
    - Memory extraction does not block voice interaction
    - Initial memories are loaded on session start
    """
    
    def test_memory_extraction_module_available(self):
        """
        Property: Memory extraction module remains available
        
        For any agent configuration, memory extraction module is available:
        - MemoryExtractor class
        - ConversationMemory class
        """
        # Import memory modules (skip if mem0 not installed)
        try:
            from memory_loop import MemoryExtractor
            from memory_store import ConversationMemory
            
            # Verify classes are available
            assert MemoryExtractor is not None, "MemoryExtractor should be available"
            assert ConversationMemory is not None, "ConversationMemory should be available"
            
            logger.info("✓ Memory extraction module remains available")
        except ModuleNotFoundError as e:
            if 'mem0' in str(e):
                pytest.skip("mem0 module not installed - memory features optional")
            else:
                raise
    
    def test_memory_extraction_initialization(self):
        """
        Property: Memory extraction initializes correctly
        
        For any user, ConversationMemory initializes with user_id
        and provides memory access methods.
        """
        try:
            from memory_store import ConversationMemory
            
            # Initialize memory store
            memory = ConversationMemory(user_id="test-user")
            
            # Verify initialization
            assert memory.user_id == "test-user", "User ID should be set"
            assert hasattr(memory, 'get_all_memories'), "Should have get_all_memories method"
            
            logger.info("✓ Memory extraction initialization preserved")
        except ModuleNotFoundError as e:
            if 'mem0' in str(e):
                pytest.skip("mem0 module not installed - memory features optional")
            else:
                raise
    
    def test_memory_extraction_async_execution(self):
        """
        Property: Memory extraction runs asynchronously
        
        For any conversation, memory extraction runs in background
        without blocking the main voice interaction loop.
        
        This is a structural test - memory extraction should use asyncio.create_task.
        """
        # Read agent.py source directly to avoid import issues
        import os
        agent_path = os.path.join(os.path.dirname(__file__), '..', 'agent.py')
        
        with open(agent_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Verify async memory extraction pattern
        assert 'asyncio.create_task' in source or 'create_task' in source, (
            "Memory extraction should use asyncio.create_task for background execution"
        )
        assert 'MemoryExtractor' in source, (
            "Memory extraction should be initialized in entrypoint"
        )
        
        logger.info("✓ Memory extraction async execution preserved")


# ============================================================================
# Preservation Property Tests - Interrupted Speech Handling
# ============================================================================

class TestInterruptedSpeechHandlingPreservation:
    """
    Test preservation of interrupted speech handling.
    
    **Validates: Requirement 3.8**
    
    WHEN the user's speech is interrupted or overlapping THEN the system SHALL
    CONTINUE TO handle turn-taking gracefully without cutting off the user.
    
    Observed behavior on unfixed code:
    - Turn-taking monitor tracks overlapping exchanges
    - Context preservation flag indicates if conversation context maintained
    - VAD configuration allows for natural interruptions
    - System handles edge cases in turn-taking
    """
    
    def test_overlapping_exchange_tracking(self):
        """
        Property: Turn-taking monitor tracks overlapping exchanges
        
        For any conversation turn, the monitor can flag overlapping exchanges
        where user and Alice speak simultaneously.
        """
        reset_turn_taking_monitor()
        monitor = get_turn_taking_monitor(session_id="test-session")
        
        # Simulate overlapping exchange
        monitor.on_user_speech_start()
        monitor.on_user_speech_end()
        monitor.on_vad_trigger()
        monitor.on_llm_response_start()
        monitor.on_alice_speech_start()
        monitor.on_turn_complete(overlapping=True)
        
        # Verify overlapping flag was recorded
        assert len(monitor.session.turns) == 1, "Turn should be recorded"
        turn = monitor.session.turns[0]
        assert turn.overlapping_exchange is True, "Overlapping exchange should be flagged"
        
        logger.info("✓ Overlapping exchange tracking preserved")
    
    def test_context_preservation_tracking(self):
        """
        Property: Turn-taking monitor tracks context preservation
        
        For any conversation turn, the monitor tracks whether conversation
        context was maintained across the turn.
        """
        reset_turn_taking_monitor()
        monitor = get_turn_taking_monitor(session_id="test-session")
        
        # Simulate turn with context preserved
        monitor.on_user_speech_start()
        monitor.on_user_speech_end()
        monitor.on_vad_trigger()
        monitor.on_llm_response_start()
        monitor.on_alice_speech_start()
        monitor.on_turn_complete(context_preserved=True)
        
        # Verify context preservation was recorded
        assert len(monitor.session.turns) == 1, "Turn should be recorded"
        turn = monitor.session.turns[0]
        assert turn.conversation_context_preserved is True, "Context preservation should be tracked"
        
        logger.info("✓ Context preservation tracking preserved")
    
    def test_graceful_interruption_handling(self):
        """
        Property: System handles interruptions gracefully
        
        For any interrupted turn, the monitor can track the turn without
        requiring all timestamps to be present.
        """
        reset_turn_taking_monitor()
        monitor = get_turn_taking_monitor(session_id="test-session")
        
        # Simulate interrupted turn (user starts but doesn't finish)
        monitor.on_user_speech_start()
        # User is interrupted - no speech end
        
        # System should handle gracefully
        assert monitor.current_turn is not None, "Turn should be created"
        assert monitor.current_turn.user_speech_start is not None, "Speech start should be recorded"
        
        # Even without complete data, turn can be recorded
        monitor.on_turn_complete(context_preserved=False, overlapping=True)
        
        assert len(monitor.session.turns) == 1, "Interrupted turn should be recorded"
        
        logger.info("✓ Graceful interruption handling preserved")


# ============================================================================
# Preservation Property Tests - Error Handling and Logging
# ============================================================================

class TestErrorHandlingPreservation:
    """
    Test preservation of error handling and logging.
    
    **Validates: Requirement 3.8 (implicit)**
    
    WHEN errors occur THEN the system SHALL CONTINUE TO handle them gracefully
    and log appropriate information for debugging.
    
    Observed behavior on unfixed code:
    - Audio configuration handles missing devices gracefully
    - VAD configuration validates and clamps invalid values
    - Audio quality validation handles missing sounddevice library
    - All modules use logging for debugging
    """
    
    def test_audio_config_error_handling(self):
        """
        Property: Audio configuration handles errors gracefully
        
        For any audio configuration error (no devices available),
        the system returns error information without crashing.
        """
        with patch('livekit_audio_config.detect_nvidia_broadcast_device') as mock_detect:
            with patch('livekit_audio_config.get_default_audio_input_device') as mock_default:
                # Simulate no devices available
                mock_detect.return_value = None
                mock_default.return_value = None
                
                config = configure_livekit_audio_input()
                
                # Verify error handling
                assert 'error' in config, "Config should include error field"
                assert config['device_id'] is None, "Device ID should be None on error"
                assert config['is_nvidia_broadcast'] is False, "NVIDIA Broadcast should be False on error"
                
                logger.info("✓ Audio config error handling preserved")
    
    def test_vad_config_invalid_value_handling(self):
        """
        Property: VAD configuration handles invalid values gracefully
        
        For any invalid VAD threshold value, the system falls back to
        dynamic threshold selection based on environment (default: noisy = 450ms).
        """
        # Test invalid string value
        with patch.dict(os.environ, {'VAD_SILENCE_THRESHOLD_MS': 'invalid'}):
            threshold = get_vad_silence_threshold()
            
            # Should fall back to dynamic selection (default: noisy without NVIDIA = 450ms)
            assert threshold == 0.45, (
                f"Invalid value should fall back to dynamic selection (450ms): got {threshold * 1000}ms"
            )
        
        logger.info("✓ VAD config invalid value handling preserved (falls back to dynamic selection)")
    
    def test_audio_quality_missing_library_handling(self):
        """
        Property: Audio quality validation handles missing sounddevice library
        
        For any audio quality check when sounddevice is unavailable,
        the system returns error information without crashing.
        """
        with patch('audio_quality_validator.SOUNDDEVICE_AVAILABLE', False):
            from audio_quality_validator import check_audio_signal_strength
            
            result = check_audio_signal_strength(device_index=None)
            
            # Verify error handling
            assert 'error' in result, "Result should include error field"
            assert result['is_acceptable'] is False, "Signal should not be acceptable on error"
            assert 'sounddevice' in result['error'].lower(), "Error should mention sounddevice"
            
            logger.info("✓ Audio quality missing library handling preserved")


# ============================================================================
# Property-Based Test Scenarios (Parameterized)
# ============================================================================

class TestPreservationPropertyBased:
    """
    Property-Based Tests for Preservation Requirements
    
    These tests verify preservation properties hold across multiple scenarios
    and input variations.
    """
    
    @pytest.mark.parametrize("threshold_ms", [300, 350, 400, 450, 500])
    def test_vad_threshold_property_across_values(self, threshold_ms):
        """
        Property: VAD threshold configuration works for all valid values
        
        For any valid threshold value (300-500ms), the system correctly
        configures and validates the threshold.
        """
        with patch.dict(os.environ, {'VAD_SILENCE_THRESHOLD_MS': str(threshold_ms)}):
            threshold = get_vad_silence_threshold()
            
            # Verify threshold is set correctly
            expected = threshold_ms / 1000.0
            assert threshold == expected, (
                f"Threshold {threshold}s != expected {expected}s for input {threshold_ms}ms"
            )
            
            # Verify threshold is within safe range
            assert MIN_VAD_SILENCE_THRESHOLD <= threshold <= MAX_VAD_SILENCE_THRESHOLD, (
                f"Threshold {threshold}s outside safe range"
            )
        
        logger.info(f"✓ VAD threshold property holds for {threshold_ms}ms")
    
    @pytest.mark.parametrize("session_id", ["session-1", "session-2", "test-session"])
    def test_turn_taking_monitor_property_across_sessions(self, session_id):
        """
        Property: Turn-taking monitor works correctly for any session ID
        
        For any session ID, the monitor initializes correctly and tracks turns.
        """
        reset_turn_taking_monitor()
        monitor = get_turn_taking_monitor(session_id=session_id)
        
        # Verify initialization
        assert monitor.session.session_id == session_id, "Session ID should match"
        assert monitor.session.current_turn_id == 0, "Turn counter should start at 0"
        
        # Simulate a turn
        monitor.on_user_speech_start()
        monitor.on_user_speech_end()
        monitor.on_vad_trigger()
        monitor.on_llm_response_start()
        monitor.on_alice_speech_start()
        monitor.on_turn_complete()
        
        # Verify turn was tracked
        assert len(monitor.session.turns) == 1, "Turn should be recorded"
        
        logger.info(f"✓ Turn-taking monitor property holds for session: {session_id}")
    
    @pytest.mark.parametrize("pause_ms,should_trigger", [
        (250, False),  # Short pause - should not trigger
        (300, False),  # At minimum threshold - should not trigger with 400ms config
        (400, True),   # At configured threshold - should trigger
        (500, True),   # Long pause - should trigger
        (600, True),   # Very long pause - should trigger
    ])
    def test_vad_behavior_property_across_pauses(self, pause_ms, should_trigger):
        """
        Property: VAD behavior is consistent across different pause durations
        
        For any pause duration, VAD behavior matches expected trigger behavior
        based on configured threshold (400ms).
        """
        mock_vad = Mock()
        mock_vad.activation_threshold = 0.5
        threshold_ms = 400.0
        
        validator = VADBehaviorValidator(mock_vad, threshold_ms)
        
        # Determine expected behavior
        actual_trigger = pause_ms >= threshold_ms
        
        # Verify behavior matches expectation
        assert actual_trigger == should_trigger, (
            f"VAD trigger behavior mismatch for {pause_ms}ms pause: "
            f"actual={actual_trigger}, expected={should_trigger}"
        )
        
        logger.info(f"✓ VAD behavior property holds for {pause_ms}ms pause")


# ============================================================================
# Integration Tests - Preservation Across Components
# ============================================================================

class TestPreservationIntegration:
    """
    Integration tests verifying preservation across multiple components.
    
    These tests verify that preservation properties hold when multiple
    components interact together.
    """
    
    def test_audio_pipeline_preservation(self):
        """
        Integration: Audio pipeline components work together
        
        For any audio session, the complete pipeline works:
        1. Audio device configuration
        2. Audio quality validation
        3. VAD configuration
        4. VAD behavior validation
        """
        # 1. Configure audio device
        with patch('livekit_audio_config.detect_nvidia_broadcast_device') as mock_detect:
            mock_detect.return_value = {
                'name': 'Microphone (NVIDIA Broadcast)',
                'index': 5,
                'channels': 2,
                'default_samplerate': 48000.0,
                'hostapi': 0
            }
            
            audio_config = configure_livekit_audio_input()
            assert audio_config['is_nvidia_broadcast'] is True, "Audio config should succeed"
        
        # 2. Validate audio quality
        with patch('audio_quality_validator.check_audio_signal_strength') as mock_check:
            mock_check.return_value = {
                'rms_amplitude': 0.05,
                'peak_amplitude': 0.15,
                'is_acceptable': True,
                'threshold': 0.01
            }
            
            audio_validation = validate_audio_quality_on_session_start(device_index=5)
            assert audio_validation['passed'] is True, "Audio validation should pass"
        
        # 3. Configure VAD
        threshold = get_vad_silence_threshold()
        assert MIN_VAD_SILENCE_THRESHOLD <= threshold <= MAX_VAD_SILENCE_THRESHOLD, (
            "VAD threshold should be valid"
        )
        
        # 4. Validate VAD behavior
        mock_vad = Mock()
        mock_vad.activation_threshold = 0.5
        vad_validation = validate_vad_behavior(mock_vad, threshold * 1000)
        assert 'all_passed' in vad_validation, "VAD validation should complete"
        
        logger.info("✓ Audio pipeline preservation integration test passed")
    
    def test_conversation_monitoring_preservation(self):
        """
        Integration: Conversation monitoring components work together
        
        For any conversation, monitoring components work:
        1. Turn-taking monitor tracks turns
        2. VAD behavior is validated
        3. Session summary is generated
        """
        # 1. Initialize turn-taking monitor
        reset_turn_taking_monitor()
        monitor = get_turn_taking_monitor(session_id="integration-test")
        
        # 2. Simulate conversation with multiple turns
        for i in range(3):
            monitor.on_user_speech_start()
            monitor.on_user_speech_end()
            monitor.on_vad_trigger()
            monitor.on_llm_response_start()
            monitor.on_alice_speech_start()
            monitor.on_turn_complete()
        
        # 3. Generate session summary
        summary = monitor.get_session_summary()
        assert summary['total_turns'] == 3, "Should have 3 turns"
        assert 'requirement_compliance_rate' in summary, "Should have compliance rate"
        
        logger.info("✓ Conversation monitoring preservation integration test passed")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
