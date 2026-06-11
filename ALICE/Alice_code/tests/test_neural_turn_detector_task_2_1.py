"""
Unit tests for NeuralTurnDetector class initialization (Task 2.1).

This test file verifies that Task 2.1 requirements are met:
- Constructor with configurable thresholds (confidence, min/max silence)
- Initialize STT provider client
- Set up fallback to Silero VAD
- Add configuration validation

Requirements: 1.1, 1.2, 1.3, 1.4, 15.4, 15.5, 15.6, 15.8, 15.9
"""

import pytest
from unittest.mock import Mock, AsyncMock
from turn_detection import NeuralTurnDetector
from stt.models import STTProviderConfig


class MockSTTProvider:
    """Mock STT provider for testing."""
    
    def __init__(self, provider_type: str = "assemblyai"):
        self.provider_type = provider_type
        self.connected = False
    
    def get_provider_type(self) -> str:
        return self.provider_type
    
    async def connect(self):
        self.connected = True
    
    async def disconnect(self):
        self.connected = False
    
    async def is_connected(self) -> bool:
        return self.connected
    
    async def stream_audio(self, audio_frame: bytes):
        pass
    
    async def get_transcription_result(self):
        return None


class TestNeuralTurnDetectorInitialization:
    """Test NeuralTurnDetector initialization (Task 2.1)."""
    
    def test_initialization_with_default_parameters(self):
        """Test initialization with default parameters."""
        # Arrange
        stt_provider = MockSTTProvider()
        
        # Act
        detector = NeuralTurnDetector(stt_provider=stt_provider)
        
        # Assert
        assert detector.stt_provider == stt_provider
        assert detector.confidence_threshold == 0.4
        assert detector.min_turn_silence_ms == 300
        assert detector.max_turn_silence_ms == 1200
        assert detector.fallback_vad is None
    
    def test_initialization_with_custom_parameters(self):
        """Test initialization with custom parameters."""
        # Arrange
        stt_provider = MockSTTProvider()
        fallback_vad = Mock()
        
        # Act
        detector = NeuralTurnDetector(
            stt_provider=stt_provider,
            confidence_threshold=0.5,
            min_turn_silence_ms=400,
            max_turn_silence_ms=1500,
            fallback_vad=fallback_vad
        )
        
        # Assert
        assert detector.stt_provider == stt_provider
        assert detector.confidence_threshold == 0.5
        assert detector.min_turn_silence_ms == 400
        assert detector.max_turn_silence_ms == 1500
        assert detector.fallback_vad == fallback_vad
    
    def test_initialization_with_assemblyai_provider(self):
        """Test initialization with AssemblyAI provider."""
        # Arrange
        stt_provider = MockSTTProvider(provider_type="assemblyai")
        
        # Act
        detector = NeuralTurnDetector(stt_provider=stt_provider)
        
        # Assert
        assert detector.stt_provider.get_provider_type() == "assemblyai"
    
    def test_initialization_with_deepgram_provider(self):
        """Test initialization with Deepgram provider."""
        # Arrange
        stt_provider = MockSTTProvider(provider_type="deepgram")
        
        # Act
        detector = NeuralTurnDetector(stt_provider=stt_provider)
        
        # Assert
        assert detector.stt_provider.get_provider_type() == "deepgram"
    
    def test_initialization_with_fallback_vad(self):
        """Test initialization with fallback VAD."""
        # Arrange
        stt_provider = MockSTTProvider()
        fallback_vad = Mock()
        
        # Act
        detector = NeuralTurnDetector(
            stt_provider=stt_provider,
            fallback_vad=fallback_vad
        )
        
        # Assert
        assert detector.fallback_vad == fallback_vad
        assert not detector.is_fallback_mode()
    
    def test_configuration_validation_invalid_confidence_threshold_too_low(self):
        """Test configuration validation rejects confidence threshold < 0.0."""
        # Arrange
        stt_provider = MockSTTProvider()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Confidence threshold must be between 0.0 and 1.0"):
            NeuralTurnDetector(
                stt_provider=stt_provider,
                confidence_threshold=-0.1
            )
    
    def test_configuration_validation_invalid_confidence_threshold_too_high(self):
        """Test configuration validation rejects confidence threshold > 1.0."""
        # Arrange
        stt_provider = MockSTTProvider()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Confidence threshold must be between 0.0 and 1.0"):
            NeuralTurnDetector(
                stt_provider=stt_provider,
                confidence_threshold=1.5
            )
    
    def test_configuration_validation_invalid_min_silence_negative(self):
        """Test configuration validation rejects negative min silence."""
        # Arrange
        stt_provider = MockSTTProvider()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Minimum turn silence must be positive"):
            NeuralTurnDetector(
                stt_provider=stt_provider,
                min_turn_silence_ms=-100
            )
    
    def test_configuration_validation_invalid_min_silence_zero(self):
        """Test configuration validation rejects zero min silence."""
        # Arrange
        stt_provider = MockSTTProvider()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Minimum turn silence must be positive"):
            NeuralTurnDetector(
                stt_provider=stt_provider,
                min_turn_silence_ms=0
            )
    
    def test_configuration_validation_invalid_max_silence_negative(self):
        """Test configuration validation rejects negative max silence."""
        # Arrange
        stt_provider = MockSTTProvider()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Maximum turn silence must be positive"):
            NeuralTurnDetector(
                stt_provider=stt_provider,
                max_turn_silence_ms=-100
            )
    
    def test_configuration_validation_invalid_max_silence_zero(self):
        """Test configuration validation rejects zero max silence."""
        # Arrange
        stt_provider = MockSTTProvider()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Maximum turn silence must be positive"):
            NeuralTurnDetector(
                stt_provider=stt_provider,
                max_turn_silence_ms=0
            )
    
    def test_configuration_validation_max_silence_less_than_min_silence(self):
        """Test configuration validation rejects max silence <= min silence."""
        # Arrange
        stt_provider = MockSTTProvider()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Maximum turn silence .* must be greater than"):
            NeuralTurnDetector(
                stt_provider=stt_provider,
                min_turn_silence_ms=500,
                max_turn_silence_ms=400
            )
    
    def test_configuration_validation_max_silence_equal_to_min_silence(self):
        """Test configuration validation rejects max silence == min silence."""
        # Arrange
        stt_provider = MockSTTProvider()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Maximum turn silence .* must be greater than"):
            NeuralTurnDetector(
                stt_provider=stt_provider,
                min_turn_silence_ms=500,
                max_turn_silence_ms=500
            )
    
    def test_configuration_validation_valid_boundary_values(self):
        """Test configuration validation accepts valid boundary values."""
        # Arrange
        stt_provider = MockSTTProvider()
        
        # Act - Test minimum valid values
        detector1 = NeuralTurnDetector(
            stt_provider=stt_provider,
            confidence_threshold=0.0,
            min_turn_silence_ms=1,
            max_turn_silence_ms=2
        )
        
        # Act - Test maximum valid values
        detector2 = NeuralTurnDetector(
            stt_provider=stt_provider,
            confidence_threshold=1.0,
            min_turn_silence_ms=1000,
            max_turn_silence_ms=5000
        )
        
        # Assert
        assert detector1.confidence_threshold == 0.0
        assert detector1.min_turn_silence_ms == 1
        assert detector1.max_turn_silence_ms == 2
        
        assert detector2.confidence_threshold == 1.0
        assert detector2.min_turn_silence_ms == 1000
        assert detector2.max_turn_silence_ms == 5000
    
    def test_initial_state_after_initialization(self):
        """Test that detector has correct initial state after initialization."""
        # Arrange
        stt_provider = MockSTTProvider()
        
        # Act
        detector = NeuralTurnDetector(stt_provider=stt_provider)
        
        # Assert - Check internal state
        assert detector._current_confidence == 0.0
        assert detector._last_transcription is None
        assert detector._audio_start_time_ms is None
        assert detector._last_audio_time_ms is None
        assert detector._silence_start_time_ms is None
        assert detector._is_fallback_mode is False
        assert detector._consecutive_failures == 0
    
    def test_get_detector_type_neural_mode(self):
        """Test get_detector_type returns 'neural' in normal mode."""
        # Arrange
        stt_provider = MockSTTProvider()
        detector = NeuralTurnDetector(stt_provider=stt_provider)
        
        # Act
        detector_type = detector.get_detector_type()
        
        # Assert
        assert detector_type == "neural"
    
    def test_is_fallback_mode_initially_false(self):
        """Test is_fallback_mode returns False initially."""
        # Arrange
        stt_provider = MockSTTProvider()
        detector = NeuralTurnDetector(stt_provider=stt_provider)
        
        # Act
        is_fallback = detector.is_fallback_mode()
        
        # Assert
        assert is_fallback is False
    
    def test_get_audio_duration_ms_initially_zero(self):
        """Test get_audio_duration_ms returns 0 initially."""
        # Arrange
        stt_provider = MockSTTProvider()
        detector = NeuralTurnDetector(stt_provider=stt_provider)
        
        # Act
        duration = detector.get_audio_duration_ms()
        
        # Assert
        assert duration == 0
    
    def test_get_silence_duration_ms_initially_zero(self):
        """Test get_silence_duration_ms returns 0 initially."""
        # Arrange
        stt_provider = MockSTTProvider()
        detector = NeuralTurnDetector(stt_provider=stt_provider)
        
        # Act
        duration = detector.get_silence_duration_ms()
        
        # Assert
        assert duration == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
