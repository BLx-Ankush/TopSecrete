"""
Configuration management for Alice Browser Automation.

This module handles loading and validating configuration from YAML files
and environment variables.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dataclasses import dataclass, field


@dataclass
class BrowserConfig:
    """Browser-specific configuration"""
    headless_default: bool = True
    max_concurrent_sessions: int = 3
    idle_timeout_seconds: int = 300
    profiles_dir: str = "~/.alice/browser_profiles"
    default_profile: str = "default"


@dataclass
class QwenConfig:
    """Qwen model configuration"""
    host: str = "http://localhost:11434"
    model: str = "qwen2.5-coder:3b"
    timeout_seconds: int = 30
    max_retries: int = 3


@dataclass
class DOMParserConfig:
    """DOM parser configuration"""
    cache_duration_seconds: float = 2.0
    max_elements: int = 1000
    filter_decorative: bool = True


@dataclass
class PerformanceConfig:
    """Performance targets and timeouts"""
    dom_parse_timeout: float = 2.0
    action_generation_timeout: float = 5.0
    simple_action_timeout: float = 1.0


@dataclass
class SecurityConfig:
    """Security and privacy settings"""
    require_payment_confirmation: bool = True
    block_banking_sites: bool = False
    validate_ssl: bool = True
    clear_sensitive_data: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    log_file: str = "~/.alice/logs/browser_automation.log"
    log_sensitive_data: bool = False


@dataclass
class Config:
    """Main configuration container"""
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    qwen: QwenConfig = field(default_factory=QwenConfig)
    dom_parser: DOMParserConfig = field(default_factory=DOMParserConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_yaml(cls, config_path: str) -> "Config":
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Config instance with loaded settings
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        path = Path(config_path).expanduser()
        
        if not path.exists():
            logging.warning(f"Config file not found: {config_path}, using defaults")
            return cls()
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        if not data:
            return cls()
        
        return cls(
            browser=BrowserConfig(**data.get('browser', {})),
            qwen=QwenConfig(**data.get('qwen', {})),
            dom_parser=DOMParserConfig(**data.get('dom_parser', {})),
            performance=PerformanceConfig(**data.get('performance', {})),
            security=SecurityConfig(**data.get('security', {})),
            logging=LoggingConfig(**data.get('logging', {})),
        )
    
    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables.
        
        Environment variables override YAML settings.
        
        Returns:
            Config instance with environment variable overrides
        """
        config = cls()
        
        # Browser config
        if os.getenv('BROWSER_PROFILES_DIR'):
            config.browser.profiles_dir = os.getenv('BROWSER_PROFILES_DIR')
        
        # Qwen config
        if os.getenv('OLLAMA_HOST'):
            config.qwen.host = os.getenv('OLLAMA_HOST')
        if os.getenv('QWEN_MODEL'):
            config.qwen.model = os.getenv('QWEN_MODEL')
        
        # Logging config
        if os.getenv('LOG_LEVEL'):
            config.logging.level = os.getenv('LOG_LEVEL')
        
        return config
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """
        Load configuration from file and environment.
        
        Priority: Environment variables > YAML file > Defaults
        
        Args:
            config_path: Optional path to YAML config file
            
        Returns:
            Config instance with merged settings
        """
        # Start with defaults
        if config_path:
            config = cls.from_yaml(config_path)
        else:
            # Try default locations
            default_paths = [
                "alice_browser_automation_config.yaml",
                "~/.alice/alice_browser_automation_config.yaml",
                "/etc/alice/alice_browser_automation_config.yaml",
            ]
            
            config = None
            for path in default_paths:
                try:
                    config = cls.from_yaml(path)
                    logging.info(f"Loaded config from: {path}")
                    break
                except FileNotFoundError:
                    continue
            
            if config is None:
                config = cls()
                logging.info("Using default configuration")
        
        # Apply environment variable overrides
        env_config = cls.from_env()
        config.browser.profiles_dir = env_config.browser.profiles_dir
        config.qwen.host = env_config.qwen.host
        config.qwen.model = env_config.qwen.model
        config.logging.level = env_config.logging.level
        
        return config
    
    def validate(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate browser config
        if self.browser.max_concurrent_sessions < 1:
            raise ValueError("max_concurrent_sessions must be at least 1")
        
        if self.browser.idle_timeout_seconds < 0:
            raise ValueError("idle_timeout_seconds must be non-negative")
        
        # Validate Qwen config
        if not self.qwen.host:
            raise ValueError("Qwen host must be specified")
        
        if not self.qwen.model:
            raise ValueError("Qwen model must be specified")
        
        if self.qwen.timeout_seconds < 1:
            raise ValueError("Qwen timeout must be at least 1 second")
        
        # Validate DOM parser config
        if self.dom_parser.cache_duration_seconds < 0:
            raise ValueError("cache_duration_seconds must be non-negative")
        
        if self.dom_parser.max_elements < 1:
            raise ValueError("max_elements must be at least 1")
        
        # Validate performance config
        if self.performance.dom_parse_timeout < 0:
            raise ValueError("dom_parse_timeout must be non-negative")
        
        if self.performance.action_generation_timeout < 0:
            raise ValueError("action_generation_timeout must be non-negative")
        
        # Validate logging config
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.logging.level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {self.logging.level}")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            'browser': {
                'headless_default': self.browser.headless_default,
                'max_concurrent_sessions': self.browser.max_concurrent_sessions,
                'idle_timeout_seconds': self.browser.idle_timeout_seconds,
                'profiles_dir': self.browser.profiles_dir,
                'default_profile': self.browser.default_profile,
            },
            'qwen': {
                'host': self.qwen.host,
                'model': self.qwen.model,
                'timeout_seconds': self.qwen.timeout_seconds,
                'max_retries': self.qwen.max_retries,
            },
            'dom_parser': {
                'cache_duration_seconds': self.dom_parser.cache_duration_seconds,
                'max_elements': self.dom_parser.max_elements,
                'filter_decorative': self.dom_parser.filter_decorative,
            },
            'performance': {
                'dom_parse_timeout': self.performance.dom_parse_timeout,
                'action_generation_timeout': self.performance.action_generation_timeout,
                'simple_action_timeout': self.performance.simple_action_timeout,
            },
            'security': {
                'require_payment_confirmation': self.security.require_payment_confirmation,
                'block_banking_sites': self.security.block_banking_sites,
                'validate_ssl': self.security.validate_ssl,
                'clear_sensitive_data': self.security.clear_sensitive_data,
            },
            'logging': {
                'level': self.logging.level,
                'log_file': self.logging.log_file,
                'log_sensitive_data': self.logging.log_sensitive_data,
            },
        }


def setup_logging(config: LoggingConfig) -> None:
    """
    Set up logging based on configuration.
    
    Args:
        config: Logging configuration
    """
    log_file = Path(config.log_file).expanduser()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, config.level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Set specific logger for this package
    logger = logging.getLogger('alice_browser_automation')
    logger.setLevel(getattr(logging, config.level.upper()))
    
    if not config.log_sensitive_data:
        logger.info("Sensitive data logging is disabled")
