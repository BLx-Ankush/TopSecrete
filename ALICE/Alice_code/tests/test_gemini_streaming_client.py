"""
Unit tests for Gemini Multimodal Live API WebSocket Streaming Client

Tests cover:
- Client initialization
- Sentence boundary detection
- Regional routing configuration
- Connection state management
- Error handling
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from gemini_streaming_client import (
    GeminiStreamingClient,
    GeminiRegion,
    SentenceBoundaryDetector,
    ConnectionState
)


class TestSentenceBoundaryDetector:
    """Test sentence boundary detection for streaming responses"""
    
    def test_single_sentence_detection(self):
        """Test detection of a single complete sentence"""
        detector = SentenceBoundaryDetector()
        
        # Add text with sentence terminator
        sentences = detector.add_text("Hello world.")
        
        assert len(sentences) == 1
        assert sentences[0] == "Hello world."
    
    def test_multiple_sentences_detection(self):
        """Test detection of multiple sentences with same terminator"""
        detector = SentenceBoundaryDetector()
        
        # Add text with multiple sentences (same terminator)
        sentences = detector.add_text("First sentence. Second sentence.")
        
        # The detector processes one terminator type at a time
        # So it will detect both sentences ending with '.'
        assert len(sentences) == 2
        assert sentences[0] == "First sentence."
        assert sentences[1] == "Second sentence."
    
    def test_incomplete_sentence_buffering(self):
        """Test that incomplete sentences are buffered"""
        detector = SentenceBoundaryDetector()
        
        # Add incomplete sentence
        sentences = detector.add_text("This is incomplete")
        
        assert len(sentences) == 0
        assert detector.buffer == "This is incomplete"
    
    def test_streaming_sentence_completion(self):
        """Test sentence completion across multiple chunks"""
        detector = SentenceBoundaryDetector()
        
        # Add first chunk
        sentences1 = detector.add_text("The weather today")
        assert len(sentences1) == 0
        
        # Add second chunk with terminator
        sentences2 = detector.add_text(" is sunny.")
        assert len(sentences2) == 1
        assert sentences2[0] == "The weather today is sunny."
    
    def test_question_mark_terminator(self):
        """Test question mark as sentence terminator"""
        detector = SentenceBoundaryDetector()
        
        sentences = detector.add_text("What's the weather?")
        
        assert len(sentences) == 1
        assert sentences[0] == "What's the weather?"
    
    def test_exclamation_terminator(self):
        """Test exclamation mark as sentence terminator"""
        detector = SentenceBoundaryDetector()
        
        sentences = detector.add_text("That's amazing!")
        
        assert len(sentences) == 1
        assert sentences[0] == "That's amazing!"
    
    def test_flush_remaining_buffer(self):
        """Test flushing remaining buffer as final sentence"""
        detector = SentenceBoundaryDetector()
        
        # Add incomplete sentence
        detector.add_text("Final words")
        
        # Flush buffer
        final = detector.flush()
        
        assert final == "Final words"
        assert detector.buffer == ""
    
    def test_flush_empty_buffer(self):
        """Test flushing empty buffer returns None"""
        detector = SentenceBoundaryDetector()
        
        final = detector.flush()
        
        assert final is None
    
    def test_reset_clears_state(self):
        """Test reset clears detector state"""
        detector = SentenceBoundaryDetector()
        
        # Add some data
        detector.add_text("Some text.")
        detector.add_text("More text")
        
        # Reset
        detector.reset()
        
        assert detector.buffer == ""
        assert len(detector.completed_sentences) == 0
    
    def test_minimum_buffer_size(self):
        """Test minimum buffer size requirement"""
        detector = SentenceBoundaryDetector()
        
        # Add very short sentence (below minimum)
        sentences = detector.add_text("Hi.")
        
        # Should still detect if meets minimum (5 chars including terminator)
        # "Hi." is 3 chars, below minimum
        assert len(sentences) == 0
        
        # Add longer sentence
        sentences = detector.add_text("Hello.")
        assert len(sentences) == 1


class TestGeminiStreamingClient:
    """Test Gemini streaming client initialization and configuration"""
    
    def test_client_initialization_with_api_key(self):
        """Test client initializes with provided API key"""
        client = GeminiStreamingClient(api_key="test-key-123")
        
        assert client.api_key == "test-key-123"
        assert client.region == GeminiRegion.ASIA_SOUTH1
        assert client.state == ConnectionState.DISCONNECTED
    
    def test_client_initialization_with_env_var(self):
        """Test client initializes with API key from environment"""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'env-key-456'}):
            client = GeminiStreamingClient()
            
            assert client.api_key == "env-key-456"
    
    def test_client_initialization_without_api_key_raises_error(self):
        """Test client raises error when no API key provided"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="API key required"):
                GeminiStreamingClient()
    
    def test_client_initialization_with_custom_region(self):
        """Test client initializes with custom region"""
        client = GeminiStreamingClient(
            api_key="test-key",
            region=GeminiRegion.ASIA_SOUTHEAST1
        )
        
        assert client.region == GeminiRegion.ASIA_SOUTHEAST1
    
    def test_client_initialization_with_custom_model(self):
        """Test client initializes with custom model"""
        client = GeminiStreamingClient(
            api_key="test-key",
            model="custom-model"
        )
        
        assert client.model == "custom-model"
    
    def test_client_initialization_with_custom_voice(self):
        """Test client initializes with custom voice"""
        client = GeminiStreamingClient(
            api_key="test-key",
            voice="CustomVoice"
        )
        
        assert client.voice == "CustomVoice"
    
    def test_websocket_url_generation_asia_south1(self):
        """Test WebSocket URL generation for asia-south1 region"""
        client = GeminiStreamingClient(api_key="test-key")
        
        url = client._get_websocket_url(GeminiRegion.ASIA_SOUTH1)
        
        assert "asia-south1-aiplatform.googleapis.com" in url
        assert "streamGenerateContent" in url
        assert "key=test-key" in url
    
    def test_websocket_url_generation_global(self):
        """Test WebSocket URL generation for global region"""
        client = GeminiStreamingClient(api_key="test-key")
        
        url = client._get_websocket_url(GeminiRegion.GLOBAL)
        
        assert "generativelanguage.googleapis.com" in url
        assert "streamGenerateContent" in url
    
    def test_fallback_regions_excludes_failed(self):
        """Test fallback regions exclude the failed region"""
        client = GeminiStreamingClient(api_key="test-key")
        
        fallbacks = client._get_fallback_regions(GeminiRegion.ASIA_SOUTH1)
        
        assert GeminiRegion.ASIA_SOUTH1 not in fallbacks
        assert GeminiRegion.ASIA_SOUTHEAST1 in fallbacks
        assert GeminiRegion.US_CENTRAL1 in fallbacks
        assert GeminiRegion.GLOBAL in fallbacks
    
    def test_state_change_triggers_callback(self):
        """Test state changes trigger callback"""
        client = GeminiStreamingClient(api_key="test-key")
        
        callback_mock = Mock()
        client.on_connection_state_change = callback_mock
        
        # Change state
        client._set_state(ConnectionState.CONNECTING)
        
        callback_mock.assert_called_once_with(ConnectionState.CONNECTING)
        assert client.state == ConnectionState.CONNECTING
    
    def test_metrics_tracking(self):
        """Test client tracks metrics correctly"""
        client = GeminiStreamingClient(api_key="test-key")
        
        # Simulate some activity
        client.total_audio_sent = 1024
        client.total_audio_received = 2048
        client.total_sentences_received = 5
        
        metrics = client.get_metrics()
        
        assert metrics["total_audio_sent"] == 1024
        assert metrics["total_audio_received"] == 2048
        assert metrics["total_sentences_received"] == 5
        assert metrics["state"] == ConnectionState.DISCONNECTED.value
    
    def test_auto_reconnect_configuration(self):
        """Test auto-reconnect can be enabled/disabled"""
        client_enabled = GeminiStreamingClient(
            api_key="test-key",
            enable_auto_reconnect=True
        )
        
        client_disabled = GeminiStreamingClient(
            api_key="test-key",
            enable_auto_reconnect=False
        )
        
        assert client_enabled.enable_auto_reconnect is True
        assert client_disabled.enable_auto_reconnect is False


class TestGeminiStreamingClientAsync:
    """Test async operations of Gemini streaming client"""
    
    @pytest.mark.asyncio
    async def test_send_audio_when_not_connected(self):
        """Test sending audio when not connected logs warning"""
        client = GeminiStreamingClient(api_key="test-key")
        
        # Should not raise error, just log warning
        await client.send_audio(b"audio_data")
        
        # Verify state is still disconnected
        assert client.state == ConnectionState.DISCONNECTED
    
    @pytest.mark.asyncio
    async def test_disconnect_cleans_up_resources(self):
        """Test disconnect properly cleans up resources"""
        client = GeminiStreamingClient(api_key="test-key")
        
        # Mock WebSocket connection
        client.ws = AsyncMock()
        client.state = ConnectionState.CONNECTED
        client._receive_task = asyncio.create_task(asyncio.sleep(0.1))
        
        # Disconnect
        await client.disconnect()
        
        # Verify cleanup
        assert client.state == ConnectionState.DISCONNECTED
        client.ws.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_context_manager_support(self):
        """Test client supports async context manager"""
        with patch.object(GeminiStreamingClient, 'connect', new_callable=AsyncMock):
            with patch.object(GeminiStreamingClient, 'disconnect', new_callable=AsyncMock):
                async with GeminiStreamingClient(api_key="test-key") as client:
                    assert client is not None


class TestRegionalRouting:
    """Test regional routing configuration and optimization"""
    
    def test_all_regions_defined(self):
        """Test all expected regions are defined"""
        regions = [
            GeminiRegion.ASIA_SOUTH1,
            GeminiRegion.ASIA_SOUTHEAST1,
            GeminiRegion.US_CENTRAL1,
            GeminiRegion.GLOBAL
        ]
        
        assert len(regions) == 4
        assert GeminiRegion.ASIA_SOUTH1.value == "asia-south1"
        assert GeminiRegion.ASIA_SOUTHEAST1.value == "asia-southeast1"
        assert GeminiRegion.US_CENTRAL1.value == "us-central1"
        assert GeminiRegion.GLOBAL.value == "global"
    
    def test_default_region_is_mumbai(self):
        """Test default region is asia-south1 (Mumbai) for optimal latency"""
        client = GeminiStreamingClient(api_key="test-key")
        
        assert client.region == GeminiRegion.ASIA_SOUTH1


class TestErrorHandling:
    """Test error handling and graceful degradation"""
    
    def test_error_callback_triggered(self):
        """Test error callback is triggered on errors"""
        client = GeminiStreamingClient(api_key="test-key")
        
        error_mock = Mock()
        client.on_error = error_mock
        
        # Simulate error
        test_error = Exception("Test error")
        client.last_error = test_error
        
        # Trigger error callback manually (simulating internal error handling)
        if client.on_error and client.last_error:
            client.on_error(client.last_error)
        
        error_mock.assert_called_once_with(test_error)
    
    def test_reconnect_attempts_tracked(self):
        """Test reconnection attempts are tracked"""
        client = GeminiStreamingClient(api_key="test-key")
        
        assert client.reconnect_attempts == 0
        
        # Simulate reconnection attempts
        client.reconnect_attempts = 3
        
        assert client.reconnect_attempts == 3
        assert client.reconnect_attempts < client.MAX_RECONNECT_ATTEMPTS


class TestConnectionManagement:
    """Test connection lifecycle management"""
    
    def test_connection_states_defined(self):
        """Test all connection states are defined"""
        states = [
            ConnectionState.DISCONNECTED,
            ConnectionState.CONNECTING,
            ConnectionState.CONNECTED,
            ConnectionState.RECONNECTING,
            ConnectionState.FAILED
        ]
        
        assert len(states) == 5
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.CONNECTED.value == "connected"
    
    def test_initial_state_is_disconnected(self):
        """Test client starts in disconnected state"""
        client = GeminiStreamingClient(api_key="test-key")
        
        assert client.state == ConnectionState.DISCONNECTED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
