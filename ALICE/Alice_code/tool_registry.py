"""
ALICE Tool Registry — Phase 3 Edition
Centralized manager for all of ALICE's agent capabilities.

Changes from Phase 2 → Phase 3:
- ALICE_VISION_TOOLS (legacy alice_vision_tools.py) replaced with new semantic tools.
- alice_whatsapp_automation now uses SemanticVisionEngine — no fragile pixel clicking.
- Legacy vision modules (alice_vision.py, alice_vision_tools.py) are no longer
  loaded as agent tools. They remain on disk for safety but are not registered.
"""

import logging

logger = logging.getLogger(__name__)

# ── Core system automation ────────────────────────────────────────────────────
from alice_personal_safe import (
    enable_personal_mode,
    disable_personal_mode,
    open_application,
    check_personal_mode,
    refresh_app_database_tool,
    show_available_apps,
    perform_multi_app_task,
    create_file_and_open,
    open_vscode_new_window,
    open_browser,
    capture_screenshot,
    adjust_brightness,
    search_files_system,
    advanced_system_operations,
)

# ── New semantic vision tools (resolution-independent) ────────────────────────
try:
    from alice_app_automation import semantic_click, semantic_type_into
    SEMANTIC_APP_TOOLS = [semantic_click, semantic_type_into]
    logger.info("✅ [ToolRegistry] Semantic vision tools loaded (semantic_click, semantic_type_into)")
except ImportError as e:
    logger.warning(f"⚠️  [ToolRegistry] Semantic app tools not available: {e}")
    SEMANTIC_APP_TOOLS = []

# ── WhatsApp automation (semantic vision edition) ─────────────────────────────
try:
    from alice_whatsapp_automation import (
        send_whatsapp_message,
        open_whatsapp_chat,
        whatsapp_automation_help,
    )
    WHATSAPP_TOOLS = [send_whatsapp_message, open_whatsapp_chat, whatsapp_automation_help]
    logger.info("✅ [ToolRegistry] WhatsApp automation loaded (semantic vision edition)")
except ImportError as e:
    logger.warning(f"⚠️  [ToolRegistry] WhatsApp automation not available: {e}")
    WHATSAPP_TOOLS = []

# ── Hardware control tools (Raspberry Pi servo + ultrasonic) ─────────────────
try:
    from alice_servo_control import control_servo_motor, get_ultrasonic_distance
    HARDWARE_TOOLS = [control_servo_motor, get_ultrasonic_distance]
    logger.info("✅ [ToolRegistry] Hardware tools loaded")
except ImportError as e:
    logger.warning(f"⚠️  [ToolRegistry] Hardware tools not available: {e}")
    HARDWARE_TOOLS = []

# NOTE: Legacy alice_vision_tools.py (ALICE_VISION_TOOLS) is intentionally NOT
# loaded here. The new semantic_click / semantic_type_into tools in
# alice_app_automation.py supersede all old vision tools.
# alice_vision.py and alice_vision_tools.py remain on disk as safety archives.


class ToolRegistry:
    """
    Centralized manager for ALICE's capabilities.
    Returns all registered tools as a flat list for GeminiStreamingClient.
    """

    @staticmethod
    async def get_all_tools(browser_automation_available: bool = True) -> list:
        """
        Build and return the complete list of ALICE tools.

        Args:
            browser_automation_available: Whether to attempt loading browser automation.

        Returns:
            List of all registered tool functions.
        """
        # Browser automation (Playwright-based)
        browser_tools = []
        if browser_automation_available:
            try:
                from alice_app_automation import initialize_browser_automation, get_browser_automation_tools
                logger.info("[ToolRegistry] Initializing browser automation engine...")
                await initialize_browser_automation()
                browser_tools = get_browser_automation_tools()
                logger.info(f"✅ [ToolRegistry] Browser automation ready ({len(browser_tools)} tools)")
            except Exception as e:
                logger.error(f"[ToolRegistry] Browser automation failed to load: {e}")
                logger.warning("[ToolRegistry] Continuing without browser automation")

        base_tools = [
            # System automation
            enable_personal_mode,
            disable_personal_mode,
            open_application,
            check_personal_mode,
            refresh_app_database_tool,
            show_available_apps,
            perform_multi_app_task,
            create_file_and_open,
            open_vscode_new_window,
            open_browser,
            capture_screenshot,
            adjust_brightness,
            search_files_system,
            advanced_system_operations,
        ]

        all_tools = (
            base_tools
            + SEMANTIC_APP_TOOLS   # semantic_click, semantic_type_into
            + WHATSAPP_TOOLS       # send_whatsapp_message, open_whatsapp_chat
            + HARDWARE_TOOLS       # servo, ultrasonic (Raspberry Pi)
            + browser_tools        # Playwright browser automation
        )

        logger.info(
            f"✅ [ToolRegistry] {len(all_tools)} tools registered total "
            f"(base={len(base_tools)}, semantic={len(SEMANTIC_APP_TOOLS)}, "
            f"whatsapp={len(WHATSAPP_TOOLS)}, hardware={len(HARDWARE_TOOLS)}, "
            f"browser={len(browser_tools)})"
        )
        return all_tools
