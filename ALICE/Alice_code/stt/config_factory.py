"""
STT Provider Configuration Factory.

This module provides factory functions to create STT provider instances
from environment variables and configuration.

Requirements: 2.1, 2.2, 15.1, 15.3, 15.9
"""

import os
import logging
from typing import Optional

from .provider import STTProvider
from .assemblyai_provider import AssemblyAIProvider
from .deepgram_provider import DeepgramProvider
from .models import STTProviderConfig

logger = logging.getLogger(__name__)


class STTConfigFactory:
    """
    Factory for creating STT provider instances from environment variables.
    
    This factory reads configuration from environment variables and creates
    the appropriate STT provider instance (AssemblyAI or Deepgram).
    
    Environment Variables:
    - STT_PROVIDER: Provider type ("assemblyai" or "deepgram")
    - ASSEMBLYAI_API_KEY: AssemblyAI API key
    - DEEPGRAM_API_KEY: Deepgram API key
    - STT_SAMPLE_RATE: Audio sample rate in Hz (default: 24000)
    - STT_ENCODING: Audio encoding format (default: "pcm_s16le")
    - STT_CHANNELS: Number of audio channels (default: 1)
    - STT_CONNECTION_TIMEOUT_S: Connection timeout in seconds (default: 10)
    - STT_RECONNECT_ATTEMPTS: Max reconnection attempts (default: 3)
    - STT_ENABLE_END_OF_UTTERANCE: Enable end-of-utterance detection (default: true)
    
    Requirements: 2.1, 2.2, 15.1, 15.3, 15.9
    """
    
    # Default configuration values
    DEFAULT_PROVIDER = "assemblyai"
    DEFAULT_SAMPLE_RATE = 24000
    DEFAULT_ENCODING = "pcm_s16le"
    DEFAULT_CHANNELS = 1
    DEFAULT_CONNECTION_TIMEOUT_S = 10
    DEFAULT_RECONNECT_ATTEMPTS = 3
    DEFAULT_ENABLE_END_OF_UTTERANCE = True
    
    @classmethod
    def create_from_env(cls) -> STTProvider:
        """
        Create STT provider from environment variables.
        
        This method reads configuration from environment variables and
        creates the appropriate STT provider instance.
        
        Returns:
            STTProvider instance (AssemblyAI or Deepgram)
        
        Raises:
            ValueError: If configuration is invalid or API key is missing
        
        Requirements: 2.1, 2.2, 15.1, 15.3, 15.9
        """
        # Read provider type from environment
        provider_type = os.getenv("STT_PROVIDER", cls.DEFAULT_PROVIDER).lower()
        
        logger.info(f"Creating STT provider: {provider_type}")
        
        # Get API key based on provider type
        if provider_type == "assemblyai":
            api_key = os.getenv("ASSEMBLYAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "ASSEMBLYAI_API_KEY environment variable is required "
                    "when STT_PROVIDER=assemblyai"
                )
        
        elif provider_type == "deepgram":
            api_key = os.getenv("DEEPGRAM_API_KEY")
            if not api_key:
                raise ValueError(
                    "DEEPGRAM_API_KEY environment variable is required "
                    "when STT_PROVIDER=deepgram"
                )
        
        else:
            raise ValueError(
                f"Invalid STT_PROVIDER: {provider_type}. "
                f"Must be 'assemblyai' or 'deepgram'"
            )
        
        # Read configuration from environment
        config = cls.create_config_from_env(provider_type, api_key)
        
        # Create provider instance
        return cls.create_provider(config)
    
    @classmethod
    def create_config_from_env(
        cls,
        provider_type: str,
        api_key: str
    ) -> STTProviderConfig:
        """
        Create STT provider configuration from environment variables.
        
        Args:
            provider_type: Provider type ("assemblyai" or "deepgram")
            api_key: API key for authentication
        
        Returns:
            STTProviderConfig instance
        
        Requirements: 2.1, 2.2, 2.7, 15.1, 15.3, 15.9
        """
        # Read configuration from environment with defaults
        sample_rate = int(os.getenv("STT_SAMPLE_RATE", cls.DEFAULT_SAMPLE_RATE))
        encoding = os.getenv("STT_ENCODING", cls.DEFAULT_ENCODING)
        channels = int(os.getenv("STT_CHANNELS", cls.DEFAULT_CHANNELS))
        connection_timeout_s = int(
            os.getenv("STT_CONNECTION_TIMEOUT_S", cls.DEFAULT_CONNECTION_TIMEOUT_S)
        )
        reconnect_attempts = int(
            os.getenv("STT_RECONNECT_ATTEMPTS", cls.DEFAULT_RECONNECT_ATTEMPTS)
        )
        enable_end_of_utterance = os.getenv(
            "STT_ENABLE_END_OF_UTTERANCE",
            str(cls.DEFAULT_ENABLE_END_OF_UTTERANCE)
        ).lower() in ("true", "1", "yes")
        
        # Create configuration
        config = STTProviderConfig(
            provider_type=provider_type,
            api_key=api_key,
            sample_rate=sample_rate,
            encoding=encoding,
            channels=channels,
            connection_timeout_s=connection_timeout_s,
            reconnect_attempts=reconnect_attempts,
            enable_end_of_utterance=enable_end_of_utterance
        )
        
        logger.info(
            f"STT configuration created: provider={provider_type}, "
            f"sample_rate={sample_rate}Hz, channels={channels}"
        )
        
        return config
    
    @classmethod
    def create_provider(cls, config: STTProviderConfig) -> STTProvider:
        """
        Create STT provider instance from configuration.
        
        Args:
            config: STT provider configuration
        
        Returns:
            STTProvider instance (AssemblyAI or Deepgram)
        
        Raises:
            ValueError: If provider type is invalid
        
        Requirements: 2.1, 2.2, 2.5, 2.6
        """
        if config.provider_type == "assemblyai":
            return AssemblyAIProvider(config)
        
        elif config.provider_type == "deepgram":
            return DeepgramProvider(config)
        
        else:
            raise ValueError(
                f"Invalid provider type: {config.provider_type}. "
                f"Must be 'assemblyai' or 'deepgram'"
            )
    
    @classmethod
    def create_provider_with_defaults(
        cls,
        provider_type: str,
        api_key: str,
        **kwargs
    ) -> STTProvider:
        """
        Create STT provider with default configuration and optional overrides.
        
        This is a convenience method for creating providers with minimal
        configuration, using defaults for most parameters.
        
        Args:
            provider_type: Provider type ("assemblyai" or "deepgram")
            api_key: API key for authentication
            **kwargs: Optional configuration overrides
        
        Returns:
            STTProvider instance
        
        Requirements: 2.1, 2.2
        """
        # Create config with defaults
        config = STTProviderConfig(
            provider_type=provider_type,
            api_key=api_key,
            sample_rate=kwargs.get("sample_rate", cls.DEFAULT_SAMPLE_RATE),
            encoding=kwargs.get("encoding", cls.DEFAULT_ENCODING),
            channels=kwargs.get("channels", cls.DEFAULT_CHANNELS),
            connection_timeout_s=kwargs.get(
                "connection_timeout_s",
                cls.DEFAULT_CONNECTION_TIMEOUT_S
            ),
            reconnect_attempts=kwargs.get(
                "reconnect_attempts",
                cls.DEFAULT_RECONNECT_ATTEMPTS
            ),
            enable_end_of_utterance=kwargs.get(
                "enable_end_of_utterance",
                cls.DEFAULT_ENABLE_END_OF_UTTERANCE
            )
        )
        
        return cls.create_provider(config)


def create_stt_provider_from_env() -> STTProvider:
    """
    Convenience function to create STT provider from environment variables.
    
    Returns:
        STTProvider instance configured from environment
    
    Raises:
        ValueError: If configuration is invalid or API key is missing
    
    Requirements: 2.1, 2.2, 15.1, 15.3, 15.9
    """
    return STTConfigFactory.create_from_env()


def create_stt_provider(
    provider_type: str,
    api_key: str,
    **kwargs
) -> STTProvider:
    """
    Convenience function to create STT provider with explicit configuration.
    
    Args:
        provider_type: Provider type ("assemblyai" or "deepgram")
        api_key: API key for authentication
        **kwargs: Optional configuration overrides
    
    Returns:
        STTProvider instance
    
    Requirements: 2.1, 2.2
    """
    return STTConfigFactory.create_provider_with_defaults(
        provider_type,
        api_key,
        **kwargs
    )
