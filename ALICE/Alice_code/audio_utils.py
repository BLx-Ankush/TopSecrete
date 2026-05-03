"""
Audio device detection and validation utilities for NVIDIA Broadcast integration.

This module provides functions to:
- Enumerate Windows audio input devices
- Detect NVIDIA Broadcast virtual microphone
- Validate audio device availability
"""

import logging
import platform
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Try to import sounddevice for audio device enumeration
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    logger.warning("sounddevice not available - audio device detection limited")


def enumerate_audio_input_devices() -> List[Dict[str, Any]]:
    """
    Enumerate all available Windows audio input devices.
    
    Returns:
        List of dictionaries containing device information:
        - name: Device name
        - index: Device index
        - channels: Number of input channels
        - default_samplerate: Default sample rate
        - hostapi: Host API index
    
    Requirements: 1.1, 1.2
    """
    if not SOUNDDEVICE_AVAILABLE:
        logger.error("sounddevice library not available - cannot enumerate audio devices")
        return []
    
    if platform.system() != "Windows":
        logger.warning(f"Audio device enumeration is designed for Windows, current OS: {platform.system()}")
    
    try:
        devices = sd.query_devices()
        input_devices = []
        
        for idx, device in enumerate(devices):
            # Only include devices with input channels
            if device.get('max_input_channels', 0) > 0:
                input_devices.append({
                    'name': device['name'],
                    'index': idx,
                    'channels': device['max_input_channels'],
                    'default_samplerate': device['default_samplerate'],
                    'hostapi': device['hostapi']
                })
                logger.debug(f"Found input device: {device['name']} (index: {idx})")
        
        logger.info(f"Enumerated {len(input_devices)} audio input devices")
        return input_devices
        
    except Exception as e:
        logger.error(f"Failed to enumerate audio devices: {e}")
        return []


def detect_nvidia_broadcast_device() -> Optional[Dict[str, Any]]:
    """
    Detect the NVIDIA Broadcast virtual microphone device.
    
    Searches for devices with "NVIDIA Broadcast" in the name.
    
    Returns:
        Dictionary with device information if found, None otherwise.
        Device info includes: name, index, channels, default_samplerate, hostapi
    
    Requirements: 1.1, 1.2
    """
    input_devices = enumerate_audio_input_devices()
    
    # Search for NVIDIA Broadcast device
    for device in input_devices:
        device_name = device['name'].lower()
        if 'nvidia broadcast' in device_name or 'nvidia rtx voice' in device_name:
            logger.info(f"✅ NVIDIA Broadcast device detected: {device['name']} (index: {device['index']})")
            return device
    
    logger.warning("⚠️  NVIDIA Broadcast virtual microphone not found")
    return None


def validate_nvidia_broadcast_available() -> bool:
    """
    Validate that NVIDIA Broadcast virtual microphone is available.
    
    Returns:
        True if NVIDIA Broadcast device is detected and available, False otherwise.
    
    Requirements: 1.2, 1.6
    """
    if not SOUNDDEVICE_AVAILABLE:
        logger.error("Cannot validate NVIDIA Broadcast - sounddevice library not available")
        return False
    
    nvidia_device = detect_nvidia_broadcast_device()
    
    if nvidia_device is None:
        logger.warning("NVIDIA Broadcast validation failed - device not found")
        return False
    
    # Additional validation: check if device has input channels
    if nvidia_device.get('channels', 0) <= 0:
        logger.error(f"NVIDIA Broadcast device found but has no input channels: {nvidia_device['name']}")
        return False
    
    logger.info(f"✅ NVIDIA Broadcast validated successfully: {nvidia_device['name']}")
    return True


def get_default_audio_input_device() -> Optional[Dict[str, Any]]:
    """
    Get the system default audio input device.
    
    Returns:
        Dictionary with default device information, or None if not available.
    
    Requirements: 1.3
    """
    if not SOUNDDEVICE_AVAILABLE:
        logger.error("Cannot get default device - sounddevice library not available")
        return None
    
    try:
        default_device_info = sd.query_devices(kind='input')
        
        if default_device_info:
            logger.info(f"Default audio input device: {default_device_info['name']}")
            return {
                'name': default_device_info['name'],
                'index': sd.default.device[0] if isinstance(sd.default.device, tuple) else sd.default.device,
                'channels': default_device_info['max_input_channels'],
                'default_samplerate': default_device_info['default_samplerate'],
                'hostapi': default_device_info['hostapi']
            }
        else:
            logger.error("No default audio input device found")
            return None
            
    except Exception as e:
        logger.error(f"Failed to get default audio input device: {e}")
        return None


def get_audio_device_by_name(device_name: str) -> Optional[Dict[str, Any]]:
    """
    Get audio device information by device name (case-insensitive partial match).
    
    Args:
        device_name: Name or partial name of the device to search for
    
    Returns:
        Dictionary with device information if found, None otherwise.
    
    Requirements: 1.1
    """
    input_devices = enumerate_audio_input_devices()
    
    search_name = device_name.lower()
    for device in input_devices:
        if search_name in device['name'].lower():
            logger.info(f"Found device matching '{device_name}': {device['name']}")
            return device
    
    logger.warning(f"No device found matching '{device_name}'")
    return None


def validate_audio_device_index(device_index: int) -> bool:
    """
    Validate that a device index is valid and available.
    
    Args:
        device_index: Device index to validate
    
    Returns:
        True if device index is valid, False otherwise.
    
    Requirements: 1.6
    """
    if not SOUNDDEVICE_AVAILABLE:
        logger.error("Cannot validate device index - sounddevice library not available")
        return False
    
    try:
        device_info = sd.query_devices(device_index)
        
        if device_info and device_info.get('max_input_channels', 0) > 0:
            logger.debug(f"Device index {device_index} is valid: {device_info['name']}")
            return True
        else:
            logger.warning(f"Device index {device_index} is not a valid input device")
            return False
            
    except Exception as e:
        logger.error(f"Failed to validate device index {device_index}: {e}")
        return False
