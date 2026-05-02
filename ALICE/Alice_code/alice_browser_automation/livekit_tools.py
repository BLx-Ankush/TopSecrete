"""
LiveKit tool definitions for Alice agent integration.

This module provides LiveKit function tools for browser automation,
enabling voice-controlled web automation through Alice.

**Validates: Requirements 11.1, 11.2**
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from livekit.agents import function_tool

from .engine import BrowserAutomationEngine
from .types import TaskType
from .exceptions import BrowserAutomationError
from .voice_callbacks import create_voice_callbacks


logger = logging.getLogger(__name__)

# Global engine instance (will be set by agent initialization)
_browser_engine: Optional[BrowserAutomationEngine] = None


def set_browser_engine(engine: BrowserAutomationEngine) -> None:
    """
    Set the global browser automation engine instance.
    
    This should be called during agent initialization.
    
    Args:
        engine: Initialized BrowserAutomationEngine instance
    """
    global _browser_engine
    _browser_engine = engine
    logger.info("Browser automation engine registered with LiveKit tools")


def get_browser_engine() -> BrowserAutomationEngine:
    """
    Get the global browser automation engine instance.
    
    Returns:
        BrowserAutomationEngine instance
        
    Raises:
        RuntimeError: If engine not initialized
    """
    if _browser_engine is None:
        raise RuntimeError(
            "Browser automation engine not initialized. "
            "Call set_browser_engine() during agent startup."
        )
    return _browser_engine


@function_tool(
    name="browser_automation",
    description=(
        "Browser automation के लिए - web bookings, problem solving, या app access। "
        "Flight/hotel booking, food ordering, web research, Gmail/apps access करने के लिए। "
        "Examples: 'Book flight to Paris', 'Find Python error solution', 'Check Gmail inbox'"
    )
)
async def browser_automation(
    task_description: str,
    task_type: str,
    parameters: Optional[str] = None
) -> str:
    """
    Execute browser automation task through voice command.
    
    **Validates: Requirement 11.1** - Recognize intent and invoke Browser_Automation_Engine
    
    Args:
        task_description: Natural language description of the browser task
        task_type: Type of task: "web_booking", "problem_solving", or "app_access"
        parameters: Optional JSON string with task-specific parameters
        
    Returns:
        Summary of task execution with actions taken
        
    Examples:
        - browser_automation("Book a flight to Paris on December 25th", "web_booking", 
                           '{"origin": "SFO", "destination": "CDG", "date": "2026-12-25"}')
        - browser_automation("Find solution for Python import error", "problem_solving", 
                           '{"error": "ModuleNotFoundError: No module named requests"}')
        - browser_automation("Check my Gmail inbox", "app_access", 
                           '{"app": "gmail", "action": "check_inbox"}')
    """
    try:
        engine = get_browser_engine()
        
        # Parse task type
        task_type_enum = TaskType[task_type.upper()]
        
        # Parse parameters if provided
        import json
        params = json.loads(parameters) if parameters else {}
        
        logger.info(
            f"Browser automation request: {task_description} "
            f"(type: {task_type}, params: {params})"
        )
        
        # Create voice callbacks for progress updates
        voice_callbacks = create_voice_callbacks()
        
        # Execute task with progress callback
        result = await engine.execute_task(
            task_description=task_description,
            task_type=task_type_enum,
            parameters=params,
            callback=voice_callbacks.progress_callback
        )
        
        # Format result for voice response
        if result.success:
            response = f"✅ Task completed successfully!\n\n"
            response += f"📋 Summary: {result.summary}\n\n"
            response += f"⚡ Actions taken: {len(result.actions_taken)}\n"
            response += f"⏱️ Duration: {result.duration_seconds:.1f} seconds\n"
            
            if result.extracted_data:
                response += f"\n📊 Extracted data:\n"
                for key, value in result.extracted_data.items():
                    response += f"  • {key}: {value}\n"
            
            return response
        else:
            response = f"❌ Task failed: {result.error}\n\n"
            response += f"📋 Summary: {result.summary}\n"
            response += f"⚡ Actions attempted: {len(result.actions_taken)}\n"
            return response
            
    except KeyError:
        return (
            f"❌ Invalid task type: {task_type}\n\n"
            f"Valid types: web_booking, problem_solving, app_access"
        )
    except json.JSONDecodeError as e:
        return f"❌ Invalid parameters JSON: {str(e)}"
    except RuntimeError as e:
        return f"❌ Browser automation not initialized: {str(e)}"
    except BrowserAutomationError as e:
        return f"❌ Browser automation error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in browser_automation: {e}", exc_info=True)
        return f"❌ Unexpected error: {str(e)}"


@function_tool(
    name="list_browser_profiles",
    description=(
        "Browser profiles की list देखने के लिए - saved login sessions और preferences। "
        "Profiles में Gmail, banking, shopping sites के saved logins होते हैं।"
    )
)
async def list_browser_profiles() -> str:
    """
    List all available browser profiles.
    
    **Validates: Requirement 11.2** - Provide status updates
    
    Returns:
        Formatted list of profiles with their names and last used dates
        
    Example output:
        📁 Available Browser Profiles:
        
        1. default (Last used: 2 hours ago)
           • 5 saved sessions
           
        2. work (Last used: 1 day ago)
           • 12 saved sessions
           
        3. personal (Last used: 3 days ago)
           • 8 saved sessions
    """
    try:
        engine = get_browser_engine()
        
        # Get profiles from profile manager
        profiles = engine.profile_manager.list_profiles()
        
        if not profiles:
            return (
                "📁 No browser profiles found.\n\n"
                "Profiles will be created automatically when you use browser automation."
            )
        
        response = "📁 Available Browser Profiles:\n\n"
        
        for i, profile_name in enumerate(profiles, 1):
            profile_info = engine.profile_manager.get_profile_info(profile_name)
            
            last_used = profile_info.get('last_used')
            if last_used:
                # Calculate time ago
                time_ago = _format_time_ago(last_used)
                response += f"{i}. {profile_name} (Last used: {time_ago})\n"
            else:
                response += f"{i}. {profile_name} (Never used)\n"
            
            # Add session count if available
            session_count = profile_info.get('session_count', 0)
            response += f"   • {session_count} saved sessions\n\n"
        
        return response
        
    except RuntimeError as e:
        return f"❌ Browser automation not initialized: {str(e)}"
    except Exception as e:
        logger.error(f"Error listing profiles: {e}", exc_info=True)
        return f"❌ Error listing profiles: {str(e)}"


@function_tool(
    name="check_browser_automation_status",
    description=(
        "Browser automation की status check करने के लिए - Ollama, Qwen model, "
        "Playwright, और active sessions की availability। "
        "System ready है या नहीं check करता है।"
    )
)
async def check_browser_automation_status() -> str:
    """
    Check if browser automation is ready and available.
    
    **Validates: Requirement 11.2** - Provide status updates
    
    Returns:
        Status of Ollama service, Qwen model, Playwright, and active sessions
        
    Example output:
        🔍 Browser Automation Status:
        
        ✅ Ollama Service: Running
        ✅ Qwen Model: Available (qwen2.5-coder:3b)
        ✅ Playwright: Installed
        ✅ Browser Engine: Initialized
        
        📊 Active Sessions: 2/3
        • example.com (active for 5 minutes)
        • gmail.com (active for 12 minutes)
        
        ✅ System ready for browser automation!
    """
    try:
        engine = get_browser_engine()
        
        response = "🔍 Browser Automation Status:\n\n"
        
        # Check Ollama service
        try:
            ollama_status = await engine.livekit_bridge.validate_model_availability()
            if ollama_status:
                response += "✅ Ollama Service: Running\n"
                response += f"✅ Qwen Model: Available ({engine.config.qwen.model})\n"
            else:
                response += "❌ Ollama Service: Not available\n"
                response += "❌ Qwen Model: Not available\n"
        except Exception as e:
            response += f"❌ Ollama/Qwen: Error - {str(e)}\n"
        
        # Check Playwright
        if engine.session_manager._browser:
            response += "✅ Playwright: Installed and ready\n"
        else:
            response += "⚠️ Playwright: Not initialized\n"
        
        # Check engine initialization
        if engine.is_initialized:
            response += "✅ Browser Engine: Initialized\n\n"
        else:
            response += "❌ Browser Engine: Not initialized\n\n"
            return response + "❌ System not ready. Please initialize browser automation first."
        
        # Get active sessions
        active_sessions = engine.get_active_sessions()
        max_sessions = engine.config.browser.max_concurrent_sessions
        
        response += f"📊 Active Sessions: {len(active_sessions)}/{max_sessions}\n"
        
        if active_sessions:
            for session in active_sessions:
                domain = session.domain
                active_time = datetime.now() - session.last_activity
                minutes = int(active_time.total_seconds() / 60)
                response += f"• {domain} (active for {minutes} minutes)\n"
        else:
            response += "• No active sessions\n"
        
        response += "\n✅ System ready for browser automation!"
        return response
        
    except RuntimeError as e:
        return (
            "❌ Browser automation not initialized.\n\n"
            "The browser automation engine needs to be initialized during agent startup. "
            "Please contact the administrator."
        )
    except Exception as e:
        logger.error(f"Error checking status: {e}", exc_info=True)
        return f"❌ Error checking status: {str(e)}"


def _format_time_ago(timestamp: datetime) -> str:
    """
    Format a timestamp as a human-readable time ago string.
    
    Args:
        timestamp: Datetime to format
        
    Returns:
        Human-readable string like "2 hours ago", "3 days ago"
    """
    now = datetime.now()
    delta = now - timestamp
    
    seconds = delta.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"


# Export all tools for easy import
BROWSER_AUTOMATION_TOOLS = [
    browser_automation,
    list_browser_profiles,
    check_browser_automation_status
]
