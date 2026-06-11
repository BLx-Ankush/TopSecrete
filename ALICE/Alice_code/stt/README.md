# STT Provider Infrastructure

This module provides Speech-to-Text (STT) provider infrastructure for neural turn detection in Alice's conversation fluidity enhancement.

## Overview

The STT provider infrastructure enables Alice to use neural STT models (AssemblyAI Universal-3 Pro or Deepgram Nova-3) for advanced turn detection, replacing simple silence-based VAD with acoustic and linguistic signal analysis.

**Requirements:** 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 15.1, 15.3, 15.9

## Components

### STTProvider (Abstract Base Class)

Abstract base class defining the interface for all STT providers.

**Key Methods:**
- `connect()`: Establish WebSocket connection to STT service
- `stream_audio(audio_frame)`: Stream audio frames for real-time transcription
- `get_transcription_result()`: Retrieve transcription results with turn detection signals
- `disconnect()`: Close connection gracefully
- `is_connected()`: Check connection status
- `reconnect()`: Automatic reconnection with exponential backoff

### AssemblyAIProvider

Implementation for AssemblyAI Universal-3 Pro Streaming model.

**Features:**
- Real-time streaming transcription
- End-of-utterance detection
- Acoustic and linguistic feature extraction
- Connection pooling and automatic reconnection
- Audio format validation (24kHz mono PCM)

**Model:** Universal-3 Pro Streaming

### DeepgramProvider

Implementation for Deepgram Nova-3 model.

**Features:**
- Real-time streaming transcription
- End-of-utterance detection with endpointing
- Acoustic and linguistic feature extraction
- Connection pooling and automatic reconnection
- Audio format validation (24kHz mono PCM)

**Model:** Nova-3

### TranscriptionResult

Data model for transcription results from STT providers.

**Attributes:**
- `text`: Transcribed text
- `confidence`: Transcription confidence (0.0-1.0)
- `end_of_utterance`: End-of-utterance signal from STT
- `is_final`: Whether this is a final result
- `timestamp_ms`: Timestamp in milliseconds
- `acoustic_features`: Acoustic features (pitch, energy, rhythm)
- `linguistic_features`: Linguistic features (sentence completion, discourse markers)

### STTProviderConfig

Configuration model for STT providers.

**Attributes:**
- `provider_type`: "assemblyai" or "deepgram"
- `api_key`: API key for authentication
- `sample_rate`: Audio sample rate (must be 24000 Hz)
- `encoding`: Audio encoding (default: "pcm_s16le")
- `channels`: Number of channels (must be 1 for mono)
- `connection_timeout_s`: Connection timeout in seconds
- `reconnect_attempts`: Maximum reconnection attempts
- `enable_end_of_utterance`: Enable end-of-utterance detection

### STTConfigFactory

Factory for creating STT provider instances from environment variables.

**Methods:**
- `create_from_env()`: Create provider from environment variables
- `create_config_from_env()`: Create configuration from environment
- `create_provider()`: Create provider from configuration
- `create_provider_with_defaults()`: Create provider with default settings

## Usage

### Basic Usage with Environment Variables

```python
from stt import create_stt_provider_from_env

# Create provider from environment variables
provider = create_stt_provider_from_env()

# Connect to STT service
await provider.connect()

# Stream audio frames
audio_frame = b"..."  # 24kHz mono PCM audio data
await provider.stream_audio(audio_frame)

# Get transcription results
result = await provider.get_transcription_result()
if result:
    print(f"Text: {result.text}")
    print(f"Confidence: {result.confidence}")
    print(f"End of utterance: {result.end_of_utterance}")

# Disconnect when done
await provider.disconnect()
```

### Explicit Configuration

```python
from stt import create_stt_provider

# Create AssemblyAI provider
provider = create_stt_provider(
    provider_type="assemblyai",
    api_key="your_api_key_here"
)

# Or create Deepgram provider
provider = create_stt_provider(
    provider_type="deepgram",
    api_key="your_api_key_here"
)
```

### Advanced Configuration

```python
from stt import STTProviderConfig, AssemblyAIProvider

# Create custom configuration
config = STTProviderConfig(
    provider_type="assemblyai",
    api_key="your_api_key_here",
    sample_rate=24000,
    channels=1,
    connection_timeout_s=10,
    reconnect_attempts=3,
    enable_end_of_utterance=True
)

# Create provider with custom config
provider = AssemblyAIProvider(config)
```

## Environment Variables

Configure STT providers using environment variables:

```bash
# Provider selection
STT_PROVIDER=assemblyai  # or "deepgram"

# API keys (provide the one matching your provider)
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# Audio configuration (must match LiveKit audio pipeline)
STT_SAMPLE_RATE=24000
STT_ENCODING=pcm_s16le
STT_CHANNELS=1

# Connection configuration
STT_CONNECTION_TIMEOUT_S=10
STT_RECONNECT_ATTEMPTS=3
STT_ENABLE_END_OF_UTTERANCE=true
```

## Audio Format Requirements

The STT provider infrastructure requires audio in the following format to match the LiveKit audio pipeline:

- **Sample Rate:** 24000 Hz (24kHz)
- **Encoding:** PCM 16-bit linear
- **Channels:** 1 (mono)
- **Chunk Size:** Typically 20ms chunks (960 bytes at 24kHz)

Audio format validation is performed automatically during provider initialization and connection.

## Connection Management

### Automatic Reconnection

The STT provider includes automatic reconnection logic with exponential backoff:

```python
# Reconnection is handled automatically
provider = create_stt_provider_from_env()
await provider.connect()

# If connection is lost, the provider will attempt to reconnect
# up to the configured number of attempts (default: 3)
```

### Manual Reconnection

```python
# Check connection status
if not await provider.is_connected():
    # Attempt manual reconnection
    success = await provider.reconnect()
    if success:
        print("Reconnected successfully")
    else:
        print("Reconnection failed")
```

### Connection Pooling

Both AssemblyAI and Deepgram providers implement connection pooling for reduced latency:

- WebSocket connections are reused across multiple audio streams
- Ping/pong keepalive messages maintain connection health
- Automatic cleanup of stale connections

## Error Handling

The STT provider infrastructure includes comprehensive error handling:

### Connection Errors

```python
from stt import create_stt_provider_from_env

provider = create_stt_provider_from_env()

try:
    await provider.connect()
except ConnectionError as e:
    print(f"Failed to connect: {e}")
    # Fall back to Silero VAD or retry
```

### Streaming Errors

```python
try:
    await provider.stream_audio(audio_frame)
except RuntimeError as e:
    print(f"Audio streaming failed: {e}")
    # Check connection and reconnect if needed
```

### Configuration Errors

```python
from stt import STTProviderConfig

try:
    config = STTProviderConfig(
        provider_type="assemblyai",
        api_key="",  # Invalid: empty API key
        sample_rate=16000  # Invalid: must be 24kHz
    )
except ValueError as e:
    print(f"Invalid configuration: {e}")
```

## Testing

Run the unit tests:

```bash
# Run all STT provider tests
pytest tests/test_stt_provider.py -v

# Run specific test class
pytest tests/test_stt_provider.py::TestAssemblyAIProvider -v

# Run with coverage
pytest tests/test_stt_provider.py --cov=stt --cov-report=html
```

## Integration with Neural Turn Detector

The STT provider infrastructure is designed to integrate with the Neural Turn Detector:

```python
from stt import create_stt_provider_from_env

# Create STT provider
stt_provider = create_stt_provider_from_env()

# Pass to Neural Turn Detector (to be implemented in Task 2)
# neural_detector = NeuralTurnDetector(
#     stt_provider=stt_provider,
#     confidence_threshold=0.4,
#     min_turn_silence_ms=300,
#     max_turn_silence_ms=1200
# )
```

## Performance Considerations

### Latency

- **Target VAD trigger time:** <307ms at P50
- **Connection establishment:** <10s (configurable timeout)
- **Transcription latency:** Varies by provider (typically 100-300ms)

### Cost

- **AssemblyAI Universal-3 Pro:** ~$0.0015/minute
- **Deepgram Nova-3:** ~$0.0043/minute

Choose AssemblyAI for cost efficiency or Deepgram for potentially lower latency.

### Throughput

- Both providers support real-time streaming with 20ms audio chunks
- Connection pooling reduces overhead for multiple concurrent streams
- WebSocket keepalive maintains connection health

## Troubleshooting

### Connection Timeout

If connection times out:
1. Check API key is valid
2. Verify network connectivity
3. Increase `STT_CONNECTION_TIMEOUT_S` if needed
4. Check provider service status

### Audio Format Mismatch

If audio format validation fails:
1. Verify audio is 24kHz mono PCM
2. Check LiveKit audio pipeline configuration
3. Ensure audio chunks are properly formatted

### Empty Transcription Results

If `get_transcription_result()` always returns None:
1. Verify audio is being streamed correctly
2. Check that audio contains speech (not silence)
3. Verify provider connection is active
4. Check provider logs for errors

## Future Enhancements

Planned enhancements for future tasks:

1. **Neural Turn Detector Integration** (Task 2)
   - Use transcription results for turn detection
   - Combine acoustic and linguistic signals
   - Calculate end-of-turn confidence scores

2. **Fallback to Silero VAD** (Task 3)
   - Automatic fallback on connection failure
   - Health monitoring and restoration
   - Seamless switching between neural and VAD

3. **Multi-Language Support** (Future)
   - Language detection from audio
   - Language-specific turn detection models
   - Consistent performance across languages

## References

- [AssemblyAI Universal-3 Pro Documentation](https://www.assemblyai.com/docs/models/universal-3)
- [Deepgram Nova-3 Documentation](https://developers.deepgram.com/docs/nova-3)
- [LiveKit Audio Pipeline Documentation](https://docs.livekit.io/agents/overview/)

## License

This module is part of the Alice voice assistant system.
