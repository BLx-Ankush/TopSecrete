"""
LiveKit audio configuration for NVIDIA Broadcast integration.

This module provides functions to configure LiveKit to use NVIDIA Broadcast
as the default audio input device with fallback to system default.

Includes audio environment detection for dynamic VAD threshold optimization.
"""

import logging
import numpy as np
from typing import Optional, Dict, Any, Tuple
from audio_utils import (
    detect_nvidia_broadcast_device,
    validate_nvidia_broadcast_available,
    get_default_audio_input_device
)

logger = logging.getLogger(__name__)


def select_audio_input_device() -> Optional[Dict[str, Any]]:
    """
    Select the best available audio input device.
    
    Priority:
    1. NVIDIA Broadcast virtual microphone (if available)
    2. System default microphone (fallback)
    
    Returns:
        Dictionary with selected device information, or None if no device available.
        Device info includes: name, index, channels, default_samplerate, hostapi
    
    Requirements: 1.1, 1.3
    """
    # Try NVIDIA Broadcast first
    nvidia_device = detect_nvidia_broadcast_device()
    
    if nvidia_device is not None:
        logger.info(f"✅ Selected NVIDIA Broadcast as audio input: {nvidia_device['name']}")
        return nvidia_device
    
    # Fallback to default microphone
    logger.warning("⚠️  NVIDIA Broadcast not available, falling back to default microphone")
    default_device = get_default_audio_input_device()
    
    if default_device is not None:
        logger.info(f"✅ Selected default microphone as audio input: {default_device['name']}")
        return default_device
    
    logger.error("❌ No audio input device available")
    return None


def get_livekit_audio_device_id(device_info: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Get the LiveKit-compatible device ID from device information.
    
    Args:
        device_info: Device information dictionary from audio_utils
    
    Returns:
        Device ID string for LiveKit configuration, or None if device_info is None
    
    Requirements: 1.2
    """
    if device_info is None:
        return None
    
    # LiveKit uses device index as the device ID on Windows
    device_id = str(device_info['index'])
    logger.debug(f"LiveKit device ID for {device_info['name']}: {device_id}")
    return device_id


def configure_livekit_audio_input() -> Dict[str, Any]:
    """
    Configure LiveKit audio input with NVIDIA Broadcast or fallback.
    
    Returns:
        Dictionary with configuration information:
        - device_id: LiveKit device ID (or None for system default)
        - device_name: Human-readable device name
        - is_nvidia_broadcast: Boolean indicating if NVIDIA Broadcast is being used
        - fallback_used: Boolean indicating if fallback was used
    
    Requirements: 1.1, 1.2, 1.3, 6.1
    """
    # Check if NVIDIA Broadcast is available
    nvidia_available = validate_nvidia_broadcast_available()
    
    # Select the best device
    selected_device = select_audio_input_device()
    
    if selected_device is None:
        logger.error("❌ Failed to configure audio input - no device available")
        return {
            'device_id': None,
            'device_name': 'No device available',
            'is_nvidia_broadcast': False,
            'fallback_used': False,
            'error': 'No audio input device available'
        }
    
    # Determine if we're using NVIDIA Broadcast
    is_nvidia = 'nvidia broadcast' in selected_device['name'].lower() or 'nvidia rtx voice' in selected_device['name'].lower()
    fallback_used = nvidia_available and not is_nvidia
    
    # Get LiveKit device ID
    device_id = get_livekit_audio_device_id(selected_device)
    
    config = {
        'device_id': device_id,
        'device_name': selected_device['name'],
        'is_nvidia_broadcast': is_nvidia,
        'fallback_used': fallback_used
    }
    
    # Log configuration
    if is_nvidia:
        logger.info(f"✅ LiveKit configured with NVIDIA Broadcast: {selected_device['name']} (device_id: {device_id})")
    elif fallback_used:
        logger.warning(f"⚠️  LiveKit configured with fallback device: {selected_device['name']} (device_id: {device_id})")
    else:
        logger.info(f"✅ LiveKit configured with default device: {selected_device['name']} (device_id: {device_id})")
    
    return config


def log_audio_device_selection(config: Dict[str, Any]) -> None:
    """
    Log audio device selection details for debugging.
    
    Args:
        config: Configuration dictionary from configure_livekit_audio_input()
    
    Requirements: 1.3, 6.1
    """
    logger.info("=" * 60)
    logger.info("LiveKit Audio Input Configuration")
    logger.info("=" * 60)
    logger.info(f"Device Name: {config.get('device_name', 'Unknown')}")
    logger.info(f"Device ID: {config.get('device_id', 'None')}")
    logger.info(f"NVIDIA Broadcast: {'Yes' if config.get('is_nvidia_broadcast') else 'No'}")
    logger.info(f"Fallback Used: {'Yes' if config.get('fallback_used') else 'No'}")
    
    if config.get('error'):
        logger.error(f"Error: {config['error']}")
    
    logger.info("=" * 60)


def get_audio_device_info_for_voice_report() -> str:
    """
    Get audio device information formatted for voice report to user.
    
    Returns:
        String describing the audio device status for voice output
    
    Requirements: 1.6, 6.6
    """
    config = configure_livekit_audio_input()
    
    if config.get('error'):
        return "Warning: No audio input device detected. Please check your microphone connection."
    
    if config.get('is_nvidia_broadcast'):
        return "Audio input configured with NVIDIA Broadcast noise cancellation."
    elif config.get('fallback_used'):
        return "Warning: NVIDIA Broadcast not available. Using default microphone without advanced noise cancellation."
    else:
        return "Audio input configured with default microphone."


def detect_audio_environment(device_index: Optional[int] = None, duration: float = 2.0) -> Dict[str, Any]:
    """
    Detect audio environment by analyzing ambient noise level.
    
    Samples audio from the input device and calculates the noise floor
    to classify the environment as "quiet" or "noisy".
    
    Args:
        device_index: Audio device index to sample from (None for default)
        duration: Duration in seconds to sample audio (default: 2.0s)
    
    Returns:
        Dictionary with environment classification:
        - environment: "quiet" or "noisy"
        - noise_floor_db: Measured noise floor in dB
        - rms_level: RMS level of ambient noise
        - sample_duration: Actual sampling duration
        - classification_threshold: Threshold used for classification
    
    Requirements: 1.1, 1.5, 2.1, 2.5, 3.1, 3.2
    """
    logger.info("=" * 60)
    logger.info("Detecting Audio Environment")
    logger.info("=" * 60)
    
    try:
        import sounddevice as sd
        
        # Sample audio from device
        logger.info(f"Sampling audio for {duration}s to detect environment...")
        sample_rate = 16000  # 16kHz is sufficient for noise detection
        
        # Record audio
        audio_samples = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            device=device_index,
            dtype='float32'
        )
        sd.wait()  # Wait for recording to complete
        
        # Calculate RMS (Root Mean Square) level
        rms_level = np.sqrt(np.mean(audio_samples ** 2))
        
        # Convert to dB (with reference to prevent log(0))
        noise_floor_db = 20 * np.log10(rms_level + 1e-10)
        
        # Classification threshold (empirically determined)
        # Quiet: < -40 dB
        # Noisy: >= -40 dB
        QUIET_THRESHOLD_DB = -40.0
        
        environment = "quiet" if noise_floor_db < QUIET_THRESHOLD_DB else "noisy"
        
        logger.info(f"Environment Detection Results:")
        logger.info(f"  - Noise Floor: {noise_floor_db:.1f} dB")
        logger.info(f"  - RMS Level: {rms_level:.6f}")
        logger.info(f"  - Classification: {environment.upper()}")
        logger.info(f"  - Threshold: {QUIET_THRESHOLD_DB} dB")
        logger.info("=" * 60)
        
        return {
            'environment': environment,
            'noise_floor_db': noise_floor_db,
            'rms_level': float(rms_level),
            'sample_duration': duration,
            'classification_threshold': QUIET_THRESHOLD_DB,
            'success': True
        }
        
    except ImportError:
        logger.warning("⚠️  sounddevice not available, cannot detect audio environment")
        logger.warning("Defaulting to 'noisy' environment (conservative VAD threshold)")
        return {
            'environment': 'noisy',
            'noise_floor_db': None,
            'rms_level': None,
            'sample_duration': 0,
            'classification_threshold': None,
            'success': False,
            'error': 'sounddevice not available'
        }
    
    except Exception as e:
        logger.error(f"❌ Error detecting audio environment: {e}")
        logger.warning("Defaulting to 'noisy' environment (conservative VAD threshold)")
        return {
            'environment': 'noisy',
            'noise_floor_db': None,
            'rms_level': None,
            'sample_duration': 0,
            'classification_threshold': None,
            'success': False,
            'error': str(e)
        }


def configure_livekit_audio_input_with_environment() -> Dict[str, Any]:
    """
    Configure LiveKit audio input with NVIDIA Broadcast detection and environment classification.
    
    This enhanced version includes audio environment detection to enable
    dynamic VAD threshold optimization.
    
    Returns:
        Dictionary with configuration information:
        - device_id: LiveKit device ID (or None for system default)
        - device_name: Human-readable device name
        - is_nvidia_broadcast: Boolean indicating if NVIDIA Broadcast is being used
        - fallback_used: Boolean indicating if fallback was used
        - environment: "quiet" or "noisy" classification
        - noise_floor_db: Measured noise floor in dB
        - environment_detection_success: Boolean indicating if detection succeeded
    
    Requirements: 1.1, 1.2, 1.3, 1.5, 2.1, 2.5, 3.1, 3.2, 6.1
    """
    # Get basic audio configuration
    config = configure_livekit_audio_input()
    
    # Detect audio environment
    device_index = int(config['device_id']) if config.get('device_id') else None
    environment_info = detect_audio_environment(device_index=device_index, duration=2.0)
    
    # Merge environment info into config
    config.update({
        'environment': environment_info['environment'],
        'noise_floor_db': environment_info.get('noise_floor_db'),
        'rms_level': environment_info.get('rms_level'),
        'environment_detection_success': environment_info['success']
    })
    
    # Log combined configuration
    logger.info("=" * 60)
    logger.info("Complete Audio Configuration")
    logger.info("=" * 60)
    logger.info(f"Device: {config.get('device_name', 'Unknown')}")
    logger.info(f"NVIDIA Broadcast: {'Yes' if config.get('is_nvidia_broadcast') else 'No'}")
    logger.info(f"Environment: {config['environment'].upper()}")
    if config.get('noise_floor_db') is not None:
        logger.info(f"Noise Floor: {config['noise_floor_db']:.1f} dB")
    logger.info("=" * 60)
    
    return config


def get_environment_classification_for_vad(config: Dict[str, Any]) -> Tuple[str, bool]:
    """
    Get environment classification for VAD threshold optimization.
    
    Args:
        config: Configuration dictionary from configure_livekit_audio_input_with_environment()
    
    Returns:
        Tuple of (environment, nvidia_broadcast_available)
        - environment: "quiet" or "noisy"
        - nvidia_broadcast_available: Boolean indicating if NVIDIA Broadcast is active
    
    Requirements: 1.1, 1.5, 2.1, 2.5
    """
    environment = config.get('environment', 'noisy')
    nvidia_available = config.get('is_nvidia_broadcast', False)
    
    logger.debug(f"VAD environment classification: {environment}, NVIDIA Broadcast: {nvidia_available}")
    
    return environment, nvidia_available
