"""
Unit tests for configuration models.

Tests Pydantic validation, field validators, and configuration structure.
"""

import pytest
from pathlib import Path
from pydantic import ValidationError

from config.models import (
    AliceConfig,
    LLMConfig,
    VoiceConfig,
    LiveKitConfig,
    VADConfig,
    MemoryConfig,
    SkillsConfig,
    ToolsConfig,
    GatewayConfig,
    CronConfig,
    SecurityConfig,
    PersonalityConfig,
    APIKeyConfig,
    TelegramConfig,
    DiscordConfig,
    validate_config_file,
    get_default_config,
)


class TestAPIKeyConfig:
    """Tests for APIKeyConfig model."""
    
    def test_valid_api_key(self):
        """Test valid API key configuration."""
        config = APIKeyConfig(key="test_key_123", rate_limit="100/min")
        assert config.key == "test_key_123"
        assert config.rate_limit == "100/min"
    
    def test_empty_key_raises_error(self):
        """Test that empty API key raises validation error."""
        with pytest.raises(ValidationError):
            APIKeyConfig(key="")
    
    def test_invalid_rate_limit_format(self):
        """Test that invalid rate limit format raises error."""
        with pytest.raises(ValidationError):
            APIKeyConfig(key="test_key", rate_limit="invalid")
    
    def test_valid_rate_limit_formats(self):
        """Test various valid rate limit formats."""
        valid_formats = ["100/min", "1000/hour", "10000/day"]
        for rate_limit in valid_formats:
            config = APIKeyConfig(key="test_key", rate_limit=rate_limit)
            assert config.rate_limit == rate_limit


class TestLLMConfig:
    """Tests for LLMConfig model."""
    
    def test_valid_llm_config(self):
        """Test valid LLM configuration."""
        config = LLMConfig(
            provider="openrouter",
            model="anthropic/claude-3.5-sonnet"
        )
        assert config.provider == "openrouter"
        assert config.model == "anthropic/claude-3.5-sonnet"
        assert config.max_retries == 3  # default
    
    def test_invalid_provider(self):
        """Test that invalid provider raises error."""
        with pytest.raises(ValidationError):
            LLMConfig(provider="invalid_provider", model="test")
    
    def test_compression_threshold_validation(self):
        """Test compression threshold validation."""
        # Valid threshold
        config = LLMConfig(
            provider="openrouter",
            model="test",
            compression_threshold=0.5
        )
        assert config.compression_threshold == 0.5
        
        # Invalid threshold (out of range)
        with pytest.raises(ValidationError):
            LLMConfig(
                provider="openrouter",
                model="test",
                compression_threshold=1.5
            )
    
    def test_compression_target_less_than_threshold(self):
        """Test that compression_target must be less than threshold."""
        with pytest.raises(ValidationError):
            LLMConfig(
                provider="openrouter",
                model="test",
                compression_threshold=0.3,
                compression_target=0.5
            )
    
    def test_context_window_auto(self):
        """Test context window with 'auto' value."""
        config = LLMConfig(
            provider="openrouter",
            model="test",
            context_window="auto"
        )
        assert config.context_window == "auto"
    
    def test_context_window_numeric(self):
        """Test context window with numeric value."""
        config = LLMConfig(
            provider="openrouter",
            model="test",
            context_window=128000
        )
        assert config.context_window == 128000


class TestVADConfig:
    """Tests for VADConfig model."""
    
    def test_valid_vad_config(self):
        """Test valid VAD configuration."""
        config = VADConfig(
            enabled=True,
            provider="silero",
            threshold=0.5,
            silence_duration_ms=400
        )
        assert config.enabled is True
        assert config.provider == "silero"
        assert config.threshold == 0.5
    
    def test_threshold_range_validation(self):
        """Test threshold must be between 0 and 1."""
        with pytest.raises(ValidationError):
            VADConfig(threshold=1.5)
        
        with pytest.raises(ValidationError):
            VADConfig(threshold=-0.1)


class TestLiveKitConfig:
    """Tests for LiveKitConfig model."""
    
    def test_valid_livekit_config(self):
        """Test valid LiveKit configuration."""
        config = LiveKitConfig(
            url="wss://test.livekit.cloud",
            api_key="test_key",
            api_secret="test_secret"
        )
        assert config.url == "wss://test.livekit.cloud"
        assert config.api_key == "test_key"
    
    def test_invalid_url_format(self):
        """Test that invalid URL format raises error."""
        with pytest.raises(ValidationError):
            LiveKitConfig(
                url="http://invalid.com",
                api_key="key",
                api_secret="secret"
            )
    
    def test_empty_credentials(self):
        """Test that empty credentials raise error."""
        with pytest.raises(ValidationError):
            LiveKitConfig(
                url="wss://test.livekit.cloud",
                api_key="",
                api_secret="secret"
            )


class TestVoiceConfig:
    """Tests for VoiceConfig model."""
    
    def test_valid_voice_config(self):
        """Test valid voice configuration."""
        config = VoiceConfig(
            model="gemini-2.0-flash-exp",
            livekit=LiveKitConfig(
                url="wss://test.livekit.cloud",
                api_key="key",
                api_secret="secret"
            )
        )
        assert config.provider == "gemini-realtime"
        assert config.model == "gemini-2.0-flash-exp"


class TestMemoryConfig:
    """Tests for MemoryConfig model."""
    
    def test_valid_memory_config(self):
        """Test valid memory configuration."""
        config = MemoryConfig(provider="builtin")
        assert config.provider == "builtin"
        assert config.builtin_memory_file == "MEMORY.md"
    
    def test_invalid_provider(self):
        """Test that invalid provider raises error."""
        with pytest.raises(ValidationError):
            MemoryConfig(provider="invalid_provider")


class TestSkillsConfig:
    """Tests for SkillsConfig model."""
    
    def test_valid_skills_config(self):
        """Test valid skills configuration."""
        config = SkillsConfig(enabled=True, auto_create=True)
        assert config.enabled is True
        assert config.skills_dir == "skills"
    
    def test_skills_hub_url_validation(self):
        """Test Skills Hub URL validation."""
        with pytest.raises(ValidationError):
            SkillsConfig(skills_hub_url="invalid_url")


class TestSecurityConfig:
    """Tests for SecurityConfig model."""
    
    def test_valid_security_config(self):
        """Test valid security configuration."""
        config = SecurityConfig(
            approval_enabled=True,
            risk_threshold=0.7
        )
        assert config.approval_enabled is True
        assert config.risk_threshold == 0.7
    
    def test_risk_threshold_range(self):
        """Test risk threshold must be between 0 and 1."""
        with pytest.raises(ValidationError):
            SecurityConfig(risk_threshold=1.5)


class TestPersonalityConfig:
    """Tests for PersonalityConfig model."""
    
    def test_valid_personality_config(self):
        """Test valid personality configuration."""
        config = PersonalityConfig(
            language="hinglish",
            tone="warm"
        )
        assert config.language == "hinglish"
        assert config.tone == "warm"
    
    def test_invalid_language(self):
        """Test that invalid language raises error."""
        with pytest.raises(ValidationError):
            PersonalityConfig(language="invalid")
    
    def test_invalid_tone(self):
        """Test that invalid tone raises error."""
        with pytest.raises(ValidationError):
            PersonalityConfig(tone="invalid")


class TestAliceConfig:
    """Tests for main AliceConfig model."""
    
    def test_valid_alice_config(self):
        """Test valid ALICE configuration."""
        config = AliceConfig(
            version=1,
            alice_home=Path("/tmp/alice"),
            llm=LLMConfig(provider="openrouter", model="test"),
            voice=VoiceConfig(
                model="gemini-2.0-flash-exp",
                livekit=LiveKitConfig(
                    url="wss://test.livekit.cloud",
                    api_key="key",
                    api_secret="secret"
                )
            )
        )
        assert config.version == 1
        assert isinstance(config.alice_home, Path)
    
    def test_alice_home_path_expansion(self):
        """Test that alice_home path is expanded."""
        config = AliceConfig(
            version=1,
            alice_home="~/alice",
            llm=LLMConfig(provider="openrouter", model="test"),
            voice=VoiceConfig(
                model="gemini-2.0-flash-exp",
                livekit=LiveKitConfig(
                    url="wss://test.livekit.cloud",
                    api_key="key",
                    api_secret="secret"
                )
            )
        )
        assert config.alice_home.is_absolute()
    
    def test_invalid_version(self):
        """Test that invalid version raises error."""
        with pytest.raises(ValidationError):
            AliceConfig(
                version=0,
                alice_home=Path("/tmp/alice"),
                llm=LLMConfig(provider="openrouter", model="test"),
                voice=VoiceConfig(
                    model="gemini-2.0-flash-exp",
                    livekit=LiveKitConfig(
                        url="wss://test.livekit.cloud",
                        api_key="key",
                        api_secret="secret"
                    )
                )
            )


class TestConfigHelpers:
    """Tests for configuration helper functions."""
    
    def test_get_default_config(self):
        """Test default configuration generation."""
        config = get_default_config(Path("/tmp/alice"))
        assert isinstance(config, AliceConfig)
        assert config.version == 1
        # Path gets resolved to absolute, so just check it's a Path
        assert isinstance(config.alice_home, Path)
    
    def test_validate_config_file(self):
        """Test configuration file validation."""
        config_dict = {
            "version": 1,
            "alice_home": "/tmp/alice",
            "llm": {
                "provider": "openrouter",
                "model": "test"
            },
            "voice": {
                "model": "gemini-2.0-flash-exp",
                "livekit": {
                    "url": "wss://test.livekit.cloud",
                    "api_key": "key",
                    "api_secret": "secret"
                }
            }
        }
        config = validate_config_file(config_dict)
        assert isinstance(config, AliceConfig)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
