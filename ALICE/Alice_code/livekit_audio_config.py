"""
LiveKit audio configuration for NVIDIA Broadcast integration.

This module provides functions to configure LiveKit to use NVIDIA Broadcast
as the default audio input device with fallback to system default.
"""

import logging
from typing import Optional, Dict, Any
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
