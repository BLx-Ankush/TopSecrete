"""
Unit tests for STT provider infrastructure.

This module tests the STT provider abstract base class, concrete implementations
(AssemblyAI and Deepgram), and configuration factory.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 15.1, 15.3, 15.9
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
import websockets.exceptions

from stt import (
    STTProvider,
    AssemblyAIProvider,
    DeepgramProvider,
    TranscriptionResult,
    STTProviderConfig
)
from stt.config_factory import (
    STTConfigFactory,
    create_stt_provider_from_env,
    create_stt_provider
)
def make_mock_websocket(initial_messages=None):
    """Helper to create a mock websocket that avoids infinite loops in recv()."""
    mock_ws = AsyncMock()
    messages = initial_messages or []
    recv_calls = 0
    
    async def mock_recv():
        nonlocal recv_calls
        if recv_calls < len(messages):
            msg = messages[recv_calls]
            recv_calls += 1
            return msg
        else:
            # Yield and sleep forever to prevent infinite loop in background task
            await asyncio.sleep(3600)
            return ""
            
    mock_ws.recv = mock_recv
    return mock_ws


class TestSTTProviderConfig:
    """Test STT provider configuration model."""
    
    def test_valid_assemblyai_config(self):
        """Test creating valid AssemblyAI configuration."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key",
            sample_rate=24000,
            channels=1
        )
        
        assert config.provider_type == "assemblyai"
        assert config.api_key == "test_key"
        assert config.sample_rate == 24000
        assert config.channels == 1
    
    def test_valid_deepgram_config(self):
        """Test creating valid Deepgram configuration."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key",
            sample_rate=24000,
            channels=1
        )
        
        assert config.provider_type == "deepgram"
        assert config.api_key == "test_key"
    
    def test_invalid_provider_type(self):
        """Test that invalid provider type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid provider type"):
            STTProviderConfig(
                provider_type="invalid",
                api_key="test_key"
            )
    
    def test_empty_api_key(self):
        """Test that empty API key raises ValueError."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            STTProviderConfig(
                provider_type="assemblyai",
                api_key=""
            )
    
    def test_invalid_sample_rate(self):
        """Test that invalid sample rate raises ValueError (must be 24kHz)."""
        with pytest.raises(ValueError, match="Sample rate must be 24000 Hz"):
            STTProviderConfig(
                provider_type="assemblyai",
                api_key="test_key",
                sample_rate=16000  # Invalid: must be 24kHz
            )
    
    def test_invalid_channels(self):
        """Test that invalid channels raises ValueError (must be mono)."""
        with pytest.raises(ValueError, match="Channels must be 1"):
            STTProviderConfig(
                provider_type="assemblyai",
                api_key="test_key",
                channels=2  # Invalid: must be mono
            )
    
    def test_config_to_dict(self):
        """Test converting configuration to dictionary."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        config_dict = config.to_dict()
        
        assert config_dict["provider_type"] == "assemblyai"
        assert config_dict["api_key"] == "test_key"
        assert config_dict["sample_rate"] == 24000
        assert config_dict["channels"] == 1


class TestTranscriptionResult:
    """Test transcription result data model."""
    
    def test_valid_transcription_result(self):
        """Test creating valid transcription result."""
        result = TranscriptionResult(
            text="Hello world",
            confidence=0.95,
            end_of_utterance=True,
            is_final=True,
            timestamp_ms=1000
        )
        
        assert result.text == "Hello world"
        assert result.confidence == 0.95
        assert result.end_of_utterance is True
        assert result.is_final is True
        assert result.timestamp_ms == 1000
    
    def test_confidence_validation_too_low(self):
        """Test that confidence < 0.0 raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            TranscriptionResult(
                text="test",
                confidence=-0.1,
                end_of_utterance=False,
                is_final=False,
                timestamp_ms=1000
            )
    
    def test_confidence_validation_too_high(self):
        """Test that confidence > 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            TranscriptionResult(
                text="test",
                confidence=1.5,
                end_of_utterance=False,
                is_final=False,
                timestamp_ms=1000
            )
    
    def test_negative_timestamp(self):
        """Test that negative timestamp raises ValueError."""
        with pytest.raises(ValueError, match="Timestamp must be non-negative"):
            TranscriptionResult(
                text="test",
                confidence=0.9,
                end_of_utterance=False,
                is_final=False,
                timestamp_ms=-100
            )
    
    def test_transcription_result_to_dict(self):
        """Test converting transcription result to dictionary."""
        result = TranscriptionResult(
            text="Hello",
            confidence=0.9,
            end_of_utterance=True,
            is_final=True,
            timestamp_ms=1000,
            acoustic_features={"pitch": 200},
            linguistic_features={"word_count": 1}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["text"] == "Hello"
        assert result_dict["confidence"] == 0.9
        assert result_dict["acoustic_features"]["pitch"] == 200
        assert result_dict["linguistic_features"]["word_count"] == 1
    
    def test_transcription_result_from_dict(self):
        """Test creating transcription result from dictionary."""
        data = {
            "text": "Hello",
            "confidence": 0.9,
            "end_of_utterance": True,
            "is_final": True,
            "timestamp_ms": 1000,
            "acoustic_features": {"pitch": 200},
            "linguistic_features": {"word_count": 1}
        }
        
        result = TranscriptionResult.from_dict(data)
        
        assert result.text == "Hello"
        assert result.confidence == 0.9
        assert result.acoustic_features["pitch"] == 200


class TestSTTProvider:
    """Test STT provider abstract base class."""
    
    def test_audio_format_validation_valid(self):
        """Test that valid audio format passes validation."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        # Create a concrete implementation for testing
        provider = AssemblyAIProvider(config)
        
        # Should not raise exception
        provider.validate_audio_format(24000, 1)
    
    def test_audio_format_validation_invalid_sample_rate(self):
        """Test that invalid sample rate fails validation."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        with pytest.raises(ValueError, match="Audio sample rate must be 24000 Hz"):
            provider.validate_audio_format(16000, 1)
    
    def test_audio_format_validation_invalid_channels(self):
        """Test that invalid channels fails validation."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        with pytest.raises(ValueError, match="Audio must be mono"):
            provider.validate_audio_format(24000, 2)
    
    def test_get_provider_type(self):
        """Test getting provider type."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        assert provider.get_provider_type() == "assemblyai"
    
    def test_get_config(self):
        """Test getting provider configuration."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        retrieved_config = provider.get_config()
        assert retrieved_config.provider_type == "assemblyai"
        assert retrieved_config.api_key == "test_key"


class TestAssemblyAIProvider:
    """Test AssemblyAI provider implementation."""
    
    def test_initialization(self):
        """Test AssemblyAI provider initialization."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        assert provider.get_provider_type() == "assemblyai"
        assert provider._connected is False
    
    def test_invalid_provider_type(self):
        """Test that wrong provider type raises ValueError."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key"
        )
        
        with pytest.raises(ValueError, match="Invalid provider type for AssemblyAI"):
            AssemblyAIProvider(config)
    
    @pytest.mark.asyncio
    async def test_is_connected_initially_false(self):
        """Test that provider is not connected initially."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        assert await provider.is_connected() is False
    
    @pytest.mark.asyncio
    async def test_stream_audio_not_connected(self):
        """Test that streaming audio when not connected raises error."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        with pytest.raises(ConnectionError, match="Not connected"):
            await provider.stream_audio(b"audio_data")
    
    @pytest.mark.asyncio
    async def test_get_transcription_result_empty_queue(self):
        """Test getting transcription result from empty queue returns None."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        result = await provider.get_transcription_result()
        assert result is None


class TestDeepgramProvider:
    """Test Deepgram provider implementation."""
    
    def test_initialization(self):
        """Test Deepgram provider initialization."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key"
        )
        
        provider = DeepgramProvider(config)
        
        assert provider.get_provider_type() == "deepgram"
        assert provider._connected is False
    
    def test_invalid_provider_type(self):
        """Test that wrong provider type raises ValueError."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        with pytest.raises(ValueError, match="Invalid provider type for Deepgram"):
            DeepgramProvider(config)
    
    @pytest.mark.asyncio
    async def test_is_connected_initially_false(self):
        """Test that provider is not connected initially."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key"
        )
        
        provider = DeepgramProvider(config)
        
        assert await provider.is_connected() is False
    
    @pytest.mark.asyncio
    async def test_stream_audio_not_connected(self):
        """Test that streaming audio when not connected raises error."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key"
        )
        
        provider = DeepgramProvider(config)
        
        with pytest.raises(ConnectionError, match="Not connected"):
            await provider.stream_audio(b"audio_data")
    
    @pytest.mark.asyncio
    async def test_get_transcription_result_empty_queue(self):
        """Test getting transcription result from empty queue returns None."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key"
        )
        
        provider = DeepgramProvider(config)
        
        result = await provider.get_transcription_result()
        assert result is None


class TestSTTConfigFactory:
    """Test STT configuration factory."""
    
    @patch.dict('os.environ', {
        'STT_PROVIDER': 'assemblyai',
        'ASSEMBLYAI_API_KEY': 'test_assemblyai_key'
    })
    def test_create_from_env_assemblyai(self):
        """Test creating AssemblyAI provider from environment."""
        provider = STTConfigFactory.create_from_env()
        
        assert isinstance(provider, AssemblyAIProvider)
        assert provider.get_provider_type() == "assemblyai"
    
    @patch.dict('os.environ', {
        'STT_PROVIDER': 'deepgram',
        'DEEPGRAM_API_KEY': 'test_deepgram_key'
    })
    def test_create_from_env_deepgram(self):
        """Test creating Deepgram provider from environment."""
        provider = STTConfigFactory.create_from_env()
        
        assert isinstance(provider, DeepgramProvider)
        assert provider.get_provider_type() == "deepgram"
    
    @patch.dict('os.environ', {
        'STT_PROVIDER': 'assemblyai'
    }, clear=True)
    def test_create_from_env_missing_api_key(self):
        """Test that missing API key raises ValueError."""
        with pytest.raises(ValueError, match="ASSEMBLYAI_API_KEY environment variable is required"):
            STTConfigFactory.create_from_env()
    
    @patch.dict('os.environ', {
        'STT_PROVIDER': 'invalid',
        'ASSEMBLYAI_API_KEY': 'test_key'
    })
    def test_create_from_env_invalid_provider(self):
        """Test that invalid provider type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid STT_PROVIDER"):
            STTConfigFactory.create_from_env()
    
    def test_create_provider_with_defaults_assemblyai(self):
        """Test creating AssemblyAI provider with defaults."""
        provider = STTConfigFactory.create_provider_with_defaults(
            "assemblyai",
            "test_key"
        )
        
        assert isinstance(provider, AssemblyAIProvider)
        assert provider.config.sample_rate == 24000
        assert provider.config.channels == 1
    
    def test_create_provider_with_defaults_deepgram(self):
        """Test creating Deepgram provider with defaults."""
        provider = STTConfigFactory.create_provider_with_defaults(
            "deepgram",
            "test_key"
        )
        
        assert isinstance(provider, DeepgramProvider)
        assert provider.config.sample_rate == 24000
        assert provider.config.channels == 1
    
    def test_create_provider_invalid_type(self):
        """Test that invalid provider type raises ValueError."""
        # Create a valid config first
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        # Manually override the provider_type to bypass validation
        # This simulates a corrupted config object
        object.__setattr__(config, 'provider_type', 'invalid')
        
        with pytest.raises(ValueError, match="Invalid provider type"):
            STTConfigFactory.create_provider(config)
    
    def test_convenience_function_create_stt_provider(self):
        """Test convenience function for creating provider."""
        provider = create_stt_provider("assemblyai", "test_key")
        
        assert isinstance(provider, AssemblyAIProvider)
        assert provider.get_provider_type() == "assemblyai"


class TestAssemblyAIProviderConnection:
    """Test AssemblyAI provider connection and streaming behavior."""
    
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to AssemblyAI."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        # Mock WebSocket connection
        mock_ws = make_mock_websocket([json.dumps({
            "message_type": "SessionBegins",
            "session_id": "test_session_123"
        })])
        
        # Create async coroutine for connect
        async def mock_connect(*args, **kwargs):
            return mock_ws
        
        with patch('websockets.connect', side_effect=mock_connect):
            await provider.connect()
            
            assert await provider.is_connected() is True
            assert provider._session_id == "test_session_123"
    
    @pytest.mark.asyncio
    async def test_connect_timeout(self):
        """Test connection timeout handling."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key",
            connection_timeout_s=1
        )
        
        provider = AssemblyAIProvider(config)
        
        # Mock connection that times out
        async def slow_connect(*args, **kwargs):
            await asyncio.sleep(2)
            return AsyncMock()
        
        with patch('websockets.connect', side_effect=slow_connect):
            with pytest.raises(ConnectionError, match="timed out"):
                await provider.connect()
    
    @pytest.mark.asyncio
    async def test_connect_invalid_credentials(self):
        """Test connection with invalid API credentials."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="invalid_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        # Mock WebSocket that raises authentication error
        async def auth_error(*args, **kwargs):
            raise websockets.exceptions.InvalidStatusCode(401, {})
        
        with patch('websockets.connect', side_effect=auth_error):
            with pytest.raises(ConnectionError, match="WebSocket connection failed"):
                await provider.connect()
    
    @pytest.mark.asyncio
    async def test_stream_audio_success(self):
        """Test successful audio streaming."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        # Mock connected state
        mock_ws = AsyncMock()
        provider._websocket = mock_ws
        provider._connected = True
        
        audio_data = b'\x00\x01\x02\x03' * 100  # Mock audio frame
        
        await provider.stream_audio(audio_data)
        
        # Verify audio was sent
        mock_ws.send.assert_called_once_with(audio_data)
    
    @pytest.mark.asyncio
    async def test_stream_audio_connection_lost(self):
        """Test audio streaming when connection is lost."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        # Mock connected state with failing WebSocket
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock(side_effect=websockets.exceptions.ConnectionClosed(None, None))
        provider._websocket = mock_ws
        provider._connected = True
        
        audio_data = b'\x00\x01\x02\x03' * 100
        
        with pytest.raises(RuntimeError, match="Audio streaming failed"):
            await provider.stream_audio(audio_data)
        
        # Verify connection state updated
        assert provider._connected is False
    
    @pytest.mark.asyncio
    async def test_disconnect_graceful(self):
        """Test graceful disconnection."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        # Mock connected state
        mock_ws = AsyncMock()
        mock_receive_task = AsyncMock()
        mock_receive_task.done.return_value = False
        
        provider._websocket = mock_ws
        provider._connected = True
        provider._receive_task = mock_receive_task
        provider._session_id = "test_session"
        
        await provider.disconnect()
        
        # Verify termination message sent
        mock_ws.send.assert_called_once()
        call_args = mock_ws.send.call_args[0][0]
        assert "terminate_session" in call_args
        
        # Verify WebSocket closed
        mock_ws.close.assert_called_once()
        
        # Verify receive task cancelled
        mock_receive_task.cancel.assert_called_once()
        
        # Verify state cleaned up
        assert provider._connected is False
        assert provider._session_id is None
    
    @pytest.mark.asyncio
    async def test_reconnect_success(self):
        """Test successful reconnection after connection loss."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key",
            reconnect_attempts=3
        )
        
        provider = AssemblyAIProvider(config)
        
        # Mock successful reconnection
        mock_ws = make_mock_websocket([json.dumps({
            "message_type": "SessionBegins",
            "session_id": "test_session_reconnect"
        })])
        
        async def mock_connect(*args, **kwargs):
            return mock_ws
        
        with patch('websockets.connect', side_effect=mock_connect):
            result = await provider.reconnect()
            
            assert result is True
            assert provider._connection_attempts == 0  # Reset on success
    
    @pytest.mark.asyncio
    async def test_reconnect_max_attempts_exceeded(self):
        """Test reconnection failure after max attempts."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key",
            reconnect_attempts=2
        )
        
        provider = AssemblyAIProvider(config)
        provider._connection_attempts = 2  # Already at max
        
        result = await provider.reconnect()
        
        assert result is False


class TestDeepgramProviderConnection:
    """Test Deepgram provider connection and streaming behavior."""
    
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to Deepgram."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key"
        )
        
        provider = DeepgramProvider(config)
        
        # Mock WebSocket connection
        mock_ws = make_mock_websocket()
        
        async def mock_connect(*args, **kwargs):
            return mock_ws
        
        with patch('websockets.connect', side_effect=mock_connect):
            await provider.connect()
            
            assert await provider.is_connected() is True
    
    @pytest.mark.asyncio
    async def test_connect_timeout(self):
        """Test connection timeout handling."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key",
            connection_timeout_s=1
        )
        
        provider = DeepgramProvider(config)
        
        # Mock connection that times out
        async def slow_connect(*args, **kwargs):
            await asyncio.sleep(2)
            return AsyncMock()
        
        with patch('websockets.connect', side_effect=slow_connect):
            with pytest.raises(ConnectionError, match="timed out"):
                await provider.connect()
    
    @pytest.mark.asyncio
    async def test_connect_invalid_credentials(self):
        """Test connection with invalid API credentials."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="invalid_key"
        )
        
        provider = DeepgramProvider(config)
        
        # Mock WebSocket that raises authentication error
        async def auth_error(*args, **kwargs):
            raise websockets.exceptions.InvalidStatusCode(401, {})
        
        with patch('websockets.connect', side_effect=auth_error):
            with pytest.raises(ConnectionError, match="WebSocket connection failed"):
                await provider.connect()
    
    @pytest.mark.asyncio
    async def test_stream_audio_success(self):
        """Test successful audio streaming."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key"
        )
        
        provider = DeepgramProvider(config)
        
        # Mock connected state
        mock_ws = AsyncMock()
        provider._websocket = mock_ws
        provider._connected = True
        
        audio_data = b'\x00\x01\x02\x03' * 100  # Mock audio frame
        
        await provider.stream_audio(audio_data)
        
        # Verify audio was sent
        mock_ws.send.assert_called_once_with(audio_data)
    
    @pytest.mark.asyncio
    async def test_stream_audio_connection_lost(self):
        """Test audio streaming when connection is lost."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key"
        )
        
        provider = DeepgramProvider(config)
        
        # Mock connected state with failing WebSocket
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock(side_effect=websockets.exceptions.ConnectionClosed(None, None))
        provider._websocket = mock_ws
        provider._connected = True
        
        audio_data = b'\x00\x01\x02\x03' * 100
        
        with pytest.raises(RuntimeError, match="Audio streaming failed"):
            await provider.stream_audio(audio_data)
        
        # Verify connection state updated
        assert provider._connected is False
    
    @pytest.mark.asyncio
    async def test_disconnect_graceful(self):
        """Test graceful disconnection."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key"
        )
        
        provider = DeepgramProvider(config)
        
        # Mock connected state
        mock_ws = AsyncMock()
        mock_receive_task = Mock()
        mock_receive_task.done = Mock(return_value=False)
        mock_receive_task.cancel = Mock()
        
        provider._websocket = mock_ws
        provider._connected = True
        provider._receive_task = mock_receive_task
        
        await provider.disconnect()
        
        # Verify close frame sent (empty bytes)
        mock_ws.send.assert_called_once_with(b"")
        
        # Verify WebSocket closed
        mock_ws.close.assert_called_once()
        
        # Verify receive task cancelled
        mock_receive_task.cancel.assert_called_once()
        
        # Verify state cleaned up
        assert provider._connected is False
    
    @pytest.mark.asyncio
    async def test_reconnect_success(self):
        """Test successful reconnection after connection loss."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key",
            reconnect_attempts=3
        )
        
        provider = DeepgramProvider(config)
        
        # Mock successful reconnection
        mock_ws = AsyncMock()
        
        async def mock_connect(*args, **kwargs):
            return mock_ws
        
        with patch('websockets.connect', side_effect=mock_connect):
            result = await provider.reconnect()
            
            assert result is True
            assert provider._connection_attempts == 0  # Reset on success


class TestAudioFormatValidation:
    """Test audio format validation for both providers."""
    
    def test_valid_format_24khz_mono(self):
        """Test that 24kHz mono format is accepted."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        # Should not raise exception
        provider.validate_audio_format(24000, 1)
    
    def test_invalid_sample_rate_16khz(self):
        """Test that 16kHz sample rate is rejected."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        with pytest.raises(ValueError, match="Audio sample rate must be 24000 Hz"):
            provider.validate_audio_format(16000, 1)
    
    def test_invalid_sample_rate_48khz(self):
        """Test that 48kHz sample rate is rejected."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key"
        )
        
        provider = DeepgramProvider(config)
        
        with pytest.raises(ValueError, match="Audio sample rate must be 24000 Hz"):
            provider.validate_audio_format(48000, 1)
    
    def test_invalid_channels_stereo(self):
        """Test that stereo audio is rejected."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        with pytest.raises(ValueError, match="Audio must be mono"):
            provider.validate_audio_format(24000, 2)
    
    def test_invalid_channels_surround(self):
        """Test that surround sound is rejected."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key"
        )
        
        provider = DeepgramProvider(config)
        
        with pytest.raises(ValueError, match="Audio must be mono"):
            provider.validate_audio_format(24000, 6)
    
    def test_format_validation_on_initialization(self):
        """Test that audio format is validated during provider initialization."""
        # This should succeed
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key",
            sample_rate=24000,
            channels=1
        )
        
        provider = AssemblyAIProvider(config)
        assert provider.config.sample_rate == 24000
        assert provider.config.channels == 1


class TestConnectionPooling:
    """Test connection pooling behavior for STT providers."""
    
    @pytest.mark.asyncio
    async def test_connection_reuse_assemblyai(self):
        """Test that AssemblyAI connection can be reused for multiple streams."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        # Mock WebSocket connection
        mock_ws = make_mock_websocket([json.dumps({
            "message_type": "SessionBegins",
            "session_id": "test_session"
        })])
        
        async def mock_connect(*args, **kwargs):
            return mock_ws
        
        with patch('websockets.connect', side_effect=mock_connect) as mock_connect_fn:
            # Connect once
            await provider.connect()
            
            # Stream multiple audio frames
            for i in range(5):
                audio_data = bytes([i] * 100)
                await provider.stream_audio(audio_data)
            
            # Verify connection was established only once
            assert mock_connect_fn.call_count == 1
            
            # Verify all audio frames were sent
            assert mock_ws.send.call_count == 5
    
    @pytest.mark.asyncio
    async def test_connection_reuse_deepgram(self):
        """Test that Deepgram connection can be reused for multiple streams."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key"
        )
        
        provider = DeepgramProvider(config)
        
        # Mock WebSocket connection
        mock_ws = AsyncMock()
        
        async def mock_connect(*args, **kwargs):
            return mock_ws
        
        with patch('websockets.connect', side_effect=mock_connect) as mock_connect_fn:
            # Connect once
            await provider.connect()
            
            # Stream multiple audio frames
            for i in range(5):
                audio_data = bytes([i] * 100)
                await provider.stream_audio(audio_data)
            
            # Verify connection was established only once
            assert mock_connect_fn.call_count == 1
            
            # Verify all audio frames were sent
            assert mock_ws.send.call_count == 5
    
    @pytest.mark.asyncio
    async def test_no_duplicate_connection(self):
        """Test that calling connect() multiple times doesn't create duplicate connections."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        # Mock WebSocket connection
        mock_ws = make_mock_websocket([json.dumps({
            "message_type": "SessionBegins",
            "session_id": "test_session"
        })])
        
        async def mock_connect(*args, **kwargs):
            return mock_ws
        
        with patch('websockets.connect', side_effect=mock_connect) as mock_connect_fn:
            # Call connect multiple times
            await provider.connect()
            await provider.connect()
            await provider.connect()
            
            # Verify connection was established only once
            assert mock_connect_fn.call_count == 1


class TestErrorHandling:
    """Test error handling for various failure scenarios."""
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_assemblyai(self):
        """Test handling of invalid API key for AssemblyAI."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="invalid_key_12345"
        )
        
        provider = AssemblyAIProvider(config)
        
        # Mock 401 Unauthorized response
        async def unauthorized(*args, **kwargs):
            raise websockets.exceptions.InvalidStatusCode(401, {})
        
        with patch('websockets.connect', side_effect=unauthorized):
            with pytest.raises(ConnectionError, match="failed"):
                await provider.connect()
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_deepgram(self):
        """Test handling of invalid API key for Deepgram."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="invalid_key_12345"
        )
        
        provider = DeepgramProvider(config)
        
        # Mock 401 Unauthorized response
        async def unauthorized(*args, **kwargs):
            raise websockets.exceptions.InvalidStatusCode(401, {})
        
        with patch('websockets.connect', side_effect=unauthorized):
            with pytest.raises(ConnectionError, match="failed"):
                await provider.connect()
    
    @pytest.mark.asyncio
    async def test_network_error_during_connection(self):
        """Test handling of network errors during connection."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        # Mock network error
        async def network_error(*args, **kwargs):
            raise OSError("Network unreachable")
        
        with patch('websockets.connect', side_effect=network_error):
            with pytest.raises(ConnectionError, match="Connection failed"):
                await provider.connect()
    
    @pytest.mark.asyncio
    async def test_websocket_close_during_streaming(self):
        """Test handling of WebSocket closure during audio streaming."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        # Mock connected state with WebSocket that closes
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock(
            side_effect=websockets.exceptions.ConnectionClosedError(None, None)
        )
        provider._websocket = mock_ws
        provider._connected = True
        
        with pytest.raises(RuntimeError, match="Audio streaming failed"):
            await provider.stream_audio(b"audio_data")
        
        # Verify connection state updated
        assert provider._connected is False
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """Test handling of API rate limit errors."""
        config = STTProviderConfig(
            provider_type="deepgram",
            api_key="test_key"
        )
        
        provider = DeepgramProvider(config)
        
        # Mock 429 Too Many Requests response
        async def rate_limited(*args, **kwargs):
            raise websockets.exceptions.InvalidStatusCode(429, {})
        
        with patch('websockets.connect', side_effect=rate_limited):
            with pytest.raises(ConnectionError, match="failed"):
                await provider.connect()
    
    @pytest.mark.asyncio
    async def test_malformed_response_handling(self):
        """Test handling of malformed JSON responses."""
        config = STTProviderConfig(
            provider_type="assemblyai",
            api_key="test_key"
        )
        
        provider = AssemblyAIProvider(config)
        
        # Mock WebSocket with malformed response
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(return_value="not valid json{{{")
        
        with patch('websockets.connect', return_value=mock_ws):
            with pytest.raises(ConnectionError):
                await provider.connect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
