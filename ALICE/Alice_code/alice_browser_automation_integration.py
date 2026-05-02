"""
Alice Browser Automation Integration Module

This module provides integration between Alice voice agent and the browser automation engine.
It handles initialization, cleanup, and tool registration.

**Validates: Requirements 11.1, 11.4**
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional

from alice_browser_automation.engine import BrowserAutomationEngine
from alice_browser_automation.config import Config
from alice_browser_automation.livekit_tools import (
    set_browser_engine,
    BROWSER_AUTOMATION_TOOLS
)
from alice_browser_automation.exceptions import BrowserAutomationError


logger = logging.getLogger(__name__)

# Global engine instance
_global_engine: Optional[BrowserAutomationEngine] = None
_initialization_lock = asyncio.Lock()


async def initialize_browser_automation(
    config_path: Optional[str] = None
) -> BrowserAutomationEngine:
    """
    Initialize browser automation engine for Alice agent.
    
    This function should be called during agent startup to initialize
    the browser automation engine and register tools.
    
    **Validates: Requirement 11.1** - Initialize browser automation
    **Validates: Requirement 11.4** - Add engine cleanup on agent shutdown
    
    Args:
        config_path: Optional path to configuration file.
                    If None, uses default config locations.
    
    Returns:
        Initialized BrowserAutomationEngine instance
        
    Raises:
        BrowserAutomationError: If initialization fails
    """
    global _global_engine
    
    async with _initialization_lock:
        # Return existing engine if already initialized
        if _global_engine is not None and _global_engine.is_initialized:
            logger.info("Browser automation engine already initialized")
            return _global_engine
        
        try:
            logger.info("Initializing browser automation engine...")
            
            # Load configuration
            if config_path:
                config = Config.load(Path(config_path))
            else:
                # Try default locations
                config = Config.load()
            
            # Create engine instance
            engine = BrowserAutomationEngine(config)
            
            # Initialize engine (sets up Playwright, Ollama, etc.)
            await engine.initialize()
            
            # Register engine with LiveKit tools
            set_browser_engine(engine)
            
            # Store global reference
            _global_engine = engine
            
            logger.info("✅ Browser automation engine initialized successfully")
            logger.info(f"   • Ollama: {config.qwen.host}")
            logger.info(f"   • Model: {config.qwen.model}")
            logger.info(f"   • Max sessions: {config.browser.max_concurrent_sessions}")
            
            return engine
            
        except Exception as e:
            logger.error(f"Failed to initialize browser automation: {e}", exc_info=True)
            raise BrowserAutomationError(
                f"Browser automation initialization failed: {str(e)}"
            ) from e


async def shutdown_browser_automation() -> None:
    """
    Shutdown browser automation engine and clean up resources.
    
    This function should be called during agent shutdown to properly
    clean up browser sessions and resources.
    
    **Validates: Requirement 11.4** - Engine cleanup on agent shutdown
    """
    global _global_engine
    
    if _global_engine is None:
        logger.info("Browser automation engine not initialized, nothing to shutdown")
        return
    
    try:
        logger.info("Shutting down browser automation engine...")
        
        await _global_engine.shutdown()
        
        _global_engine = None
        
        logger.info("✅ Browser automation engine shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during browser automation shutdown: {e}", exc_info=True)


def get_browser_automation_tools() -> list:
    """
    Get the list of browser automation tools for agent registration.
    
    **Validates: Requirement 11.1** - Register browser automation tools
    
    Returns:
        List of browser automation function tools
    """
    return BROWSER_AUTOMATION_TOOLS


async def check_browser_automation_available() -> bool:
    """
    Check if browser automation is available and ready.
    
    Returns:
        True if browser automation is initialized and ready, False otherwise
    """
    global _global_engine
    
    if _global_engine is None:
        return False
    
    return _global_engine.is_initialized


# Optional: Auto-initialize on import (can be disabled)
_AUTO_INITIALIZE = False  # Set to True to auto-initialize

if _AUTO_INITIALIZE:
    # Note: This won't work in sync context, needs to be called from async context
    logger.info("Auto-initialization is enabled but requires async context")
