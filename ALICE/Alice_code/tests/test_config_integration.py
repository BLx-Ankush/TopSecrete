"""
Integration tests for the configuration system.

Tests the complete configuration system including models, manager,
YAML loading, environment variable handling, and validation.
"""

import pytest
import os
import yaml
import tempfile
from pathlib import Path
from unittest.mock import patch

from config import (
    ConfigManager,
    AliceConfig,
    load_config,
    ConfigValidationError,
    ConfigLoadError,
)


@pytest.fixture
def complete_alice_env(tmp_path):
    """Create complete ALICE environment with all files."""
    # Create directory structure
    alice_home = tmp_path / "data"
    alice_home.mkdir()
    
    # Create subdirectories
    (alice_home / "skills").mkdir()
    (alice_home / "optional-skills").mkdir()
    (alice_home / "cron").mkdir()
    (alice_home / "logs").mkdir()
    (alice_home / "memory").mkdir()
    (alice_home / "sessions").mkdir()
    (alice_home / "plugins").mkdir()
    
    # Create placeholder files
    (alice_home / "MEMORY.md").write_text("# Memory\n\nNo memories yet.")
    (alice_home / "USER.md").write_text("# User Profile\n\nNo profile yet.")
    (alice_home / "SOUL.md").write_text("# ALICE Personality\n\nWarm and supportive.")
    
    # Create .env file
    env_file = tmp_path / ".env"
    env_content = """
# LiveKit Configuration
LIVEKIT_URL=wss://test.livekit.cloud
LIVEKIT_API_KEY=test_livekit_key_123
LIVEKIT_API_SECRET=test_livekit_secret_456

# Google Gemini API
GOOGLE_API_KEY=test_google_key_789

# Optional providers
OPENROUTER_API_KEY=test_openrouter_key
ANTHROPIC_API_KEY=test_anthropic_key
MEM0_API_KEY=test_mem0_key
"""
    env_file.write_text(env_content.strip())
    
    # Create config.yaml
    config_file = alice_home / "config.yaml"
    config_content = {
        "version": 1,
        "llm": {
            "provider": "openrouter",
            "model": "anthropic/claude-3.5-sonnet",
            "fallback_providers": ["google"],
            "max_retries": 3,
            "context_window": 128000,
        },
        "voice": {
            "provider": "gemini-realtime",
            "model": "gemini-2.0-flash-exp",
            "livekit": {
                "url": "${LIVEKIT_URL}",
                "api_key": "${LIVEKIT_API_KEY}",
                "api_secret": "${LIVEKIT_API_SECRET}",
            },
            "vad": {
                "enabled": True,
                "provider": "silero",
                "threshold": 0.5,
                "silence_duration_ms": 400,
            },
        },
        "memory": {
            "provider": "builtin",
        },
        "skills": {
            "enabled": True,
            "auto_create": True,
        },
        "personality": {
            "language": "hinglish",
            "tone": "warm",
        },
    }
    with open(config_file, 'w') as f:
        yaml.safe_dump(config_content, f)
    
    return {
        "alice_home": alice_home,
        "env_file": env_file,
        "config_file": config_file,
    }


class TestConfigurationIntegration:
    """Integration tests for complete configuration system."""
    
    def test_full_config_load_with_env_substitution(self, complete_alice_env):
        """Test complete configuration loading with environment substitution."""
        manager = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager.env_path = complete_alice_env["env_file"]
        
        # Load configuration
        config = manager.load()
        
        # Verify configuration loaded
        assert isinstance(config, AliceConfig)
        assert config.version == 1
        
        # Verify environment substitution worked
        assert config.voice.livekit.url == "wss://test.livekit.cloud"
        assert config.voice.livekit.api_key == "test_livekit_key_123"
        assert config.voice.livekit.api_secret == "test_livekit_secret_456"
        
        # Verify merged configuration
        assert config.llm.provider == "openrouter"
        assert config.llm.model == "anthropic/claude-3.5-sonnet"
        assert config.llm.fallback_providers == ["google"]
        
        # Verify defaults were applied
        assert config.llm.retry_delay == 1.0
        assert config.llm.exponential_backoff is True
    
    def test_config_with_partial_overrides(self, complete_alice_env):
        """Test configuration with partial user overrides."""
        # Modify config to only override some values
        config_file = complete_alice_env["config_file"]
        minimal_config = {
            "version": 1,
            "llm": {
                "model": "custom-model",
            },
        }
        with open(config_file, 'w') as f:
            yaml.safe_dump(minimal_config, f)
        
        manager = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager.env_path = complete_alice_env["env_file"]
        config = manager.load()
        
        # User override should be applied
        assert config.llm.model == "custom-model"
        
        # Defaults should still be present
        assert config.llm.provider == "openrouter"
        assert config.llm.max_retries == 3
    
    def test_config_validation_catches_errors(self, complete_alice_env):
        """Test that validation catches configuration errors."""
        # Create invalid config
        config_file = complete_alice_env["config_file"]
        invalid_config = {
            "version": 1,
            "llm": {
                "provider": "invalid_provider",  # Invalid
                "model": "test",
            },
        }
        with open(config_file, 'w') as f:
            yaml.safe_dump(invalid_config, f)
        
        manager = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager.env_path = complete_alice_env["env_file"]
        
        # Should raise ConfigLoadError (which wraps ConfigValidationError)
        with pytest.raises(ConfigLoadError) as exc_info:
            manager.load()
        
        # Error message should mention the invalid provider
        assert "provider" in str(exc_info.value).lower()
    
    def test_config_save_and_reload(self, complete_alice_env):
        """Test saving and reloading configuration."""
        manager = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager.env_path = complete_alice_env["env_file"]
        
        # Load initial config
        config = manager.load()
        original_model = config.llm.model
        
        # Modify and save
        config.llm.model = "modified-model"
        config.llm.max_retries = 5
        manager.save(config)
        
        # Create new manager and reload
        manager2 = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager2.env_path = complete_alice_env["env_file"]
        config2 = manager2.load()
        
        # Verify changes persisted
        assert config2.llm.model == "modified-model"
        assert config2.llm.max_retries == 5
        assert config2.llm.model != original_model
    
    def test_config_get_set_operations(self, complete_alice_env):
        """Test get and set operations on loaded config."""
        manager = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager.env_path = complete_alice_env["env_file"]
        manager.load()
        
        # Test get
        provider = manager.get("llm.provider")
        assert provider == "openrouter"
        
        model = manager.get("llm.model")
        assert model == "anthropic/claude-3.5-sonnet"
        
        # Test get with default
        missing = manager.get("nonexistent.key", "default_value")
        assert missing == "default_value"
        
        # Test set
        manager.set("llm.model", "new-model")
        assert manager.get("llm.model") == "new-model"
        
        # Test nested set
        manager.set("llm.max_retries", 10)
        assert manager.get("llm.max_retries") == 10
    
    def test_profile_isolation(self, tmp_path):
        """Test that profiles are isolated."""
        # Create two profiles
        default_home = tmp_path / "data"
        work_home = tmp_path / "data" / "profiles" / "work"
        
        for home in [default_home, work_home]:
            home.mkdir(parents=True, exist_ok=True)
            (home / "MEMORY.md").write_text("# Memory\n")
            (home / "USER.md").write_text("# User\n")
            (home / "SOUL.md").write_text("# Soul\n")
        
        # Create different configs
        default_config = {"version": 1, "llm": {"model": "default-model"}}
        work_config = {"version": 1, "llm": {"model": "work-model"}}
        
        with open(default_home / "config.yaml", 'w') as f:
            yaml.safe_dump(default_config, f)
        with open(work_home / "config.yaml", 'w') as f:
            yaml.safe_dump(work_config, f)
        
        # Create env file
        env_file = tmp_path / ".env"
        env_file.write_text("""
LIVEKIT_URL=wss://test.livekit.cloud
LIVEKIT_API_KEY=key
LIVEKIT_API_SECRET=secret
GOOGLE_API_KEY=key
""")
        
        # Load default profile
        manager1 = ConfigManager(profile="default", alice_home=default_home)
        manager1.env_path = env_file
        config1 = manager1.load()
        
        # Load work profile
        manager2 = ConfigManager(profile="work", alice_home=work_home)
        manager2.env_path = env_file
        config2 = manager2.load()
        
        # Verify isolation
        assert config1.llm.model == "default-model"
        assert config2.llm.model == "work-model"
    
    def test_missing_env_vars_handled_gracefully(self, complete_alice_env):
        """Test that missing environment variables are handled gracefully."""
        # Create config with env vars
        config_file = complete_alice_env["config_file"]
        config_with_missing = {
            "version": 1,
            "llm": {
                "provider": "openrouter",
                "model": "${MISSING_VAR}",  # This var doesn't exist
            },
        }
        with open(config_file, 'w') as f:
            yaml.safe_dump(config_with_missing, f)
        
        manager = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager.env_path = complete_alice_env["env_file"]
        
        # Should load but with empty string for missing var
        config = manager.load()
        assert config.llm.model == ""
    
    def test_deep_nested_config_merge(self, complete_alice_env):
        """Test deep nested configuration merging."""
        config_file = complete_alice_env["config_file"]
        
        # Create config with deeply nested overrides
        nested_config = {
            "version": 1,
            "llm": {
                "provider": "openrouter",
                "api_keys": {
                    "openrouter": [
                        {"key": "key1", "rate_limit": "100/min"},
                        {"key": "key2", "rate_limit": "200/min"},
                    ]
                },
            },
            "gateway": {
                "enabled": True,
                "telegram": {
                    "enabled": True,
                    "bot_token": "${TELEGRAM_BOT_TOKEN}",
                    "allowed_users": ["user1", "user2"],
                },
            },
        }
        with open(config_file, 'w') as f:
            yaml.safe_dump(nested_config, f)
        
        manager = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager.env_path = complete_alice_env["env_file"]
        config = manager.load()
        
        # Verify nested values
        assert config.gateway.enabled is True
        assert config.gateway.telegram.enabled is True
        assert len(config.gateway.telegram.allowed_users) == 2
        
        # Verify API keys structure
        assert len(config.llm.api_keys.get("openrouter", [])) == 2
    
    def test_config_validation_comprehensive(self, complete_alice_env):
        """Test comprehensive validation of all config sections."""
        manager = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager.env_path = complete_alice_env["env_file"]
        config = manager.load()
        
        # Verify all major sections exist
        assert hasattr(config, "llm")
        assert hasattr(config, "voice")
        assert hasattr(config, "memory")
        assert hasattr(config, "skills")
        assert hasattr(config, "tools")
        assert hasattr(config, "gateway")
        assert hasattr(config, "cron")
        assert hasattr(config, "security")
        assert hasattr(config, "personality")
        
        # Verify types
        assert isinstance(config.llm.max_retries, int)
        assert isinstance(config.llm.retry_delay, float)
        assert isinstance(config.llm.exponential_backoff, bool)
        assert isinstance(config.voice.vad.threshold, float)
        assert isinstance(config.security.approval_timeout, int)
    
    def test_env_var_validation(self, complete_alice_env):
        """Test environment variable validation."""
        manager = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager.env_path = complete_alice_env["env_file"]
        manager._load_env(complete_alice_env["env_file"])
        
        status = manager.validate_env_vars()
        
        # Required vars should be present
        assert status["LIVEKIT_URL"] is True
        assert status["LIVEKIT_API_KEY"] is True
        assert status["LIVEKIT_API_SECRET"] is True
        assert status["GOOGLE_API_KEY"] is True
        
        # Optional vars should be present (from our test env)
        assert status["OPENROUTER_API_KEY"] is True
        assert status["ANTHROPIC_API_KEY"] is True
        assert status["MEM0_API_KEY"] is True


class TestConfigurationEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_config_file(self, complete_alice_env):
        """Test loading with empty config file."""
        config_file = complete_alice_env["config_file"]
        config_file.write_text("")
        
        manager = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager.env_path = complete_alice_env["env_file"]
        
        # Should use all defaults
        config = manager.load()
        assert config.llm.provider == "openrouter"
    
    def test_malformed_yaml(self, complete_alice_env):
        """Test handling of malformed YAML."""
        config_file = complete_alice_env["config_file"]
        config_file.write_text("invalid: yaml: [unclosed")
        
        manager = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager.env_path = complete_alice_env["env_file"]
        
        with pytest.raises(ConfigLoadError):
            manager.load()
    
    def test_invalid_yaml_structure(self, complete_alice_env):
        """Test handling of invalid YAML structure."""
        config_file = complete_alice_env["config_file"]
        # Valid YAML but invalid structure (string instead of dict)
        config_file.write_text("just_a_string")
        
        manager = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager.env_path = complete_alice_env["env_file"]
        
        # Should raise ConfigLoadError due to invalid structure
        with pytest.raises(ConfigLoadError):
            manager.load()
    
    def test_config_with_extra_fields(self, complete_alice_env):
        """Test configuration with extra unknown fields."""
        config_file = complete_alice_env["config_file"]
        config_with_extra = {
            "version": 1,
            "llm": {
                "provider": "openrouter",
                "model": "test",
                "unknown_field": "should_be_ignored",
            },
            "unknown_section": {
                "field": "value",
            },
        }
        with open(config_file, 'w') as f:
            yaml.safe_dump(config_with_extra, f)
        
        manager = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager.env_path = complete_alice_env["env_file"]
        
        # Pydantic should ignore extra fields by default or raise error
        # depending on configuration
        try:
            config = manager.load()
            # If it loads, verify known fields are correct
            assert config.llm.provider == "openrouter"
        except ConfigValidationError:
            # If it raises, that's also acceptable behavior
            pass
    
    def test_numeric_validation_boundaries(self, complete_alice_env):
        """Test numeric field validation at boundaries."""
        config_file = complete_alice_env["config_file"]
        
        # Test with values at boundaries
        boundary_config = {
            "version": 1,
            "llm": {
                "provider": "openrouter",
                "model": "test",
                "max_retries": 0,  # Minimum
                "compression_threshold": 0.1,  # Minimum
                "compression_target": 0.05,  # Minimum
            },
            "voice": {
                "vad": {
                    "threshold": 1.0,  # Maximum
                    "silence_duration_ms": 100,  # Minimum
                },
            },
        }
        with open(config_file, 'w') as f:
            yaml.safe_dump(boundary_config, f)
        
        manager = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager.env_path = complete_alice_env["env_file"]
        config = manager.load()
        
        # Verify boundary values accepted
        assert config.llm.max_retries == 0
        assert config.llm.compression_threshold == 0.1
        assert config.voice.vad.threshold == 1.0


class TestConfigurationConvenienceFunctions:
    """Test convenience functions for configuration."""
    
    def test_load_config_convenience_function(self, complete_alice_env):
        """Test load_config convenience function."""
        # Temporarily set env path via environment
        with patch.dict(os.environ, {
            "LIVEKIT_URL": "wss://test.livekit.cloud",
            "LIVEKIT_API_KEY": "key",
            "LIVEKIT_API_SECRET": "secret",
            "GOOGLE_API_KEY": "key",
        }):
            config = load_config(alice_home=complete_alice_env["alice_home"])
            assert isinstance(config, AliceConfig)
    
    def test_config_manager_reusability(self, complete_alice_env):
        """Test that ConfigManager can be reused."""
        manager = ConfigManager(alice_home=complete_alice_env["alice_home"])
        manager.env_path = complete_alice_env["env_file"]
        
        # Load multiple times
        config1 = manager.load()
        config2 = manager.load()
        
        # Should work without issues
        assert isinstance(config1, AliceConfig)
        assert isinstance(config2, AliceConfig)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
