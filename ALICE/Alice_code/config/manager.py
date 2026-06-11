"""
Configuration Manager for ALICE-Hermes Integration.

This module provides the ConfigManager class for loading, validating, and managing
configuration from YAML files, environment variables, and profiles.

Author: ALICE-Hermes Integration Team
Version: 1.0.0
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from pydantic import ValidationError
import re

from .models import AliceConfig, validate_config_file

# Current configuration version
CURRENT_VERSION = 1

# Setup logger
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Base exception for configuration errors."""
    pass


class ConfigValidationError(ConfigurationError):
    """Configuration validation error."""
    pass


class ConfigLoadError(ConfigurationError):
    """Configuration loading error."""
    pass


class ConfigManager:
    """
    Manages configuration loading, validation, and profiles.
    
    The ConfigManager handles:
    - Loading configuration from YAML files
    - Loading environment variables from .env files
    - Deep merging default and user configurations
    - Applying environment variable overrides
    - Validating configuration with Pydantic models
    - Profile-based configuration isolation
    - Configuration version migration
    
    Attributes:
        profile: Active configuration profile name
        alice_home: Path to ALICE data directory
        config_path: Path to config.yaml file
        env_path: Path to .env file
        config: Loaded and validated configuration
    """
    
    def __init__(self, profile: Optional[str] = None, alice_home: Optional[Path] = None):
        """
        Initialize ConfigManager.
        
        Args:
            profile: Configuration profile name (default: "default")
            alice_home: Override ALICE_HOME directory (for testing)
        """
        self.profile = profile or os.getenv("ALICE_PROFILE", "default")
        self.alice_home = alice_home or self._resolve_alice_home()
        self.config_path = self.alice_home / "config.yaml"
        self.env_path = self.alice_home.parent / ".env"  # .env is in Alice_code/
        self.config: Optional[AliceConfig] = None
        
        logger.info(f"ConfigManager initialized with profile: {self.profile}")
        logger.info(f"ALICE_HOME: {self.alice_home}")
    
    def _resolve_alice_home(self) -> Path:
        """
        Resolve ALICE_HOME based on profile.
        
        For default profile: ALICE/Alice_code/data/
        For named profiles: ALICE/Alice_code/data/profiles/{profile_name}/
        
        Returns:
            Path to ALICE data directory
        """
        # Check for ALICE_HOME environment variable
        if "ALICE_HOME" in os.environ:
            return Path(os.environ["ALICE_HOME"]).expanduser().resolve()
        
        # Default to data directory in Alice_code
        base_dir = Path(__file__).parent.parent / "data"
        
        if self.profile == "default":
            return base_dir
        else:
            return base_dir / "profiles" / self.profile
    
    def load(self) -> AliceConfig:
        """
        Load and validate configuration.
        
        Process:
        1. Load default configuration
        2. Load user configuration from config.yaml
        3. Deep merge defaults with user config
        4. Load environment variables from .env
        5. Apply environment variable overrides
        6. Validate with Pydantic models
        7. Migrate if version mismatch
        
        Returns:
            Validated AliceConfig instance
            
        Raises:
            ConfigLoadError: If configuration cannot be loaded
            ConfigValidationError: If configuration is invalid
        """
        try:
            # Load defaults
            logger.debug("Loading default configuration")
            default_config = self._load_defaults()
            
            # Load user config
            logger.debug(f"Loading user configuration from {self.config_path}")
            user_config = self._load_yaml(self.config_path)
            
            # Deep merge
            logger.debug("Merging default and user configurations")
            merged = self._deep_merge(default_config, user_config)
            
            # Load environment variables
            logger.debug(f"Loading environment variables from {self.env_path}")
            self._load_env(self.env_path)
            
            # Apply environment overrides
            logger.debug("Applying environment variable overrides")
            config_dict = self._apply_env_overrides(merged)
            
            # Add alice_home to config
            config_dict["alice_home"] = str(self.alice_home)
            
            # Validate
            logger.debug("Validating configuration")
            validated = self._validate(config_dict)
            
            # Check version and migrate if needed
            if validated.version < CURRENT_VERSION:
                logger.info(f"Migrating configuration from v{validated.version} to v{CURRENT_VERSION}")
                validated = self._migrate(validated)
            
            self.config = validated
            logger.info("Configuration loaded and validated successfully")
            return validated
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ConfigLoadError(f"Failed to load configuration: {e}") from e
    
    def _load_defaults(self) -> Dict[str, Any]:
        """
        Load default configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {
            "version": CURRENT_VERSION,
            "llm": {
                "provider": "openrouter",
                "model": "anthropic/claude-3.5-sonnet",
                "fallback_providers": [],
                "api_keys": {},
                "max_retries": 3,
                "retry_delay": 1.0,
                "exponential_backoff": True,
                "context_window": "auto",
                "compression_threshold": 0.50,
                "compression_target": 0.20,
                "preserve_last_n": 20,
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
                "audio_device": None,
                "enable_nvidia_broadcast": False,
            },
            "memory": {
                "provider": "builtin",
                "builtin_memory_file": "MEMORY.md",
                "builtin_user_file": "USER.md",
            },
            "skills": {
                "enabled": True,
                "skills_dir": "skills",
                "optional_skills_dir": "optional-skills",
                "auto_create": True,
                "skills_hub_enabled": False,
                "skills_hub_url": "https://agentskills.io",
            },
            "tools": {
                "enabled": True,
                "tools_dir": "tools",
                "default_toolset": "alice-cli",
                "enabled_toolsets": ["alice-cli"],
                "mcp_enabled": False,
                "mcp_servers": {},
            },
            "gateway": {
                "enabled": False,
                "telegram": {
                    "enabled": False,
                    "bot_token": None,
                    "allowed_users": [],
                    "home_channel": None,
                    "dm_pairing": True,
                },
                "discord": {
                    "enabled": False,
                    "bot_token": None,
                    "allowed_guilds": [],
                    "home_channel": None,
                },
            },
            "cron": {
                "enabled": False,
                "jobs_file": "cron/jobs.yaml",
                "default_timeout": 1800,
                "max_retries": 3,
                "log_dir": "cron/logs",
            },
            "security": {
                "approval_enabled": True,
                "approval_timeout": 300,
                "trusted_users": [],
                "always_approve": [],
                "always_deny": [],
                "use_auxiliary_for_approval": True,
                "risk_threshold": 0.7,
            },
            "personality": {
                "soul_file": "SOUL.md",
                "language": "hinglish",
                "tone": "warm",
                "proactive_support": True,
                "enable_coaching": True,
            },
        }
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """
        Load YAML configuration file.
        
        Args:
            path: Path to YAML file
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigLoadError: If file cannot be loaded
        """
        if not path.exists():
            logger.warning(f"Configuration file not found: {path}")
            return {}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config or {}
        except yaml.YAMLError as e:
            raise ConfigLoadError(f"Invalid YAML in {path}: {e}") from e
        except Exception as e:
            raise ConfigLoadError(f"Failed to read {path}: {e}") from e
    
    def _load_env(self, path: Path) -> None:
        """
        Load environment variables from .env file.
        
        Args:
            path: Path to .env file
        """
        if not path.exists():
            logger.warning(f".env file not found: {path}")
            return
        
        # Check file permissions (should be 0600 on Unix)
        if hasattr(os, 'stat'):
            try:
                stat_info = path.stat()
                mode = stat_info.st_mode & 0o777
                if mode != 0o600 and os.name != 'nt':  # Skip on Windows
                    logger.warning(
                        f".env file has permissive permissions: {oct(mode)}. "
                        f"Consider setting to 0600 for security."
                    )
            except Exception as e:
                logger.debug(f"Could not check .env permissions: {e}")
        
        # Load environment variables
        load_dotenv(path, override=True)
        logger.debug(f"Loaded environment variables from {path}")
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.
        
        Override values take precedence over base values.
        Nested dictionaries are merged recursively.
        
        Args:
            base: Base dictionary
            override: Override dictionary
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._deep_merge(result[key], value)
            else:
                # Override value
                result[key] = value
        
        return result
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.
        
        Replaces ${VAR_NAME} placeholders with environment variable values.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configuration with environment variables substituted
        """
        def substitute(obj: Any) -> Any:
            """Recursively substitute environment variables."""
            if isinstance(obj, dict):
                return {k: substitute(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [substitute(item) for item in obj]
            elif isinstance(obj, str):
                # Replace ${VAR_NAME} with environment variable value
                pattern = r'\$\{([^}]+)\}'
                matches = re.findall(pattern, obj)
                for var_name in matches:
                    env_value = os.getenv(var_name, "")
                    obj = obj.replace(f"${{{var_name}}}", env_value)
                return obj
            else:
                return obj
        
        return substitute(config)
    
    def _validate(self, config: Dict[str, Any]) -> AliceConfig:
        """
        Validate configuration against Pydantic schema.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Validated AliceConfig instance
            
        Raises:
            ConfigValidationError: If validation fails
        """
        try:
            return validate_config_file(config)
        except ValidationError as e:
            # Format validation errors for better readability
            errors = []
            for error in e.errors():
                loc = " -> ".join(str(l) for l in error["loc"])
                msg = error["msg"]
                errors.append(f"  {loc}: {msg}")
            
            error_msg = "Configuration validation failed:\n" + "\n".join(errors)
            raise ConfigValidationError(error_msg) from e
    
    def _migrate(self, config: AliceConfig) -> AliceConfig:
        """
        Migrate configuration to current version.
        
        Args:
            config: Configuration to migrate
            
        Returns:
            Migrated configuration
        """
        migrations = {
            # Add migration functions as needed
            # 1: self._migrate_v1_to_v2,
            # 2: self._migrate_v2_to_v3,
        }
        
        current_version = config.version
        while current_version < CURRENT_VERSION:
            if current_version not in migrations:
                logger.warning(
                    f"No migration path from v{current_version} to v{CURRENT_VERSION}"
                )
                break
            
            logger.info(f"Migrating from v{current_version} to v{current_version + 1}")
            config = migrations[current_version](config)
            current_version += 1
        
        return config
    
    def save(self, config: Optional[AliceConfig] = None) -> None:
        """
        Save configuration to YAML file.
        
        Args:
            config: Configuration to save (uses self.config if None)
            
        Raises:
            ConfigLoadError: If configuration cannot be saved
        """
        if config is None:
            config = self.config
        
        if config is None:
            raise ConfigLoadError("No configuration to save")
        
        try:
            # Convert Pydantic model to dict
            config_dict = config.model_dump(exclude={"alice_home"})
            
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write YAML
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(
                    config_dict,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2
                )
            
            logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            raise ConfigLoadError(f"Failed to save configuration: {e}") from e
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.
        
        Args:
            key: Configuration key (e.g., "llm.provider")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        if self.config is None:
            raise ConfigLoadError("Configuration not loaded")
        
        parts = key.split(".")
        value = self.config
        
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value by dot-notation key.
        
        Args:
            key: Configuration key (e.g., "llm.provider")
            value: Value to set
            
        Raises:
            ConfigLoadError: If configuration not loaded
            ConfigValidationError: If value is invalid
        """
        if self.config is None:
            raise ConfigLoadError("Configuration not loaded")
        
        parts = key.split(".")
        obj = self.config
        
        # Navigate to parent object
        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                raise ConfigValidationError(f"Invalid configuration key: {key}")
        
        # Set value
        final_key = parts[-1]
        if hasattr(obj, final_key):
            setattr(obj, final_key, value)
        else:
            raise ConfigValidationError(f"Invalid configuration key: {key}")
        
        logger.info(f"Configuration updated: {key} = {value}")
    
    def reload(self) -> AliceConfig:
        """
        Reload configuration from disk.
        
        Returns:
            Reloaded configuration
        """
        logger.info("Reloading configuration")
        return self.load()
    
    def validate_env_vars(self) -> Dict[str, bool]:
        """
        Validate that required environment variables are set.
        
        Returns:
            Dictionary mapping variable names to presence status
        """
        required_vars = [
            "LIVEKIT_URL",
            "LIVEKIT_API_KEY",
            "LIVEKIT_API_SECRET",
            "GOOGLE_API_KEY",
        ]
        
        optional_vars = [
            "OPENROUTER_API_KEY",
            "ANTHROPIC_API_KEY",
            "MEM0_API_KEY",
            "N8N_MCP_SERVER_URL",
        ]
        
        status = {}
        missing_required = []
        
        for var in required_vars:
            is_set = bool(os.getenv(var))
            status[var] = is_set
            if not is_set:
                missing_required.append(var)
        
        for var in optional_vars:
            status[var] = bool(os.getenv(var))
        
        if missing_required:
            logger.warning(
                f"Missing required environment variables: {', '.join(missing_required)}"
            )
        
        return status


def get_config_manager(
    profile: Optional[str] = None,
    alice_home: Optional[Path] = None
) -> ConfigManager:
    """
    Get a ConfigManager instance.
    
    Args:
        profile: Configuration profile name
        alice_home: Override ALICE_HOME directory
        
    Returns:
        ConfigManager instance
    """
    return ConfigManager(profile=profile, alice_home=alice_home)


def load_config(
    profile: Optional[str] = None,
    alice_home: Optional[Path] = None
) -> AliceConfig:
    """
    Load and validate configuration.
    
    Convenience function for quick configuration loading.
    
    Args:
        profile: Configuration profile name
        alice_home: Override ALICE_HOME directory
        
    Returns:
        Validated AliceConfig instance
    """
    manager = get_config_manager(profile=profile, alice_home=alice_home)
    return manager.load()
