# Gemini Multimodal Live API WebSocket Streaming Client

## Overview

The `gemini_streaming_client.py` module provides a WebSocket-based streaming client for the Gemini Multimodal Live API, enabling real-time bidirectional audio streaming with sentence-level response processing.

## Key Features

✅ **WebSocket Connection**: Real-time bidirectional communication with Gemini API  
✅ **Audio Streaming**: Send user audio and receive AI audio in real-time  
✅ **Sentence-Level Streaming**: Begin TTS playback while response is still generating  
✅ **Regional Routing**: Optimized for asia-south1 (Mumbai) with automatic fallbacks  
✅ **Connection Management**: Automatic reconnection with exponential backoff  
✅ **Error Handling**: Comprehensive error handling and graceful degradation  
✅ **Metrics Tracking**: Monitor connection status, latency, and data transfer  

## Performance Targets

- **Network Latency**: <100ms (via regional routing)
- **Sentence Streaming**: First sentence playback within 200ms
- **Connection Resilience**: Automatic reconnection with exponential backoff

## Installation

The required `websockets` package is already included in `requirements.txt`:

```bash
pip install websockets
```

## Basic Usage

```python
import asyncio
from gemini_streaming_client import GeminiStreamingClient, GeminiRegion

async def main():
    # Initialize client with Mumbai region for optimal latency
    client = GeminiStreamingClient(
        api_key="your-google-api-key",  # Or set GOOGLE_API_KEY env var
        region=GeminiRegion.ASIA_SOUTH1,
        enable_auto_reconnect=True
    )
    
    # Set up callbacks
    def on_sentence(sentence: str):
        print(f"Sentence ready for TTS: {sentence}")
        # Send to TTS immediately for low-latency playback
    
    def on_audio(audio_data: bytes):
        print(f"Audio chunk received: {len(audio_data)} bytes")
        # Play audio immediately (stream-to-play)
    
    def on_state_change(state):
        print(f"Connection state: {state.value}")
    
    client.on_sentence_complete = on_sentence
    client.on_audio_chunk = on_audio
    client.on_connection_state_change = on_state_change
    
    # Connect to API
    if await client.connect():
        print("Connected successfully!")
        
        # Send audio data
        # audio_data = capture_audio_from_microphone()
        # await client.send_audio(audio_data)
        
        # Keep connection alive
        await asyncio.sleep(60)
        
        # Disconnect
        await client.disconnect()
        
        # Print metrics
        metrics = client.get_metrics()
        print(f"Session metrics: {metrics}")
    else:
        print("Connection failed")

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced Usage

### Context Manager

```python
async with GeminiStreamingClient(api_key="your-key") as client:
    # Client automatically connects on entry
    await client.send_audio(audio_data)
    # Client automatically disconnects on exit
```

### Custom Region Configuration

```python
# Use Singapore region as primary
client = GeminiStreamingClient(
    api_key="your-key",
    region=GeminiRegion.ASIA_SOUTHEAST1
)
```

### Error Handling

```python
def on_error(error: Exception):
    print(f"Error occurred: {error}")
    # Handle error (log, retry, notify user, etc.)

client.on_error = on_error
```

### Metrics Monitoring

```python
metrics = client.get_metrics()
print(f"Connection state: {metrics['state']}")
print(f"Region: {metrics['region']}")
print(f"Audio sent: {metrics['total_audio_sent']} bytes")
print(f"Audio received: {metrics['total_audio_received']} bytes")
print(f"Sentences received: {metrics['total_sentences_received']}")
print(f"Connection duration: {metrics['connection_duration']:.1f}s")
```

## Regional Routing

The client supports multiple regions with automatic fallback:

1. **ASIA_SOUTH1** (Mumbai) - Primary for optimal latency
2. **ASIA_SOUTHEAST1** (Singapore) - Fallback 1
3. **US_CENTRAL1** (Iowa) - Fallback 2
4. **GLOBAL** - Last resort

If the primary region fails, the client automatically tries fallback regions in order.

## Sentence Boundary Detection

The `SentenceBoundaryDetector` class identifies complete sentences in streaming text:

```python
from gemini_streaming_client import SentenceBoundaryDetector

detector = SentenceBoundaryDetector()

# Add streaming text chunks
sentences = detector.add_text("The weather today is sunny.")
# Returns: ["The weather today is sunny."]

# Handle incomplete sentences
sentences = detector.add_text("Tomorrow will be")
# Returns: [] (buffered until complete)

sentences = detector.add_text(" cloudy.")
# Returns: ["Tomorrow will be cloudy."]

# Flush remaining buffer at end of response
final = detector.flush()
```

## Connection States

The client tracks connection state through the `ConnectionState` enum:

- **DISCONNECTED**: Not connected
- **CONNECTING**: Establishing connection
- **CONNECTED**: Active connection
- **RECONNECTING**: Attempting to reconnect
- **FAILED**: Connection failed

## Configuration Options

### Client Initialization

```python
client = GeminiStreamingClient(
    api_key="your-key",                    # API key (or GOOGLE_API_KEY env var)
    region=GeminiRegion.ASIA_SOUTH1,       # Primary region
    model="gemini-2.5-flash-...",          # Model name
    voice="Erinome",                       # Voice name for TTS
    enable_auto_reconnect=True             # Enable automatic reconnection
)
```

### Connection Parameters

- `MAX_RECONNECT_ATTEMPTS`: 5 (maximum reconnection attempts)
- `RECONNECT_BASE_DELAY`: 1.0s (initial reconnection delay)
- `RECONNECT_MAX_DELAY`: 30.0s (maximum reconnection delay)
- `CONNECTION_TIMEOUT`: 10.0s (connection timeout)
- `PING_INTERVAL`: 30.0s (WebSocket ping interval)
- `PING_TIMEOUT`: 10.0s (WebSocket ping timeout)

## Integration with Alice Agent

To integrate with the Alice agent in `agent.py`:

1. Import the streaming client
2. Replace `google.beta.realtime.RealtimeModel` with `GeminiStreamingClient`
3. Set up callbacks for sentence-level TTS and audio playback
4. Configure regional routing for optimal latency

See the design document for detailed integration steps.

## Testing

Run the comprehensive unit test suite:

```bash
pytest tests/test_gemini_streaming_client.py -v
```

The test suite covers:
- Sentence boundary detection (10 tests)
- Client initialization and configuration (12 tests)
- Async operations (3 tests)
- Regional routing (2 tests)
- Error handling (2 tests)
- Connection management (2 tests)

## Troubleshooting

### Connection Timeout

If connection times out, check:
- API key is valid
- Network connectivity
- Region availability

The client will automatically try fallback regions.

### Audio Not Streaming

Ensure callbacks are set before connecting:
```python
client.on_audio_chunk = your_audio_handler
await client.connect()
```

### Reconnection Failures

If all reconnection attempts fail:
- Check API quota limits
- Verify API key permissions
- Check network stability

## Performance Optimization

For optimal latency:

1. **Use Mumbai Region**: `region=GeminiRegion.ASIA_SOUTH1`
2. **Enable Auto-Reconnect**: `enable_auto_reconnect=True`
3. **Stream-to-Play**: Play audio immediately in `on_audio_chunk` callback
4. **Sentence-Level TTS**: Start TTS in `on_sentence_complete` callback
5. **Monitor Metrics**: Track latency with `get_metrics()`

## License

Part of the Alice voice assistant project.
