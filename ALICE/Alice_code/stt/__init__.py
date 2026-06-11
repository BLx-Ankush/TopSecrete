"""
Speech-to-Text (STT) Provider Infrastructure

This module provides STT provider infrastructure for neural turn detection
in Alice's conversation fluidity enhancement.

Components:
- STTProvider: Abstract base class for STT providers
- AssemblyAIProvider: AssemblyAI Universal-3 Pro Streaming implementation
- DeepgramProvider: Deepgram Nova-3 implementation
- TranscriptionResult: Data model for transcription results
- STTProviderConfig: Configuration model for STT providers
- STTConfigFactory: Factory for creating providers from environment
- create_stt_provider_from_env: Convenience function to create from environment
- create_stt_provider: Convenience function to create with explicit config

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 15.1, 15.3, 15.9
"""

from .provider import STTProvider
from .assemblyai_provider import AssemblyAIProvider
from .deepgram_provider import DeepgramProvider
from .models import TranscriptionResult, STTProviderConfig
from .config_factory import (
    STTConfigFactory,
    create_stt_provider_from_env,
    create_stt_provider
)

__all__ = [
    'STTProvider',
    'AssemblyAIProvider',
    'DeepgramProvider',
    'TranscriptionResult',
    'STTProviderConfig',
    'STTConfigFactory',
    'create_stt_provider_from_env',
    'create_stt_provider'
]
