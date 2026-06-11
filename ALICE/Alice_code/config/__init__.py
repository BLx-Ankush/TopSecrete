"""
Configuration Management for ALICE

This module provides configuration loading, validation, and management
with support for profiles, environment variables, and secure secrets.
"""

__version__ = "0.1.0"

from .models import (
    # Main configuration
    AliceConfig,
    
    # Subsystem configurations
    LLMConfig,
    VoiceConfig,
    MemoryConfig,
    SkillsConfig,
    ToolsConfig,
    GatewayConfig,
    CronConfig,
    SecurityConfig,
    PersonalityConfig,
    
    # Component configurations
    APIKeyConfig,
    VADConfig,
    LiveKitConfig,
    TelegramConfig,
    DiscordConfig,
    
    # Validation helpers
    validate_config_file,
    get_default_config,
)

from .manager import (
    ConfigManager,
    ConfigurationError,
    ConfigValidationError,
    ConfigLoadError,
    get_config_manager,
    load_config,
)

__all__ = [
    # Main configuration
    "AliceConfig",
    
    # Subsystem configurations
    "LLMConfig",
    "VoiceConfig",
    "MemoryConfig",
    "SkillsConfig",
    "ToolsConfig",
    "GatewayConfig",
    "CronConfig",
    "SecurityConfig",
    "PersonalityConfig",
    
    # Component configurations
    "APIKeyConfig",
    "VADConfig",
    "LiveKitConfig",
    "TelegramConfig",
    "DiscordConfig",
    
    # Validation helpers
    "validate_config_file",
    "get_default_config",
    
    # Configuration manager
    "ConfigManager",
    "ConfigurationError",
    "ConfigValidationError",
    "ConfigLoadError",
    "get_config_manager",
    "load_config",
]
