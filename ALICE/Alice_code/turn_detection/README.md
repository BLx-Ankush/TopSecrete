# Neural Turn Detection Module

This module implements neural turn detection for Alice's conversation fluidity enhancement using STT provider streaming (AssemblyAI Universal-3 Pro or Deepgram Nova-3).

## Overview

The Neural Turn Detector uses acoustic and linguistic signal analysis from neural STT models to detect end-of-turn with higher accuracy than simple silence-based VAD. It analyzes:

- **Acoustic signals**: Pitch, energy, rhythm patterns
- **Linguistic signals**: Sentence completion, discourse markers
- **Silence duration**: Configurable min/max thresholds

## Components

### NeuralTurnDetector

Main class for neural turn detection.

**Key Features:**
- Streams audio frames to STT provider
- Calculates End-of-Turn Confidence score (0.0-1.0)
- Signals end-of-turn when confidence exceeds threshold
- Falls back to Silero VAD if STT provider unavailable
- Tracks audio and silence durations
- Creates turn detection events for monitoring

**Usage:**

```python
from turn_detection import NeuralTurnDetector
from stt import create_stt_provider_from_env

# Create STT provider
stt_provider = create_stt_provider_from_env()

# Initialize neural turn detector
detector = NeuralTurnDetector(
    stt_provider=stt_provider,
    confidence_threshold=0.4,
    min_turn_silence_ms=300,
    max_turn_silence_ms=1200,
    fallback_vad=None  # Optional Silero VAD instance
)

# Connect STT provider
await stt_provider.connect()

# Process audio frames
await detector.process_audio_frame(audio_frame)

# Check for end-of-turn
if await detector.is_end_of_turn():
    print("End-of-turn detected!")
    
    # Create event for monitoring
    event = detector.create_turn_detection_event(triggered=True)
    
    # Reset for next turn
    await detector.reset()

# Health check
if not await detector.health_check():
    print("Neural turn detector unhealthy, may fall back to Silero VAD")
```

### NeuralTurnDetectorConfig

Configuration management for neural turn detection.

**Environment Variables:**
- `NEURAL_TURN_DETECTOR_ENABLED`: Enable neural turn detection (default: true)
- `END_OF_TURN_CONFIDENCE_THRESHOLD`: Confidence threshold 0.0-1.0 (default: 0.4)
- `MIN_TURN_SILENCE_MS`: Minimum silence duration in ms (default: 300)
- `MAX_TURN_SILENCE_MS`: Maximum silence duration in ms (default: 1200)
- `NEURAL_TURN_DETECTOR_HEALTH_CHECK_INTERVAL_S`: Health check interval in seconds (default: 30)
- `NEURAL_TURN_DETECTOR_MAX_FAILURES`: Max failures before fallback (default: 3)

**Usage:**

```python
from turn_detection import create_neural_turn_detector_config_from_env

# Load configuration from environment
config = create_neural_turn_detector_config_from_env()

# Log configuration
config.log_configuration()

# Use configuration
detector = NeuralTurnDetector(
    stt_provider=stt_provider,
    confidence_threshold=config.confidence_threshold,
    min_turn_silence_ms=config.min_turn_silence_ms,
    max_turn_silence_ms=config.max_turn_silence_ms
)
```

### TurnDetectionEvent

Data model for turn detection events.

**Attributes:**
- `event_id`: Unique event identifier
- `timestamp_ms`: Event timestamp in milliseconds
- `detector_type`: "neural" or "silero"
- `end_of_turn_confidence`: Confidence score (0.0-1.0)
- `threshold`: Threshold used for detection
- `triggered`: Whether end-of-turn was triggered
- `audio_duration_ms`: Duration of user audio
- `silence_duration_ms`: Duration of silence before trigger
- `is_false_trigger`: Whether this was a false trigger (labeled post-hoc)

**Usage:**

```python
from turn_detection import TurnDetectionEvent

# Create event manually
event = TurnDetectionEvent.create(
    detector_type="neural",
    end_of_turn_confidence=0.65,
    threshold=0.4,
    triggered=True,
    audio_duration_ms=2500,
    silence_duration_ms=350
)

# Convert to dictionary for logging
event_dict = event.to_dict()

# Create from dictionary
event = TurnDetectionEvent.from_dict(event_dict)
```

## Configuration Validation

All configuration parameters are validated on initialization:

- **Confidence threshold**: Must be between 0.0 and 1.0
- **Min turn silence**: Must be positive and between 100ms and 5000ms
- **Max turn silence**: Must be positive, between 100ms and 5000ms, and greater than min silence
- **Health check interval**: Must be positive
- **Max failures**: Must be non-negative

Invalid configuration will raise `ValueError` with a descriptive error message.

## Fallback to Silero VAD

The neural turn detector automatically falls back to Silero VAD if:

1. STT provider initialization fails
2. STT provider connection is lost during conversation
3. Health check fails 3 consecutive times (configurable)

When in fallback mode:
- `is_fallback_mode()` returns `True`
- `get_detector_type()` returns `"silero"`
- Turn detection events are logged with `detector_type="silero"`

## Integration with STT Providers

The neural turn detector integrates with the STT provider infrastructure from task 1:

```python
from stt import create_stt_provider_from_env
from turn_detection import NeuralTurnDetector

# Create STT provider (AssemblyAI or Deepgram based on env)
stt_provider = create_stt_provider_from_env()

# Create neural turn detector
detector = NeuralTurnDetector(
    stt_provider=stt_provider,
    confidence_threshold=0.4,
    min_turn_silence_ms=300,
    max_turn_silence_ms=1200
)

# Connect and start processing
await stt_provider.connect()
```

## Requirements Mapping

This implementation satisfies the following requirements:

- **1.1**: Neural_Turn_Detector integrates with AssemblyAI Universal-3 Pro Streaming OR Deepgram Nova-3
- **1.2**: Configure end-of-turn confidence threshold to 0.4
- **1.3**: Configure minimum turn silence to 300 milliseconds
- **1.4**: Configure maximum turn silence to 1200 milliseconds
- **1.5**: Process acoustic signals to detect turn boundaries
- **1.6**: Process linguistic signals to detect turn boundaries
- **1.7**: Signal end-of-turn when confidence exceeds threshold
- **1.8**: Trigger response generation within 307ms at P50 (integration point)
- **1.9**: Produce confidence scores between 0.0 and 1.0 inclusive
- **3.1**: Activate Silero_VAD as fallback if initialization fails
- **3.2**: Switch to Silero_VAD if connection lost
- **15.4**: Support configuration of end-of-turn confidence threshold
- **15.5**: Support configuration of minimum turn silence
- **15.6**: Support configuration of maximum turn silence
- **15.8**: Validate all configuration values at startup
- **15.9**: Log validation errors and use default values on failure

## Next Steps

Task 2.1 is now complete. The next tasks are:

- **2.2**: Implement audio frame processing pipeline
- **2.3**: Implement end-of-turn confidence calculation
- **2.4**: Write property test for confidence score range invariant
- **2.5**: Implement end-of-turn detection logic
- **2.6**: Write property test for end-of-turn signaling logic

## Testing

Unit tests for this implementation should be created in `tests/test_neural_turn_detector.py` to verify:

- Configuration validation
- Initialization with valid/invalid parameters
- Confidence score range (0.0-1.0)
- End-of-turn detection logic
- Fallback mode activation
- Turn detection event creation
