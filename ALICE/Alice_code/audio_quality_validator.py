"""
Audio quality validation for LiveKit session initialization.

This module provides functions to validate audio input quality on session start,
including signal strength checks and quality reporting.
"""

import logging
from typing import Optional, Dict, Any
import time

logger = logging.getLogger(__name__)

# Try to import sounddevice for audio quality checks
try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    logger.warning("sounddevice not available - audio quality validation limited")


# Audio quality thresholds
SIGNAL_STRENGTH_THRESHOLD = 0.01  # Minimum RMS amplitude for acceptable signal
SAMPLE_DURATION = 1.0  # Duration in seconds to sample audio
SAMPLE_RATE = 48000  # Sample rate for audio capture


def check_audio_signal_strength(device_index: Optional[int] = None, duration: float = SAMPLE_DURATION) -> Dict[str, Any]:
    """
    Check audio signal strength from the specified device.
    
    Args:
        device_index: Device index to check (None for default)
        duration: Duration in seconds to sample audio
    
    Returns:
        Dictionary with signal strength information:
        - rms_amplitude: Root mean square amplitude of the signal
        - peak_amplitude: Peak amplitude of the signal
        - is_acceptable: Boolean indicating if signal is above threshold
        - threshold: The threshold used for validation
        - error: Error message if check failed
    
    Requirements: 1.6
    """
    if not SOUNDDEVICE_AVAILABLE:
        logger.error("Cannot check audio signal strength - sounddevice not available")
        return {
            'rms_amplitude': 0.0,
            'peak_amplitude': 0.0,
            'is_acceptable': False,
            'threshold': SIGNAL_STRENGTH_THRESHOLD,
            'error': 'sounddevice library not available'
        }
    
    try:
        logger.info(f"Checking audio signal strength (device: {device_index}, duration: {duration}s)...")
        
        # Record audio sample
        recording = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            device=device_index,
            dtype='float32'
        )
        sd.wait()  # Wait for recording to complete
        
        # Calculate signal metrics
        rms_amplitude = float(np.sqrt(np.mean(recording ** 2)))
        peak_amplitude = float(np.max(np.abs(recording)))
        
        is_acceptable = rms_amplitude >= SIGNAL_STRENGTH_THRESHOLD
        
        logger.info(f"Audio signal check complete - RMS: {rms_amplitude:.4f}, Peak: {peak_amplitude:.4f}, Acceptable: {is_acceptable}")
        
        return {
            'rms_amplitude': rms_amplitude,
            'peak_amplitude': peak_amplitude,
            'is_acceptable': is_acceptable,
            'threshold': SIGNAL_STRENGTH_THRESHOLD
        }
        
    except Exception as e:
        logger.error(f"Failed to check audio signal strength: {e}")
        return {
            'rms_amplitude': 0.0,
            'peak_amplitude': 0.0,
            'is_acceptable': False,
            'threshold': SIGNAL_STRENGTH_THRESHOLD,
            'error': str(e)
        }


def validate_audio_quality_on_session_start(device_index: Optional[int] = None) -> Dict[str, Any]:
    """
    Validate audio quality during session initialization.
    
    Performs signal strength check and returns validation results.
    
    Args:
        device_index: Device index to validate (None for default)
    
    Returns:
        Dictionary with validation results:
        - passed: Boolean indicating if validation passed
        - signal_strength: Signal strength check results
        - warnings: List of warning messages
        - timestamp: Validation timestamp
    
    Requirements: 1.6, 6.6
    """
    logger.info("=" * 60)
    logger.info("Audio Quality Validation - Session Start")
    logger.info("=" * 60)
    
    timestamp = time.time()
    warnings = []
    
    # Check signal strength
    signal_check = check_audio_signal_strength(device_index)
    
    # Evaluate results
    if signal_check.get('error'):
        warnings.append(f"Signal strength check failed: {signal_check['error']}")
        passed = False
    elif not signal_check['is_acceptable']:
        warnings.append(f"Audio signal too weak (RMS: {signal_check['rms_amplitude']:.4f}, threshold: {signal_check['threshold']:.4f})")
        passed = False
    else:
        passed = True
        logger.info(f"✅ Audio quality validation passed (RMS: {signal_check['rms_amplitude']:.4f})")
    
    # Log warnings
    for warning in warnings:
        logger.warning(f"⚠️  {warning}")
    
    logger.info("=" * 60)
    
    return {
        'passed': passed,
        'signal_strength': signal_check,
        'warnings': warnings,
        'timestamp': timestamp
    }


def get_audio_quality_voice_report(validation_result: Dict[str, Any]) -> str:
    """
    Generate voice report for audio quality validation results.
    
    Args:
        validation_result: Validation result from validate_audio_quality_on_session_start()
    
    Returns:
        String describing audio quality status for voice output
    
    Requirements: 1.6, 6.6
    """
    if validation_result['passed']:
        return "Audio quality check passed. Your microphone is working properly."
    
    warnings = validation_result.get('warnings', [])
    
    if not warnings:
        return "Audio quality check completed with unknown status."
    
    # Report the first warning (most critical)
    first_warning = warnings[0]
    
    if 'too weak' in first_warning.lower():
        return "Warning: Your microphone signal is too weak. Please check your microphone connection and volume settings."
    elif 'failed' in first_warning.lower():
        return "Warning: Unable to validate audio quality. Please ensure your microphone is connected and working."
    else:
        return f"Warning: Audio quality issue detected. {first_warning}"


def log_audio_quality_validation(validation_result: Dict[str, Any]) -> None:
    """
    Log detailed audio quality validation results.
    
    Args:
        validation_result: Validation result from validate_audio_quality_on_session_start()
    
    Requirements: 1.6, 6.6
    """
    logger.info("Audio Quality Validation Results:")
    logger.info(f"  Passed: {validation_result['passed']}")
    logger.info(f"  Timestamp: {validation_result['timestamp']}")
    
    signal = validation_result.get('signal_strength', {})
    logger.info(f"  Signal Strength:")
    logger.info(f"    RMS Amplitude: {signal.get('rms_amplitude', 0.0):.4f}")
    logger.info(f"    Peak Amplitude: {signal.get('peak_amplitude', 0.0):.4f}")
    logger.info(f"    Threshold: {signal.get('threshold', 0.0):.4f}")
    logger.info(f"    Acceptable: {signal.get('is_acceptable', False)}")
    
    if signal.get('error'):
        logger.error(f"    Error: {signal['error']}")
    
    warnings = validation_result.get('warnings', [])
    if warnings:
        logger.warning(f"  Warnings ({len(warnings)}):")
        for i, warning in enumerate(warnings, 1):
            logger.warning(f"    {i}. {warning}")
