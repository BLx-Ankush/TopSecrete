"""
Alice WhatsApp Automation — Semantic Vision Edition
Sends messages via WhatsApp Desktop using Gemini-powered semantic clicking.
ALL fragile pyautogui pixel-coordinate clicking has been removed.
ALICE now describes what she wants to interact with in plain English and
SemanticVisionEngine locates it visually — immune to resolution or layout changes.
"""

import asyncio
import logging
from livekit.agents import function_tool
from alice_personal_safe import open_application

logger = logging.getLogger(__name__)

# ── Semantic Vision (replaces all pyautogui pixel-math) ──────────────────────
try:
    from alice_semantic_vision import get_semantic_vision_engine
    SEMANTIC_VISION_AVAILABLE = True
    logger.info("✅ [WhatsApp] SemanticVisionEngine loaded")
except ImportError as e:
    SEMANTIC_VISION_AVAILABLE = False
    logger.warning(f"⚠️  [WhatsApp] SemanticVisionEngine not available: {e}")


async def _whatsapp_send_flow(contact_name: str, message: str) -> str:
    """
    Core WhatsApp send flow using semantic vision at every click point.
    Returns a result string (success or error).
    """
    if not SEMANTIC_VISION_AVAILABLE:
        return (
            "❌ Semantic Vision not available. "
            "Please ensure alice_semantic_vision.py and its dependencies (Pillow, httpx) are installed."
        )

    engine = get_semantic_vision_engine()

    # Step 1: Open WhatsApp
    logger.info("[WhatsApp] Opening WhatsApp Desktop...")
    open_result = await open_application("whatsapp")
    if "❌" in open_result:
        return f"❌ Could not open WhatsApp: {open_result}"
    await asyncio.sleep(3)  # Wait for app to load

    # Step 2: Open the search box using Ctrl+F (reliable keyboard shortcut)
    import pyautogui
    logger.info("[WhatsApp] Opening search with Ctrl+F...")
    pyautogui.hotkey("ctrl", "f")
    await asyncio.sleep(1.5)

    # Step 3: Type the contact name into the search box (semantic)
    logger.info(f"[WhatsApp] Typing contact name: {contact_name}")
    typed = await engine.type_into_element(
        "the WhatsApp search input box at the top of the chat list", contact_name
    )
    if not typed:
        # Fallback: just type directly since Ctrl+F already focused the search
        pyautogui.typewrite(contact_name, interval=0.05)
    await asyncio.sleep(2)

    # Step 4: Press Down + Enter to select the first search result (keyboard nav — reliable)
    logger.info("[WhatsApp] Selecting first search result via keyboard...")
    pyautogui.press("down")
    await asyncio.sleep(0.5)
    pyautogui.press("enter")
    await asyncio.sleep(2)

    # Step 5: Verify chat opened — check WhatsApp window still exists
    try:
        import pygetwindow as gw
        wa_windows = [w for w in gw.getAllWindows() if "whatsapp" in w.title.lower()]
        if not wa_windows:
            return "❌ WhatsApp was accidentally closed during contact selection. Please try again."
        wa_windows[0].activate()
    except ImportError:
        pass  # pygetwindow optional — continue without verification
    await asyncio.sleep(1)

    # Step 6: Click the message input box (semantic — works regardless of resolution)
    logger.info("[WhatsApp] Clicking message input box...")
    clicked = await engine.click_element(
        "the WhatsApp message input box at the bottom of the chat — where you type messages"
    )
    if not clicked:
        # Fallback: try clicking the send button area then tabbing
        logger.warning("[WhatsApp] Could not find message box by description — trying Tab fallback")
        pyautogui.hotkey("alt", "tab")  # ensure WhatsApp is focused
        await asyncio.sleep(0.5)
        pyautogui.press("tab")
        await asyncio.sleep(0.3)
    await asyncio.sleep(0.5)

    # Step 7: Clear any existing text and type the message
    pyautogui.hotkey("ctrl", "a")
    await asyncio.sleep(0.2)
    pyautogui.press("delete")
    await asyncio.sleep(0.2)

    logger.info(f"[WhatsApp] Typing message: {message[:50]}...")
    # Use clipboard paste for full Unicode support (avoids typewrite ASCII limitation)
    try:
        import pyperclip
        pyperclip.copy(message)
        pyautogui.hotkey("ctrl", "v")
    except ImportError:
        # Fallback char-by-char if pyperclip not installed
        for char in message:
            pyautogui.typewrite(char, interval=0.04)
    await asyncio.sleep(0.5)

    # Step 8: Send — press Enter
    logger.info("[WhatsApp] Sending message...")
    pyautogui.press("enter")
    await asyncio.sleep(1)

    return "success"


@function_tool(
    name="send_whatsapp_message",
    description=(
        "WhatsApp Desktop पर किसी contact को message भेजने के लिए। "
        "Uses Gemini Vision to locate the search box and message field automatically — "
        "works regardless of screen resolution or window position."
    )
)
async def send_whatsapp_message(contact_name: str, message: str) -> str:
    """
    Send a WhatsApp message to a contact using semantic vision.

    Args:
        contact_name: Name of the contact to message (as saved in WhatsApp).
        message: The message text to send.
    """
    try:
        result = await _whatsapp_send_flow(contact_name, message)
        if result == "success":
            return (
                f"✅ **WhatsApp Message Sent!**\n\n"
                f"👤 **To**: {contact_name}\n"
                f"💬 **Message**: {message[:100]}{'...' if len(message) > 100 else ''}\n\n"
                f"📱 Message भेज दिया गया है! 🚀"
            )
        return result
    except Exception as e:
        logger.error(f"[WhatsApp] send_whatsapp_message failed: {e}", exc_info=True)
        return (
            f"❌ **WhatsApp Message Failed**\n\n"
            f"🎯 **Contact**: {contact_name}\n"
            f"❌ **Error**: {str(e)[:100]}\n\n"
            f"💡 Check that WhatsApp Desktop is installed, open, and logged in."
        )


@function_tool(
    name="open_whatsapp_chat",
    description=(
        "WhatsApp में किसी specific contact का chat खोलने के लिए "
        "(without sending a message). Uses Gemini Vision to navigate."
    )
)
async def open_whatsapp_chat(contact_name: str) -> str:
    """
    Open a WhatsApp chat with a specific contact (no message sent).

    Args:
        contact_name: Name of the contact whose chat to open.
    """
    try:
        if not SEMANTIC_VISION_AVAILABLE:
            return "❌ Semantic Vision not available."

        engine = get_semantic_vision_engine()

        import pyautogui
        open_result = await open_application("whatsapp")
        if "❌" in open_result:
            return f"❌ WhatsApp open नहीं हो सका: {open_result}"
        await asyncio.sleep(3)

        pyautogui.hotkey("ctrl", "f")
        await asyncio.sleep(1)

        typed = await engine.type_into_element(
            "WhatsApp search input", contact_name
        )
        if not typed:
            pyautogui.typewrite(contact_name, interval=0.05)
        await asyncio.sleep(2)

        pyautogui.press("down")
        await asyncio.sleep(0.4)
        pyautogui.press("enter")
        await asyncio.sleep(1.5)

        return (
            f"✅ **WhatsApp Chat Opened!**\n\n"
            f"👤 **Contact**: {contact_name}\n"
            f"💬 Chat ready — अब message type करें! 🚀"
        )
    except Exception as e:
        logger.error(f"[WhatsApp] open_whatsapp_chat failed: {e}")
        return f"❌ Chat open करने में error: {str(e)}"


@function_tool
async def whatsapp_automation_help() -> str:
    """Get help about WhatsApp automation capabilities."""
    engine_status = "✅ Gemini Semantic Vision (Active)" if SEMANTIC_VISION_AVAILABLE else "⚠️  Fallback mode (SemanticVision unavailable)"
    return f"""📱 **Alice WhatsApp Automation Help**

🚀 **Available Commands**:
1. **Send Message**: `send_whatsapp_message` — e.g. "Mom को 'Hello' message भेजो"
2. **Open Chat**: `open_whatsapp_chat` — e.g. "Dad का WhatsApp chat खोलो"

🧠 **Vision Engine**: {engine_status}

📋 **Requirements**:
- ✅ WhatsApp Desktop app installed & logged in
- ✅ Internet connection active
- ✅ Contact name as saved in WhatsApp

💡 **How it works (Semantic Vision)**:
1. Opens WhatsApp Desktop
2. Uses Ctrl+F to open search
3. Gemini Vision locates the search box and message field visually
4. Types contact name, selects first result
5. Types and sends message — fully resolution-independent
"""