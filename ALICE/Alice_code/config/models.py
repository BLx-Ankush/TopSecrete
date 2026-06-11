"""
Configuration schema models for ALICE-Hermes Integration.

This module defines Pydantic models for validating and managing configuration
across the integrated system. It preserves ALICE's existing configuration while
adding Hermes Agent's enterprise capabilities.

Author: ALICE-Hermes Integration Team
Version: 1.0.0
"""

from typing import Optional, List, Dict, Any, Union, Literal
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import re


# ============================================================================
# API Key and Credential Models
# ============================================================================

class APIKeyConfig(BaseModel):
    """
    API key configuration with rate limiting support.
    
    Attributes:
        key: The API key value (loaded from environment variable)
        rate_limit: Optional rate limit specification (e.g., "100/min", "1000/hour")
        last_used: Timestamp of last usage (managed at runtime)
        rate_limited_until: Timestamp when rate limit expires (managed at runtime)
    """
    key: str = Field(..., description="API key value")
    rate_limit: Optional[str] = Field(
        None,
        description="Rate limit specification (e.g., '100/min', '1000/hour')"
    )
    
    @field_validator("key")
    @classmethod
    def validate_key(cls, v):
        """Validate API key is not empty."""
        if not v or v.strip() == "":
            raise ValueError("API key cannot be empty")
        return v.strip()
    
    @field_validator("rate_limit")
    @classmethod
    def validate_rate_limit(cls, v):
        """Validate rate limit format."""
        if v is None:
            return v
        
        # Pattern: number/unit where unit is min, hour, day
        pattern = r'^\d+/(min|hour|day)$'
        if not re.match(pattern, v):
            raise ValueError(
                "Rate limit must be in format 'number/unit' "
                "(e.g., '100/min', '1000/hour')"
            )
        return v


# ============================================================================
# LLM Provider Configuration
# ============================================================================

class LLMConfig(BaseModel):
    """
    Multi-provider LLM configuration with fallback support.
    
    Supports multiple LLM providers with automatic fallback, credential rotation,
    and context management. Preserves ALICE's existing Gemini integration while
    adding enterprise-grade reliability.
    
    Attributes:
        provider: Primary LLM provider name
        model: Model identifier for the primary provider
        fallback_providers: Ordered list of fallback providers
        api_keys: Per-provider API key pools for rotation
        max_retries: Maximum retry attempts per provider
        retry_delay: Base delay between retries in seconds
        exponential_backoff: Enable exponential backoff for retries
        context_window: Context window size ("auto" or specific number)
        compression_threshold: Trigger compression at this ratio of context window
        compression_target: Target ratio after compression
        preserve_last_n: Number of recent messages to preserve uncompressed
    """
    provider: str = Field(
        ...,
        description="Primary LLM provider (openrouter, anthropic, openai, google, etc.)"
    )
    model: str = Field(..., description="Model identifier")
    fallback_providers: List[str] = Field(
        default_factory=list,
        description="Ordered list of fallback providers"
    )
    api_keys: Dict[str, List[APIKeyConfig]] = Field(
        default_factory=dict,
        description="API key pools per provider"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts"
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Base retry delay in seconds"
    )
    exponential_backoff: bool = Field(
        default=True,
        description="Enable exponential backoff"
    )
    context_window: Union[int, str] = Field(
        default="auto",
        description="Context window size (auto-detect or specific number)"
    )
    compression_threshold: float = Field(
        default=0.50,
        ge=0.1,
        le=0.9,
        description="Compression trigger threshold (ratio of context window)"
    )
    compression_target: float = Field(
        default=0.20,
        ge=0.05,
        le=0.5,
        description="Target ratio after compression"
    )
    preserve_last_n: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of recent messages to preserve"
    )
    
    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v):
        """Validate provider name."""
        valid_providers = {
            "openrouter", "anthropic", "openai", "google", "gemini",
            "nous", "nvidia", "xiaomi", "huggingface", "custom"
        }
        if v.lower() not in valid_providers:
            raise ValueError(
                f"Provider must be one of: {', '.join(valid_providers)}"
            )
        return v.lower()
    
    @field_validator("context_window")
    @classmethod
    def validate_context_window(cls, v):
        """Validate context window specification."""
        if isinstance(v, str):
            if v != "auto":
                raise ValueError("Context window must be 'auto' or a positive integer")
            return v
        if isinstance(v, int):
            if v <= 0:
                raise ValueError("Context window must be positive")
            return v
        raise ValueError("Context window must be 'auto' or a positive integer")
    
    @model_validator(mode='after')
    def validate_compression_thresholds(self):
        """Validate compression threshold relationships."""
        if self.compression_target >= self.compression_threshold:
            raise ValueError(
                "compression_target must be less than compression_threshold"
            )
        return self


# ============================================================================
# Voice Interaction Configuration
# ============================================================================

class VADConfig(BaseModel):
    """
    Voice Activity Detection configuration.
    
    Preserves ALICE's existing VAD setup with Silero VAD.
    
    Attributes:
        enabled: Enable VAD for turn-taking
        provider: VAD provider (silero)
        threshold: Voice detection threshold (0.0-1.0)
        silence_duration_ms: Silence duration to trigger end of turn
    """
    enabled: bool = Field(default=True, description="Enable VAD")
    provider: str = Field(default="silero", description="VAD provider")
    threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Voice detection threshold"
    )
    silence_duration_ms: int = Field(
        default=400,
        ge=100,
        le=2000,
        description="Silence duration in milliseconds"
    )
    
    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v):
        """Validate VAD provider."""
        valid_providers = {"silero", "webrtc"}
        if v.lower() not in valid_providers:
            raise ValueError(f"VAD provider must be one of: {', '.join(valid_providers)}")
        return v.lower()


class LiveKitConfig(BaseModel):
    """
    LiveKit configuration for voice interaction.
    
    Preserves ALICE's existing LiveKit setup.
    
    Attributes:
        url: LiveKit server URL
        api_key: LiveKit API key
        api_secret: LiveKit API secret
    """
    url: str = Field(..., description="LiveKit server URL")
    api_key: str = Field(..., description="LiveKit API key")
    api_secret: str = Field(..., description="LiveKit API secret")
    
    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        """Validate LiveKit URL format."""
        if not v.startswith(("ws://", "wss://")):
            raise ValueError("LiveKit URL must start with ws:// or wss://")
        return v
    
    @field_validator("api_key", "api_secret")
    @classmethod
    def validate_credentials(cls, v):
        """Validate credentials are not empty."""
        if not v or v.strip() == "":
            raise ValueError("LiveKit credentials cannot be empty")
        return v.strip()


class VoiceConfig(BaseModel):
    """
    Voice interaction configuration.
    
    Preserves ALICE's voice-first interaction with Gemini Realtime Model.
    
    Attributes:
        provider: Voice provider (gemini-realtime)
        model: Gemini model identifier
        livekit: LiveKit configuration
        vad: VAD configuration
        audio_device: Audio input device name (optional)
        enable_nvidia_broadcast: Enable NVIDIA Broadcast integration
    """
    provider: Literal["gemini-realtime"] = Field(
        default="gemini-realtime",
        description="Voice provider"
    )
    model: str = Field(
        default="gemini-2.0-flash-exp",
        description="Gemini model identifier"
    )
    livekit: LiveKitConfig = Field(..., description="LiveKit configuration")
    vad: VADConfig = Field(
        default_factory=VADConfig,
        description="VAD configuration"
    )
    audio_device: Optional[str] = Field(
        None,
        description="Audio input device name"
    )
    enable_nvidia_broadcast: bool = Field(
        default=False,
        description="Enable NVIDIA Broadcast audio processing"
    )


# ============================================================================
# Memory Provider Configuration
# ============================================================================

class MemoryConfig(BaseModel):
    """
    Memory provider configuration.
    
    Supports multiple memory backends with built-in memory as default.
    Preserves ALICE's existing Mem0 integration.
    
    Attributes:
        provider: Active memory provider (builtin, honcho, mem0, etc.)
        builtin_memory_file: Path to MEMORY.md file
        builtin_user_file: Path to USER.md file
        honcho: Honcho-specific configuration
        mem0: Mem0-specific configuration
        supermemory: Supermemory-specific configuration
    """
    provider: str = Field(
        default="builtin",
        description="Active memory provider"
    )
    builtin_memory_file: str = Field(
        default="MEMORY.md",
        description="Built-in memory file"
    )
    builtin_user_file: str = Field(
        default="USER.md",
        description="Built-in user profile file"
    )
    honcho: Optional[Dict[str, Any]] = Field(
        None,
        description="Honcho configuration"
    )
    mem0: Optional[Dict[str, Any]] = Field(
        None,
        description="Mem0 configuration"
    )
    supermemory: Optional[Dict[str, Any]] = Field(
        None,
        description="Supermemory configuration"
    )
    
    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v):
        """Validate memory provider."""
        valid_providers = {
            "builtin", "honcho", "mem0", "supermemory",
            "byterover", "hindsight", "holographic", "openviking", "retaindb"
        }
        if v.lower() not in valid_providers:
            raise ValueError(
                f"Memory provider must be one of: {', '.join(valid_providers)}"
            )
        return v.lower()


# ============================================================================
# Skills System Configuration
# ============================================================================

class SkillsConfig(BaseModel):
    """
    Skills system configuration.
    
    Manages self-improving procedural memory through skills.
    
    Attributes:
        enabled: Enable skills system
        skills_dir: Directory for active skills
        optional_skills_dir: Directory for optional/heavy skills
        auto_create: Automatically create skills from successful tasks
        skills_hub_enabled: Enable Skills Hub integration
        skills_hub_url: Skills Hub API URL
    """
    enabled: bool = Field(default=True, description="Enable skills system")
    skills_dir: str = Field(default="skills", description="Active skills directory")
    optional_skills_dir: str = Field(
        default="optional-skills",
        description="Optional skills directory"
    )
    auto_create: bool = Field(
        default=True,
        description="Auto-create skills from tasks"
    )
    skills_hub_enabled: bool = Field(
        default=False,
        description="Enable Skills Hub integration"
    )
    skills_hub_url: str = Field(
        default="https://agentskills.io",
        description="Skills Hub URL"
    )
    
    @field_validator("skills_hub_url")
    @classmethod
    def validate_url(cls, v):
        """Validate Skills Hub URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Skills Hub URL must start with http:// or https://")
        return v


# ============================================================================
# Tool Registry Configuration
# ============================================================================

class ToolsConfig(BaseModel):
    """
    Tool registry and toolset configuration.
    
    Manages tool discovery, registration, and availability.
    
    Attributes:
        enabled: Enable tool system
        tools_dir: Directory for tool modules
        default_toolset: Default toolset to load
        enabled_toolsets: List of enabled toolsets
        mcp_enabled: Enable MCP tool integration
        mcp_servers: MCP server configurations
    """
    enabled: bool = Field(default=True, description="Enable tool system")
    tools_dir: str = Field(default="tools", description="Tools directory")
    default_toolset: str = Field(
        default="alice-cli",
        description="Default toolset"
    )
    enabled_toolsets: List[str] = Field(
        default_factory=lambda: ["alice-cli"],
        description="Enabled toolsets"
    )
    mcp_enabled: bool = Field(
        default=False,
        description="Enable MCP integration"
    )
    mcp_servers: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="MCP server configurations"
    )


# ============================================================================
# Gateway Configuration
# ============================================================================

class TelegramConfig(BaseModel):
    """Telegram gateway configuration."""
    enabled: bool = Field(default=False, description="Enable Telegram")
    bot_token: Optional[str] = Field(None, description="Bot token")
    allowed_users: List[str] = Field(
        default_factory=list,
        description="Allowed user IDs"
    )
    home_channel: Optional[str] = Field(None, description="Home channel ID")
    dm_pairing: bool = Field(default=True, description="Enable DM pairing")


class DiscordConfig(BaseModel):
    """Discord gateway configuration."""
    enabled: bool = Field(default=False, description="Enable Discord")
    bot_token: Optional[str] = Field(None, description="Bot token")
    allowed_guilds: List[str] = Field(
        default_factory=list,
        description="Allowed guild IDs"
    )
    home_channel: Optional[str] = Field(None, description="Home channel ID")


class GatewayConfig(BaseModel):
    """
    Multi-platform gateway configuration.
    
    Enables cross-platform messaging and conversation continuity.
    
    Attributes:
        enabled: Enable gateway system
        telegram: Telegram configuration
        discord: Discord configuration
        whatsapp: WhatsApp configuration
        slack: Slack configuration
    """
    enabled: bool = Field(default=False, description="Enable gateway")
    telegram: TelegramConfig = Field(
        default_factory=TelegramConfig,
        description="Telegram config"
    )
    discord: DiscordConfig = Field(
        default_factory=DiscordConfig,
        description="Discord config"
    )
    whatsapp: Optional[Dict[str, Any]] = Field(None, description="WhatsApp config")
    slack: Optional[Dict[str, Any]] = Field(None, description="Slack config")


# ============================================================================
# Cron Scheduler Configuration
# ============================================================================

class CronConfig(BaseModel):
    """
    Cron scheduler configuration.
    
    Manages scheduled tasks with natural language specification.
    
    Attributes:
        enabled: Enable cron scheduler
        jobs_file: Path to jobs configuration file
        default_timeout: Default job timeout in seconds
        max_retries: Maximum retry attempts for failed jobs
        log_dir: Directory for cron logs
    """
    enabled: bool = Field(default=False, description="Enable cron scheduler")
    jobs_file: str = Field(default="cron/jobs.yaml", description="Jobs file")
    default_timeout: int = Field(
        default=1800,
        ge=60,
        le=86400,
        description="Default timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Max retry attempts"
    )
    log_dir: str = Field(default="cron/logs", description="Cron logs directory")


# ============================================================================
# Security Configuration
# ============================================================================

class SecurityConfig(BaseModel):
    """
    Security and approval system configuration.
    
    Controls dangerous operation approval and security policies.
    
    Attributes:
        approval_enabled: Enable approval system
        approval_timeout: Approval request timeout in seconds
        trusted_users: List of trusted user IDs
        always_approve: Patterns to always approve
        always_deny: Patterns to always deny
        use_auxiliary_for_approval: Use auxiliary model for risk assessment
        risk_threshold: Risk threshold for approval (0.0-1.0)
    """
    approval_enabled: bool = Field(
        default=True,
        description="Enable approval system"
    )
    approval_timeout: int = Field(
        default=300,
        ge=30,
        le=3600,
        description="Approval timeout in seconds"
    )
    trusted_users: List[str] = Field(
        default_factory=list,
        description="Trusted user IDs"
    )
    always_approve: List[str] = Field(
        default_factory=list,
        description="Always approve patterns"
    )
    always_deny: List[str] = Field(
        default_factory=list,
        description="Always deny patterns"
    )
    use_auxiliary_for_approval: bool = Field(
        default=True,
        description="Use auxiliary model for approval"
    )
    risk_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Risk threshold for approval"
    )


# ============================================================================
# Personality Configuration
# ============================================================================

class PersonalityConfig(BaseModel):
    """
    Personality and behavior configuration.
    
    Preserves ALICE's Hinglish personality and emotional support focus.
    
    Attributes:
        soul_file: Path to SOUL.md personality definition
        language: Primary language (hinglish, english, etc.)
        tone: Response tone (warm, professional, casual)
        proactive_support: Enable proactive emotional support
        enable_coaching: Enable skill coaching
    """
    soul_file: str = Field(default="SOUL.md", description="Personality file")
    language: str = Field(
        default="hinglish",
        description="Primary language"
    )
    tone: str = Field(default="warm", description="Response tone")
    proactive_support: bool = Field(
        default=True,
        description="Proactive emotional support"
    )
    enable_coaching: bool = Field(
        default=True,
        description="Enable skill coaching"
    )
    
    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        """Validate language option."""
        valid_languages = {"hinglish", "english", "hindi"}
        if v.lower() not in valid_languages:
            raise ValueError(
                f"Language must be one of: {', '.join(valid_languages)}"
            )
        return v.lower()
    
    @field_validator("tone")
    @classmethod
    def validate_tone(cls, v):
        """Validate tone option."""
        valid_tones = {"warm", "professional", "casual", "formal"}
        if v.lower() not in valid_tones:
            raise ValueError(f"Tone must be one of: {', '.join(valid_tones)}")
        return v.lower()


# ============================================================================
# Main Configuration
# ============================================================================

class AliceConfig(BaseModel):
    """
    Main ALICE-Hermes integration configuration.
    
    This is the root configuration model that combines all subsystem configurations.
    It preserves ALICE's existing settings while adding Hermes Agent capabilities.
    
    Attributes:
        version: Configuration version for migration support
        alice_home: Path to ALICE data directory
        llm: LLM provider configuration
        voice: Voice interaction configuration
        memory: Memory provider configuration
        skills: Skills system configuration
        tools: Tool registry configuration
        gateway: Multi-platform gateway configuration
        cron: Cron scheduler configuration
        security: Security and approval configuration
        personality: Personality configuration
    """
    version: int = Field(default=1, description="Configuration version")
    alice_home: Path = Field(..., description="ALICE data directory")
    llm: LLMConfig = Field(..., description="LLM configuration")
    voice: VoiceConfig = Field(..., description="Voice configuration")
    memory: MemoryConfig = Field(
        default_factory=MemoryConfig,
        description="Memory configuration"
    )
    skills: SkillsConfig = Field(
        default_factory=SkillsConfig,
        description="Skills configuration"
    )
    tools: ToolsConfig = Field(
        default_factory=ToolsConfig,
        description="Tools configuration"
    )
    gateway: GatewayConfig = Field(
        default_factory=GatewayConfig,
        description="Gateway configuration"
    )
    cron: CronConfig = Field(
        default_factory=CronConfig,
        description="Cron configuration"
    )
    security: SecurityConfig = Field(
        default_factory=SecurityConfig,
        description="Security configuration"
    )
    personality: PersonalityConfig = Field(
        default_factory=PersonalityConfig,
        description="Personality configuration"
    )
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True
    )
    
    @field_validator("alice_home")
    @classmethod
    def validate_alice_home(cls, v):
        """Validate ALICE home directory."""
        if isinstance(v, str):
            v = Path(v)
        return v.expanduser().resolve()
    
    @field_validator("version")
    @classmethod
    def validate_version(cls, v):
        """Validate configuration version."""
        if v < 1:
            raise ValueError("Configuration version must be >= 1")
        return v


# ============================================================================
# Configuration Validation Helpers
# ============================================================================

def validate_config_file(config_dict: Dict[str, Any]) -> AliceConfig:
    """
    Validate a configuration dictionary and return AliceConfig instance.
    
    Args:
        config_dict: Configuration dictionary from YAML
        
    Returns:
        Validated AliceConfig instance
        
    Raises:
        ValidationError: If configuration is invalid
    """
    return AliceConfig(**config_dict)


def get_default_config(alice_home: Path) -> AliceConfig:
    """
    Generate default configuration for ALICE.
    
    Args:
        alice_home: Path to ALICE data directory
        
    Returns:
        Default AliceConfig instance
    """
    return AliceConfig(
        version=1,
        alice_home=alice_home,
        llm=LLMConfig(
            provider="openrouter",
            model="anthropic/claude-3.5-sonnet",
            fallback_providers=["google"],
        ),
        voice=VoiceConfig(
            model="gemini-2.0-flash-exp",
            livekit=LiveKitConfig(
                url="wss://your-livekit-url.livekit.cloud",
                api_key="your_api_key",
                api_secret="your_api_secret",
            ),
        ),
    )
