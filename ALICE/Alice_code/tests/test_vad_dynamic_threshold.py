"""
Test suite for dynamic VAD threshold optimization (Task 3.6)

This module tests the environment-aware VAD threshold selection that
optimizes latency in quiet environments while maintaining safety in noisy environments.

Requirements: 1.1, 1.5, 2.1, 2.5, 3.1
"""

import pytest
import os
from unittest.mock import patch
import logging

# Import the functions to test
from vad_config import (
    get_vad_silence_threshold,
    log_vad_configuration,
    MIN_VAD_SILENCE_THRESHOLD,
    MAX_VAD_SILENCE_THRESHOLD
)

logger = logging.getLogger(__name__)


class TestDynamicVADThreshold:
    """Test dynamic VAD threshold optimization based on environment."""
    
    def test_quiet_environment_with_nvidia_broadcast(self):
        """
        Test: Quiet environment + NVIDIA Broadcast = 300ms (optimal latency)
        
        **Validates: Requirements 1.1, 1.5, 2.1, 2.5**
        """
        threshold = get_vad_silence_threshold(
            environment="quiet",
            nvidia_broadcast_available=True
        )
        
        assert threshold == 0.3, (
            f"Expected 300ms threshold for quiet + NVIDIA Broadcast, got {threshold * 1000}ms"
        )
        logger.info("✓ Quiet + NVIDIA Broadcast: 300ms threshold (optimal)")
    
    def test_quiet_environment_without_nvidia_broadcast(self):
        """
        Test: Quiet environment without NVIDIA Broadcast = 350ms (balanced)
        
        **Validates: Requirements 1.1, 1.5, 2.1, 2.5**
        """
        threshold = get_vad_silence_threshold(
            environment="quiet",
            nvidia_broadcast_available=False
        )
        
        assert threshold == 0.35, (
            f"Expected 350ms threshold for quiet without NVIDIA Broadcast, got {threshold * 1000}ms"
        )
        logger.info("✓ Quiet without NVIDIA Broadcast: 350ms threshold (balanced)")
    
    def test_noisy_environment_with_nvidia_broadcast(self):
        """
        Test: Noisy environment + NVIDIA Broadcast = 400ms (conservative)
        
        **Validates: Requirements 3.1**
        """
        threshold = get_vad_silence_threshold(
            environment="noisy",
            nvidia_broadcast_available=True
        )
        
        assert threshold == 0.4, (
            f"Expected 400ms threshold for noisy + NVIDIA Broadcast, got {threshold * 1000}ms"
        )
        logger.info("✓ Noisy + NVIDIA Broadcast: 400ms threshold (conservative)")
    
    def test_noisy_environment_without_nvidia_broadcast(self):
        """
        Test: Noisy environment without NVIDIA Broadcast = 450ms (maximum safety)
        
        **Validates: Requirements 3.1**
        """
        threshold = get_vad_silence_threshold(
            environment="noisy",
            nvidia_broadcast_available=False
        )
        
        assert threshold == 0.45, (
            f"Expected 450ms threshold for noisy without NVIDIA Broadcast, got {threshold * 1000}ms"
        )
        logger.info("✓ Noisy without NVIDIA Broadcast: 450ms threshold (maximum safety)")
    
    def test_default_parameters(self):
        """
        Test: Default parameters (noisy, no NVIDIA Broadcast) = 450ms
        
        **Validates: Requirements 3.1**
        """
        threshold = get_vad_silence_threshold()
        
        assert threshold == 0.45, (
            f"Expected 450ms threshold for default parameters, got {threshold * 1000}ms"
        )
        logger.info("✓ Default parameters: 450ms threshold (safe default)")
    
    def test_environment_override_with_env_variable(self):
        """
        Test: Environment variable override takes precedence
        
        **Validates: Requirements 2.5**
        """
        with patch.dict(os.environ, {'VAD_SILENCE_THRESHOLD_MS': '320'}):
            threshold = get_vad_silence_threshold(
                environment="quiet",
                nvidia_broadcast_available=True
            )
            
            assert threshold == 0.32, (
                f"Expected 320ms from env override, got {threshold * 1000}ms"
            )
        
        logger.info("✓ Environment variable override works correctly")
    
    def test_env_override_clamping_minimum(self):
        """
        Test: Environment variable override respects minimum threshold
        
        **Validates: Requirements 2.5**
        """
        with patch.dict(os.environ, {'VAD_SILENCE_THRESHOLD_MS': '200'}):
            threshold = get_vad_silence_threshold(
                environment="quiet",
                nvidia_broadcast_available=True
            )
            
            assert threshold == MIN_VAD_SILENCE_THRESHOLD, (
                f"Expected {MIN_VAD_SILENCE_THRESHOLD * 1000}ms (clamped), got {threshold * 1000}ms"
            )
        
        logger.info("✓ Environment override clamping (minimum) works correctly")
    
    def test_env_override_clamping_maximum(self):
        """
        Test: Environment variable override respects maximum threshold
        
        **Validates: Requirements 2.5**
        """
        with patch.dict(os.environ, {'VAD_SILENCE_THRESHOLD_MS': '600'}):
            threshold = get_vad_silence_threshold(
                environment="noisy",
                nvidia_broadcast_available=False
            )
            
            assert threshold == MAX_VAD_SILENCE_THRESHOLD, (
                f"Expected {MAX_VAD_SILENCE_THRESHOLD * 1000}ms (clamped), got {threshold * 1000}ms"
            )
        
        logger.info("✓ Environment override clamping (maximum) works correctly")
    
    def test_invalid_env_override_falls_back_to_dynamic(self):
        """
        Test: Invalid environment variable falls back to dynamic selection
        
        **Validates: Requirements 2.5**
        """
        with patch.dict(os.environ, {'VAD_SILENCE_THRESHOLD_MS': 'invalid'}):
            threshold = get_vad_silence_threshold(
                environment="quiet",
                nvidia_broadcast_available=True
            )
            
            # Should fall back to dynamic selection (300ms for quiet + NVIDIA)
            assert threshold == 0.3, (
                f"Expected 300ms (dynamic fallback), got {threshold * 1000}ms"
            )
        
        logger.info("✓ Invalid env override falls back to dynamic selection")
    
    @pytest.mark.parametrize("environment,nvidia,expected_ms", [
        ("quiet", True, 300),
        ("quiet", False, 350),
        ("noisy", True, 400),
        ("noisy", False, 450),
    ])
    def test_all_environment_combinations(self, environment, nvidia, expected_ms):
        """
        Property: All environment combinations return correct thresholds
        
        **Validates: Requirements 1.1, 1.5, 2.1, 2.5, 3.1**
        """
        threshold = get_vad_silence_threshold(
            environment=environment,
            nvidia_broadcast_available=nvidia
        )
        
        expected_s = expected_ms / 1000.0
        assert threshold == expected_s, (
            f"Environment={environment}, NVIDIA={nvidia}: "
            f"Expected {expected_ms}ms, got {threshold * 1000}ms"
        )
        
        logger.info(
            f"✓ {environment.capitalize()} + NVIDIA={nvidia}: {expected_ms}ms threshold"
        )
    
    def test_latency_improvement_in_quiet_environment(self):
        """
        Test: Quiet environment provides 100-150ms latency improvement
        
        **Validates: Requirements 2.1, 2.5**
        
        Bug Condition: VAD threshold > 400ms in quiet environments
        Expected Behavior: Dynamic threshold reduces trigger time by 100-150ms
        """
        # Old behavior: 400ms default
        old_threshold_ms = 400
        
        # New behavior: 300ms in quiet + NVIDIA Broadcast
        new_threshold = get_vad_silence_threshold(
            environment="quiet",
            nvidia_broadcast_available=True
        )
        new_threshold_ms = new_threshold * 1000
        
        # Calculate improvement
        improvement_ms = old_threshold_ms - new_threshold_ms
        
        assert improvement_ms >= 100, (
            f"Expected at least 100ms improvement, got {improvement_ms}ms"
        )
        assert improvement_ms <= 150, (
            f"Expected at most 150ms improvement, got {improvement_ms}ms"
        )
        
        logger.info(f"✓ Latency improvement in quiet environment: {improvement_ms}ms")
    
    def test_noisy_environment_preservation(self):
        """
        Test: Noisy environment handling continues to work correctly
        
        **Validates: Requirement 3.1 (Preservation)**
        
        Preservation: Noisy environment handling must continue to work correctly
        (prevent false triggers)
        """
        # Noisy environment should use conservative thresholds (400-450ms)
        threshold_with_nvidia = get_vad_silence_threshold(
            environment="noisy",
            nvidia_broadcast_available=True
        )
        threshold_without_nvidia = get_vad_silence_threshold(
            environment="noisy",
            nvidia_broadcast_available=False
        )
        
        # Both should be >= 400ms to prevent false triggers
        assert threshold_with_nvidia >= 0.4, (
            f"Noisy + NVIDIA threshold {threshold_with_nvidia * 1000}ms too low (< 400ms)"
        )
        assert threshold_without_nvidia >= 0.4, (
            f"Noisy without NVIDIA threshold {threshold_without_nvidia * 1000}ms too low (< 400ms)"
        )
        
        logger.info("✓ Noisy environment handling preserved (prevents false triggers)")


class TestVADConfigurationLogging:
    """Test VAD configuration logging with environment information."""
    
    def test_log_vad_configuration_with_environment(self, caplog):
        """
        Test: VAD configuration logging includes environment details
        
        **Validates: Requirements 1.1, 1.5, 2.1, 2.5**
        """
        with caplog.at_level(logging.INFO):
            log_vad_configuration(
                silence_threshold=0.3,
                environment="quiet",
                nvidia_broadcast_available=True
            )
        
        # Check that log contains expected information
        log_text = caplog.text
        assert "Voice Activity Detection (VAD) Configuration" in log_text
        assert "300ms" in log_text
        assert "QUIET" in log_text
        assert "Active" in log_text
        
        logger.info("✓ VAD configuration logging includes environment details")
    
    def test_log_vad_configuration_default_parameters(self, caplog):
        """
        Test: VAD configuration logging works with default parameters
        
        **Validates: Requirements 1.1, 1.5, 2.1, 2.5**
        """
        with caplog.at_level(logging.INFO):
            log_vad_configuration(silence_threshold=0.4)
        
        # Check that log contains expected information
        log_text = caplog.text
        assert "Voice Activity Detection (VAD) Configuration" in log_text
        assert "400ms" in log_text
        assert "UNKNOWN" in log_text
        assert "Not Available" in log_text
        
        logger.info("✓ VAD configuration logging works with default parameters")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
