"""
Alice Browser Automation Package

This package extends Alice's capabilities by integrating browser automation powered by
a local Qwen Coder 2.5 3B model via Ollama. It enables Alice to handle complex web-based
tasks through voice commands using a DOM-first approach with browser-use and Playwright.

Key Components:
- BrowserAutomationEngine: Core orchestrator for browser automation tasks
- DOMParser: Extracts structured DOM data and accessibility trees
- QwenModelClient: Interface with Ollama for Qwen model inference
- LiveKitQwenBridge: Connects Alice's LiveKit agent to local Qwen model
- ChromeProfileManager: Manages persistent browser profiles
- SessionManager: Manages browser session lifecycle
- OTPHandler: Handles OTP verification through voice interaction
- ErrorHandler: Manages error recovery strategies

Action Suites:
- WebBookingsActionSuite: Handles travel, food, and event bookings
- ProblemSolvingActionSuite: Researches and solves desktop problems
- ApplicationAccessActionSuite: Accesses web applications with persistent login
"""

import logging
from pathlib import Path

__version__ = "0.1.0"
__author__ = "Alice Development Team"

# Set up package logger
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
log_dir = Path.home() / ".alice" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# Import main components for easy access
from alice_browser_automation.engine import BrowserAutomationEngine
from alice_browser_automation.types import (
    TaskType,
    ActionType,
    SessionState,
    BrowserTask,
    BrowserAction,
    TaskResult,
)
from alice_browser_automation.exceptions import (
    BrowserAutomationError,
    ElementNotFoundError,
    PageLoadTimeoutError,
    InvalidActionError,
    NetworkError,
    SessionCrashedError,
    QwenModelUnavailableError,
)

# Import LiveKit tools for Alice integration (optional)
try:
    from alice_browser_automation.livekit_tools import (
        browser_automation,
        list_browser_profiles,
        check_browser_automation_status,
    )
    LIVEKIT_TOOLS_AVAILABLE = True
except ImportError:
    # LiveKit not installed, tools not available
    LIVEKIT_TOOLS_AVAILABLE = False
    browser_automation = None
    list_browser_profiles = None
    check_browser_automation_status = None

__all__ = [
    # Main engine
    "BrowserAutomationEngine",
    # Types
    "TaskType",
    "ActionType",
    "SessionState",
    "BrowserTask",
    "BrowserAction",
    "TaskResult",
    # Exceptions
    "BrowserAutomationError",
    "ElementNotFoundError",
    "PageLoadTimeoutError",
    "InvalidActionError",
    "NetworkError",
    "SessionCrashedError",
    "QwenModelUnavailableError",
    # LiveKit tools
    "browser_automation",
    "list_browser_profiles",
    "check_browser_automation_status",
]
