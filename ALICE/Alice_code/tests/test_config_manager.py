"""
Unit tests for ConfigManager.

Tests configuration loading, validation, environment variable handling,
and profile management.
"""

import pytest
import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from config.manager import (
    ConfigManager,
    ConfigurationError,
    ConfigValidationError,
    ConfigLoadError,
    get_config_manager,
    load_config,
)
from config.models import AliceConfig


@pytest.fixture
def temp_alice_home(tmp_path):
    """Create temporary ALICE_HOME directory structure."""
    alice_home = tmp_path / "data"
    alice_home.mkdir()
    
    # Create subdirectories
    (alice_home / "skills").mkdir()
    (alice_home / "cron").mkdir()
    (alice_home / "logs").mkdir()
    
    # Create placeholder files
    (alice_home / "MEMORY.md").write_text("# Memory\n")
    (alice_home / "USER.md").write_text("# User Profile\n")
    (alice_home / "SOUL.md").write_text("# Personality\n")
    
    return alice_home


@pytest.fixture
def temp_env_file(tmp_path):
    """Create temporary .env file."""
    env_file = tmp_path / ".env"
    env_content = """
LIVEKIT_URL=wss://test.livekit.cloud
LIVEKIT_API_KEY=test_api_key
LIVEKIT_API_SECRET=test_api_secret
GOOGLE_API_KEY=test_google_key
OPENROUTER_API_KEY=test_openrouter_key
"""
    env_file.write_text(env_content.strip())
    return env_file


@pytest.fixture
def valid_config_yaml(temp_alice_home):
    """Create valid config.yaml file."""
    config_path = temp_alice_home / "config.yaml"
    config = {
        "version": 1,
        "llm": {
            "provider": "openrouter",
            "model": "anthropic/claude-3.5-sonnet",
        },
        "voice": {
            "provider": "gemini-realtime",
            "model": "gemini-2.0-flash-exp",
            "livekit": {
                "url": "${LIVEKIT_URL}",
                "api_key": "${LIVEKIT_API_KEY}",
                "api_secret": "${LIVEKIT_API_SECRET}",
            },
        },
    }
    with open(config_path, 'w') as f:
        yaml.safe_dump(config, f)
    return config_path


class TestConfigManager:
    """Tests for ConfigManager class."""
    
    def test_init_default_profile(self, temp_alice_home):
        """Test ConfigManager initialization with default profile."""
        manager = ConfigManager(profile="default", alice_home=temp_alice_home)
        assert manager.profile == "default"
        assert manager.alice_home == temp_alice_home
        assert manager.config_path == temp_alice_home / "config.yaml"
    
    def test_init_custom_profile(self, temp_alice_home):
        """Test ConfigManager initialization with custom profile."""
        manager = ConfigManager(profile="work", alice_home=temp_alice_home)
        assert manager.profile == "work"
        # Profile path should be under profiles/
        assert "profiles" in str(manager.alice_home) or manager.alice_home == temp_alice_home
    
    def test_resolve_alice_home_default(self, temp_alice_home):
        """Test ALICE_HOME resolution for default profile."""
        manager = ConfigManager(profile="default", alice_home=temp_alice_home)
        assert manager.alice_home == temp_alice_home
    
    def test_load_defaults(self, temp_alice_home):
        """Test loading default configuration."""
        manager = ConfigManager(alice_home=temp_alice_home)
        defaults = manager._load_defaults()
        
        assert defaults["version"] == 1
        assert "llm" in defaults
        assert "voice" in defaults
        assert defaults["llm"]["provider"] == "openrouter"
    
    def test_load_yaml_valid(self, temp_alice_home, valid_config_yaml):
        """Test loading valid YAML configuration."""
        manager = ConfigManager(alice_home=temp_alice_home)
        config = manager._load_yaml(valid_config_yaml)
        
        assert config["version"] == 1
        assert config["llm"]["provider"] == "openrouter"
    
    def test_load_yaml_missing_file(self, temp_alice_home):
        """Test loading non-existent YAML file."""
        manager = ConfigManager(alice_home=temp_alice_home)
        config = manager._load_yaml(temp_alice_home / "nonexistent.yaml")
        
        # Should return empty dict, not raise error
        assert config == {}
    
    def test_load_yaml_invalid(self, temp_alice_home):
        """Test loading invalid YAML file."""
        invalid_yaml = temp_alice_home / "invalid.yaml"
        invalid_yaml.write_text("invalid: yaml: content: [")
        
        manager = ConfigManager(alice_home=temp_alice_home)
        with pytest.raises(ConfigLoadError):
            manager._load_yaml(invalid_yaml)
    
    def test_deep_merge_simple(self, temp_alice_home):
        """Test deep merge with simple dictionaries."""
        manager = ConfigManager(alice_home=temp_alice_home)
        
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        
        result = manager._deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}
    
    def test_deep_merge_nested(self, temp_alice_home):
        """Test deep merge with nested dictionaries."""
        manager = ConfigManager(alice_home=temp_alice_home)
        
        base = {
            "llm": {
                "provider": "openrouter",
                "model": "test",
                "max_retries": 3,
            }
        }
        override = {
            "llm": {
                "model": "new-model",
                "timeout": 30,
            }
        }
        
        result = manager._deep_merge(base, override)
        assert result["llm"]["provider"] == "openrouter"  # preserved
        assert result["llm"]["model"] == "new-model"  # overridden
        assert result["llm"]["max_retries"] == 3  # preserved
        assert result["llm"]["timeout"] == 30  # added
    
    def test_apply_env_overrides(self, temp_alice_home):
        """Test environment variable substitution."""
        manager = ConfigManager(alice_home=temp_alice_home)
        
        # Set environment variables
        os.environ["TEST_VAR"] = "test_value"
        os.environ["TEST_URL"] = "https://test.com"
        
        config = {
            "key1": "${TEST_VAR}",
            "nested": {
                "key2": "${TEST_URL}",
                "key3": "normal_value",
            },
        }
        
        result = manager._apply_env_overrides(config)
        assert result["key1"] == "test_value"
        assert result["nested"]["key2"] == "https://test.com"
        assert result["nested"]["key3"] == "normal_value"
        
        # Cleanup
        del os.environ["TEST_VAR"]
        del os.environ["TEST_URL"]
    
    def test_apply_env_overrides_missing_var(self, temp_alice_home):
        """Test environment variable substitution with missing variable."""
        manager = ConfigManager(alice_home=temp_alice_home)
        
        config = {"key": "${MISSING_VAR}"}
        result = manager._apply_env_overrides(config)
        
        # Missing variables should be replaced with empty string
        assert result["key"] == ""
    
    def test_load_full_config(self, temp_alice_home, valid_config_yaml, temp_env_file):
        """Test full configuration loading process."""
        # Set up environment
        manager = ConfigManager(alice_home=temp_alice_home)
        manager.env_path = temp_env_file
        
        # Load environment variables
        manager._load_env(temp_env_file)
        
        # Load configuration
        config = manager.load()
        
        assert isinstance(config, AliceConfig)
        assert config.version == 1
        assert config.llm.provider == "openrouter"
        assert config.voice.livekit.url == "wss://test.livekit.cloud"
    
    def test_validate_valid_config(self, temp_alice_home):
        """Test validation of valid configuration."""
        manager = ConfigManager(alice_home=temp_alice_home)
        
        config_dict = {
            "version": 1,
            "alice_home": str(temp_alice_home),
            "llm": {
                "provider": "openrouter",
                "model": "test",
            },
            "voice": {
                "provider": "gemini-realtime",
                "model": "gemini-2.0-flash-exp",
                "livekit": {
                    "url": "wss://test.livekit.cloud",
                    "api_key": "key",
                    "api_secret": "secret",
                },
            },
        }
        
        validated = manager._validate(config_dict)
        assert isinstance(validated, AliceConfig)
    
    def test_validate_invalid_config(self, temp_alice_home):
        """Test validation of invalid configuration."""
        manager = ConfigManager(alice_home=temp_alice_home)
        
        config_dict = {
            "version": 1,
            "alice_home": str(temp_alice_home),
            "llm": {
                "provider": "invalid_provider",  # Invalid
                "model": "test",
            },
            "voice": {
                "provider": "gemini-realtime",
                "model": "test",
                "livekit": {
                    "url": "wss://test.livekit.cloud",
                    "api_key": "key",
                    "api_secret": "secret",
                },
            },
        }
        
        with pytest.raises(ConfigValidationError):
            manager._validate(config_dict)
    
    def test_save_config(self, temp_alice_home, temp_env_file):
        """Test saving configuration to file."""
        manager = ConfigManager(alice_home=temp_alice_home)
        manager.env_path = temp_env_file
        
        # Load environment variables
        manager._load_env(temp_env_file)
        
        # Load configuration
        config = manager.load()
        
        # Modify configuration
        config.llm.model = "new-model"
        
        # Save configuration
        manager.save(config)
        
        # Verify file was created
        assert manager.config_path.exists()
        
        # Load and verify
        with open(manager.config_path) as f:
            saved_config = yaml.safe_load(f)
        
        assert saved_config["llm"]["model"] == "new-model"
    
    def test_get_config_value(self, temp_alice_home, temp_env_file):
        """Test getting configuration value by key."""
        manager = ConfigManager(alice_home=temp_alice_home)
        manager.env_path = temp_env_file
        manager._load_env(temp_env_file)
        manager.load()
        
        # Get nested value
        provider = manager.get("llm.provider")
        assert provider == "openrouter"
        
        # Get with default
        missing = manager.get("nonexistent.key", "default")
        assert missing == "default"
    
    def test_set_config_value(self, temp_alice_home, temp_env_file):
        """Test setting configuration value by key."""
        manager = ConfigManager(alice_home=temp_alice_home)
        manager.env_path = temp_env_file
        manager._load_env(temp_env_file)
        manager.load()
        
        # Set value
        manager.set("llm.model", "new-model")
        
        # Verify
        assert manager.config.llm.model == "new-model"
    
    def test_set_invalid_key(self, temp_alice_home, temp_env_file):
        """Test setting invalid configuration key."""
        manager = ConfigManager(alice_home=temp_alice_home)
        manager.env_path = temp_env_file
        manager._load_env(temp_env_file)
        manager.load()
        
        with pytest.raises(ConfigValidationError):
            manager.set("invalid.key", "value")
    
    def test_reload_config(self, temp_alice_home, valid_config_yaml, temp_env_file):
        """Test reloading configuration."""
        manager = ConfigManager(alice_home=temp_alice_home)
        manager.env_path = temp_env_file
        manager._load_env(temp_env_file)
        
        # Initial load
        config1 = manager.load()
        original_model = config1.llm.model
        
        # Modify config file
        with open(valid_config_yaml, 'r') as f:
            config_data = yaml.safe_load(f)
        config_data["llm"]["model"] = "modified-model"
        with open(valid_config_yaml, 'w') as f:
            yaml.safe_dump(config_data, f)
        
        # Reload
        config2 = manager.reload()
        
        assert config2.llm.model == "modified-model"
        assert config2.llm.model != original_model
    
    def test_validate_env_vars(self, temp_alice_home, temp_env_file):
        """Test environment variable validation."""
        manager = ConfigManager(alice_home=temp_alice_home)
        manager._load_env(temp_env_file)
        
        status = manager.validate_env_vars()
        
        # Required variables should be present
        assert status["LIVEKIT_URL"] is True
        assert status["LIVEKIT_API_KEY"] is True
        assert status["GOOGLE_API_KEY"] is True


class TestConfigManagerHelpers:
    """Tests for ConfigManager helper functions."""
    
    def test_get_config_manager(self, temp_alice_home):
        """Test get_config_manager helper."""
        manager = get_config_manager(alice_home=temp_alice_home)
        assert isinstance(manager, ConfigManager)
        assert manager.alice_home == temp_alice_home
    
    def test_load_config_helper(self, temp_alice_home, valid_config_yaml, temp_env_file):
        """Test load_config helper."""
        # Create manager to set up env path
        manager = ConfigManager(alice_home=temp_alice_home)
        manager.env_path = temp_env_file
        manager._load_env(temp_env_file)
        
        # Use helper
        config = load_config(alice_home=temp_alice_home)
        assert isinstance(config, AliceConfig)


class TestConfigManagerEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_load_without_env_file(self, temp_alice_home, valid_config_yaml):
        """Test loading configuration without .env file."""
        manager = ConfigManager(alice_home=temp_alice_home)
        
        # Should not raise error, just warning
        config = manager.load()
        assert isinstance(config, AliceConfig)
    
    def test_load_without_config_file(self, temp_alice_home, temp_env_file):
        """Test loading with only defaults (no config.yaml)."""
        manager = ConfigManager(alice_home=temp_alice_home)
        manager.env_path = temp_env_file
        manager._load_env(temp_env_file)
        
        # Should use defaults
        config = manager.load()
        assert isinstance(config, AliceConfig)
        assert config.llm.provider == "openrouter"  # default
    
    def test_get_before_load(self, temp_alice_home):
        """Test getting config value before loading."""
        manager = ConfigManager(alice_home=temp_alice_home)
        
        with pytest.raises(ConfigLoadError):
            manager.get("llm.provider")
    
    def test_set_before_load(self, temp_alice_home):
        """Test setting config value before loading."""
        manager = ConfigManager(alice_home=temp_alice_home)
        
        with pytest.raises(ConfigLoadError):
            manager.set("llm.provider", "test")
    
    def test_save_before_load(self, temp_alice_home):
        """Test saving config before loading."""
        manager = ConfigManager(alice_home=temp_alice_home)
        
        with pytest.raises(ConfigLoadError):
            manager.save()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
