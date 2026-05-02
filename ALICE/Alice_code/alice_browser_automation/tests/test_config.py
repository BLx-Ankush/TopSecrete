"""
Unit tests for configuration management.
"""

import pytest
from pathlib import Path
from alice_browser_automation.config import (
    Config,
    BrowserConfig,
    QwenConfig,
    LoggingConfig,
)


class TestConfig:
    """Test configuration loading and validation"""
    
    def test_default_config(self):
        """Test that default configuration is created correctly"""
        config = Config()
        
        assert config.browser.headless_default is True
        assert config.browser.max_concurrent_sessions == 3
        assert config.qwen.host == "http://localhost:11434"
        assert config.qwen.model == "qwen2.5-coder:3b"
        assert config.logging.level == "INFO"
    
    def test_config_from_yaml(self, test_config_path: Path):
        """Test loading configuration from YAML file"""
        config = Config.from_yaml(str(test_config_path))
        
        assert config.browser.max_concurrent_sessions == 2
        assert config.browser.idle_timeout_seconds == 60
        assert config.qwen.timeout_seconds == 10
        assert config.logging.level == "DEBUG"
    
    def test_config_validation_success(self):
        """Test that valid configuration passes validation"""
        config = Config()
        assert config.validate() is True
    
    def test_config_validation_invalid_sessions(self):
        """Test that invalid max_concurrent_sessions fails validation"""
        config = Config()
        config.browser.max_concurrent_sessions = 0
        
        with pytest.raises(ValueError, match="max_concurrent_sessions must be at least 1"):
            config.validate()
    
    def test_config_validation_invalid_timeout(self):
        """Test that invalid timeout fails validation"""
        config = Config()
        config.qwen.timeout_seconds = 0
        
        with pytest.raises(ValueError, match="Qwen timeout must be at least 1 second"):
            config.validate()
    
    def test_config_validation_invalid_log_level(self):
        """Test that invalid log level fails validation"""
        config = Config()
        config.logging.level = "INVALID"
        
        with pytest.raises(ValueError, match="Invalid log level"):
            config.validate()
    
    def test_config_to_dict(self):
        """Test converting configuration to dictionary"""
        config = Config()
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert "browser" in config_dict
        assert "qwen" in config_dict
        assert "logging" in config_dict
        assert config_dict["browser"]["max_concurrent_sessions"] == 3
        assert config_dict["qwen"]["model"] == "qwen2.5-coder:3b"


class TestBrowserConfig:
    """Test browser-specific configuration"""
    
    def test_default_browser_config(self):
        """Test default browser configuration values"""
        config = BrowserConfig()
        
        assert config.headless_default is True
        assert config.max_concurrent_sessions == 3
        assert config.idle_timeout_seconds == 300
        assert config.default_profile == "default"


class TestQwenConfig:
    """Test Qwen model configuration"""
    
    def test_default_qwen_config(self):
        """Test default Qwen configuration values"""
        config = QwenConfig()
        
        assert config.host == "http://localhost:11434"
        assert config.model == "qwen2.5-coder:3b"
        assert config.timeout_seconds == 30
        assert config.max_retries == 3


class TestLoggingConfig:
    """Test logging configuration"""
    
    def test_default_logging_config(self):
        """Test default logging configuration values"""
        config = LoggingConfig()
        
        assert config.level == "INFO"
        assert config.log_sensitive_data is False
        assert "browser_automation.log" in config.log_file
