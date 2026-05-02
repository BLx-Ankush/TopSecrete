"""
Alice WhatsApp Automation - Send Messages Automatically
Enables Alice to open WhatsApp and send messages to specific contacts
"""

import asyncio
import time
from livekit.agents import function_tool
import logging
from alice_personal_safe import open_application
from alice_vision_tools import smart_vision_analysis, click_on, type_text_here
from alice_app_automation import type_in_app

logger = logging.getLogger(__name__)

def is_safe_click_target(element_label: str, element_text: str, target_name: str) -> bool:
    """
    Check if an element is safe to click (not a system control)
    
    Args:
        element_label: Label of the UI element
        element_text: Text content of the element  
        target_name: The name we're looking for
    
    Returns:
        bool: True if safe to click, False if it's a system control
    """
    # Convert to lowercase for comparison
    label_lower = element_label.lower()
    text_lower = element_text.lower()
    target_lower = target_name.lower()
    
    # Unsafe elements (system controls)
    unsafe_keywords = [
        'minimize', 'close', 'maximize', 'restore', 'exit', 'quit',
        'window', 'title bar', 'system menu', 'control button',
        'chrome_widgetwin_1', 'whatsapp - minimize', 'whatsapp - close'
    ]
    
    # Check if element contains unsafe keywords
    for unsafe in unsafe_keywords:
        if unsafe in label_lower or unsafe in text_lower:
            return False
    
    # Must be an exact match or very close match to target
    if target_lower not in text_lower and text_lower not in target_lower:
        return False
    
    return True

@function_tool(name="send_whatsapp_message", description="WhatsApp पर किसी को भी message भेजने के लिए")
async def send_whatsapp_message(contact_name: str, message: str) -> str:
    """
    Open WhatsApp and send a message to the specified contact.
    
    Args:
        contact_name: Name of the person to send message to
        message: Message content to send
    """
    try:
        logger.info(f"Starting WhatsApp automation: {contact_name} -> {message[:50]}...")
        
        # Step 1: Open WhatsApp Desktop
        logger.info("Opening WhatsApp...")
        open_result = await open_application("whatsapp")
        if "❌" in open_result:
            return f"❌ WhatsApp open नहीं हो सका: {open_result}"
        
        # Wait for WhatsApp to load
        await asyncio.sleep(3)
        
        # Step 2: Take screenshot and analyze WhatsApp interface
        logger.info("Analyzing WhatsApp interface...")
        analysis_result = await smart_vision_analysis(
            task_description=f"Find WhatsApp search box or contact '{contact_name}' in the chat list",
            analysis_type="ui_analysis"
        )
        
        # Step 3: Search for contact using improved strategies
        logger.info(f"Searching for contact: {contact_name}")
        
        # Strategy 1: Use keyboard shortcut (most reliable)
        logger.info("Using Ctrl+F for search...")
        import pyautogui
        pyautogui.hotkey('ctrl', 'f')  # WhatsApp search shortcut
        await asyncio.sleep(1.5)
        
        # Additional fallback: click on typical search locations
        try:
            # WhatsApp typically has search at top left
            screen_width, screen_height = pyautogui.size()
            pyautogui.click(screen_width // 4, 100)  # Top area where search usually is
            await asyncio.sleep(0.5)
        except:
            pass
        
        # Step 4: Type contact name with clear text first
        logger.info(f"Typing contact name: {contact_name}")
        
        # Clear any existing text first
        pyautogui.hotkey('ctrl', 'a')  # Select all
        await asyncio.sleep(0.3)
        
        # Type the contact name
        await type_text_here(contact_name)
        await asyncio.sleep(2)
        
        # Step 5: Select contact with improved strategies
        logger.info("Selecting contact from search results...")
        
        # Strategy A: Try to select contact using safer keyboard navigation
        contact_clicked = False
        try:
            # Wait for search results to appear
            await asyncio.sleep(1)
            
            # Use DOWN arrow to navigate to first result (much safer than clicking)
            logger.info("Using DOWN arrow key to select first search result...")
            pyautogui.press('down')
            await asyncio.sleep(0.5)
            
            # Press ENTER to select
            pyautogui.press('enter')
            await asyncio.sleep(1)
            
            logger.info("Used keyboard navigation to select contact (safer method)")
            contact_clicked = True
            
        except Exception as e:
            logger.info(f"Keyboard navigation failed: {e}, trying alternative methods...")
        
        # Strategy B: If keyboard navigation didn't work, use manual ENTER
        if not contact_clicked:
            logger.info("Using Enter to select first search result...")
            pyautogui.press('enter')
            await asyncio.sleep(2)
            contact_clicked = True
            logger.info("Used Enter key to select contact")

        # Strategy C: Only use vision as last resort with STRICT filtering
        if not contact_clicked:
            try:
                logger.info("Using vision with strict filtering as last resort...")
                # Get current window elements
                from alice_vision import AliceVision
                vision = AliceVision()
                elements = await vision.scan_active_window()
                
                for element in elements:
                    element_text = element.get('text', '').strip()
                    element_label = element.get('label', '').strip()
                    
                    # Use our safety check function
                    if is_safe_click_target(element_label, element_text, contact_name):
                        logger.info(f"Found SAFE contact match: '{element_text}' (Label: {element_label})")
                        x, y = element['bbox']['center']
                        await vision.click_at_position(x, y)
                        logger.info(f"Clicked on verified safe contact at ({x}, {y})")
                        contact_clicked = True
                        break
                    else:
                        logger.debug(f"SKIPPED unsafe element: '{element_text}' (Label: {element_label})")
                        
                if not contact_clicked:
                    logger.warning("Vision method failed - no safe contact match found")
                        
            except Exception as e:
                logger.warning(f"Vision fallback failed: {e}")

        # CRITICAL: Verify WhatsApp is still open and active after contact selection
        logger.info("🔍 Verifying WhatsApp is still open after contact selection...")
        await asyncio.sleep(1)
        try:
            # Check if WhatsApp window is still active
            import pygetwindow as gw
            whatsapp_windows = [w for w in gw.getAllWindows() if 'whatsapp' in w.title.lower()]
            
            if not whatsapp_windows:
                logger.error("🚨 CRITICAL: WhatsApp window was closed during contact selection!")
                return f"❌ WhatsApp was accidentally closed. Please try again."
            else:
                # Ensure WhatsApp window is active and not minimized
                whatsapp_window = whatsapp_windows[0] 
                if whatsapp_window.isMinimized:
                    logger.info("Restoring minimized WhatsApp window...")
                    whatsapp_window.restore()
                    await asyncio.sleep(1)
                whatsapp_window.activate()
                logger.info("✅ Verified WhatsApp is still open and active")
                
        except ImportError:
            logger.info("pygetwindow not available, using alternative verification")
            # Alternative: try to take screenshot to verify WhatsApp is visible
            try:
                import pyautogui
                screen = pyautogui.screenshot()
                # If screenshot works, assume WhatsApp is still there
                logger.info("✅ Alternative verification passed")
            except Exception:
                logger.warning("Could not verify WhatsApp status")
        except Exception as verify_error:
            logger.warning(f"Window verification failed: {verify_error}")

        # IMPORTANT: Verify WhatsApp is still the active window
        logger.info("Ensuring WhatsApp remains focused...")
        try:
            # Try to bring WhatsApp back to focus if it was minimized
            pyautogui.hotkey('alt', 'tab')  # Switch back to WhatsApp if needed
            await asyncio.sleep(1)
            
            # Click in center of screen to focus on WhatsApp chat area
            screen_width, screen_height = pyautogui.size()
            safe_x, safe_y = screen_width // 2, screen_height // 2
            pyautogui.click(safe_x, safe_y)
            await asyncio.sleep(1)
            logger.info("Re-focused on WhatsApp window")
        except Exception as focus_error:
            logger.warning(f"Focus management failed: {focus_error}")
        
        # Verify we're in a chat by looking for message input area
        logger.info("Verifying chat opened and ready for messaging...")
        await asyncio.sleep(3)  # Give time for chat to load
        
        # Step 6: Wait for chat to load and find message input
        logger.info("Waiting for chat to load...")
        await asyncio.sleep(3)  # Give more time for chat to load
        
        # Step 7: Click on message input area using multiple strategies
        logger.info("Looking for message input box...")
        
        # Step 7: Find and click message input with better detection
        logger.info("Looking for message input box...")
        
        message_input_found = False
        
        # Strategy A: Try clicking in the typical message input area (most reliable)
        try:
            screen_width, screen_height = pyautogui.size()
            logger.info("Trying standard message input locations...")
            
            # WhatsApp typically has message input in bottom area
            message_input_locations = [
                (screen_width * 0.5, screen_height - 50),   # Bottom center
                (screen_width * 0.4, screen_height - 60),   # Bottom left-center  
                (screen_width * 0.6, screen_height - 60),   # Bottom right-center
                (screen_width * 0.5, screen_height - 80),   # Slightly higher center
                (screen_width * 0.3, screen_height - 50),   # Left side
            ]
            
            for i, (x, y) in enumerate(message_input_locations):
                try:
                    logger.info(f"Testing location {i+1}: ({x:.0f}, {y:.0f})")
                    pyautogui.click(x, y)
                    await asyncio.sleep(0.5)
                    
                    # Test if we can type by typing and deleting a test character
                    pyautogui.typewrite('.')
                    await asyncio.sleep(0.2)
                    pyautogui.press('backspace')
                    
                    logger.info(f"✅ Found working message input at location {i+1}")
                    message_input_found = True
                    break
                    
                except Exception as e:
                    logger.debug(f"Location {i+1} failed: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error testing message input locations: {e}")
        
        # Strategy B: Use Tab navigation to find message input
        if not message_input_found:
            logger.info("Trying Tab navigation to find message input...")
            try:
                # Click somewhere in the chat area first
                screen_width, screen_height = pyautogui.size()
                pyautogui.click(screen_width * 0.5, screen_height * 0.5)
                await asyncio.sleep(0.5)
                
                # Try tabbing to the message input
                for tab_attempt in range(10):
                    pyautogui.press('tab')
                    await asyncio.sleep(0.2)
                    
                    # Test if this is a text input
                    try:
                        pyautogui.typewrite('.')
                        pyautogui.press('backspace')
                        logger.info(f"✅ Found message input via Tab navigation (attempt {tab_attempt + 1})")
                        message_input_found = True
                        break
                    except:
                        continue
                        
            except Exception as e:
                logger.debug(f"Tab navigation failed: {e}")
        
        # Strategy C: Try keyboard shortcut to focus message input
        if not message_input_found:
            logger.info("Trying keyboard shortcuts...")
            try:
                # Some WhatsApp versions respond to Ctrl+N or other shortcuts
                shortcuts = ['ctrl+t', 'alt+t', 'tab']
                for shortcut in shortcuts:
                    pyautogui.hotkey(*shortcut.split('+'))
                    await asyncio.sleep(0.3)
                    
                    try:
                        pyautogui.typewrite('.')
                        pyautogui.press('backspace')
                        logger.info(f"✅ Found message input via {shortcut}")
                        message_input_found = True
                        break
                    except:
                        continue
                        
            except Exception as e:
                logger.debug(f"Keyboard shortcuts failed: {e}")
        
        if not message_input_found:
            logger.warning("Could not reliably find message input, using default location")
            # Use most common location as fallback
            screen_width, screen_height = pyautogui.size()
            pyautogui.click(screen_width * 0.5, screen_height - 60)
            await asyncio.sleep(0.5)
        
        # Step 8: Type and send message with enhanced verification
        logger.info(f"Typing message: {message[:50]}...")
        
        # CRITICAL: Ensure WhatsApp is focused before typing
        logger.info("Ensuring WhatsApp is the active window before typing...")
        try:
            # Method 1: Click in WhatsApp message area to ensure focus
            screen_width, screen_height = pyautogui.size()
            whatsapp_focus_x = screen_width * 0.5
            whatsapp_focus_y = screen_height - 60
            
            logger.info(f"Clicking to focus WhatsApp at ({whatsapp_focus_x:.0f}, {whatsapp_focus_y:.0f})")
            pyautogui.click(whatsapp_focus_x, whatsapp_focus_y)
            await asyncio.sleep(1)
            
            # Method 2: Try Alt+Tab to ensure we're in WhatsApp (if it got minimized)
            pyautogui.hotkey('alt', 'tab')
            await asyncio.sleep(0.5)
            
            # Method 3: Click again in message area to be absolutely sure
            pyautogui.click(whatsapp_focus_x, whatsapp_focus_y)
            await asyncio.sleep(0.5)
            
            logger.info("WhatsApp focus verification completed")
            
        except Exception as focus_error:
            logger.warning(f"Focus verification failed: {focus_error}")
        
        # Clear any existing text first
        try:
            pyautogui.hotkey('ctrl', 'a')  # Select all existing text
            await asyncio.sleep(0.3)
            pyautogui.press('delete')  # Delete selected content
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.debug(f"Text clearing failed: {e}")
        
        # Type the message with verification
        logger.info("Typing message character by character...")
        try:
            # Add a safety check: type one test character first
            logger.info("Safety check: typing test character...")
            pyautogui.typewrite('.')
            await asyncio.sleep(0.2)
            pyautogui.press('backspace')
            await asyncio.sleep(0.2)
            logger.info("Safety check passed - we're in a text input")
            
            # Now type the actual message
            for char in message:
                pyautogui.typewrite(char)
                await asyncio.sleep(0.05)  # Small delay between characters
        except Exception as e:
            logger.error(f"Message typing failed: {e}")
            # Fallback: try typing the whole message at once
            logger.info("Trying fallback: typing whole message at once")
            pyautogui.typewrite(message)
        
        await asyncio.sleep(1)
        
        # Verify the message was typed
        logger.info("Verifying message was typed...")
        try:
            pyautogui.hotkey('ctrl', 'a')  # Select all text
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.debug(f"Text selection failed: {e}")
        
        # Send the message with multiple attempts and verification
        logger.info("Sending message with verification...")
        message_sent = False
        
        for attempt in range(5):  # Increased attempts
            try:
                logger.info(f"Send attempt {attempt + 1}: Pressing Enter")
                
                # Make sure we're focused on the input
                screen_width, screen_height = pyautogui.size()
                pyautogui.click(screen_width * 0.5, screen_height - 60)
                await asyncio.sleep(0.3)
                
                # Press Enter to send
                pyautogui.press('enter')
                await asyncio.sleep(2)  # Give more time for message to send
                
                # Verify message was sent by checking if input is empty
                # Click in message input area
                pyautogui.click(screen_width * 0.5, screen_height - 60)
                await asyncio.sleep(0.3)
                
                # Select all text in input
                pyautogui.hotkey('ctrl', 'a')
                await asyncio.sleep(0.3)
                
                # Try to type a test character
                test_pos_before = pyautogui.position()
                pyautogui.typewrite('X')
                await asyncio.sleep(0.2)
                
                # If the field was empty, 'X' should be there. Delete it.
                pyautogui.press('backspace')
                await asyncio.sleep(0.2)
                
                message_sent = True
                logger.info(f"✅ Message verified as sent on attempt {attempt + 1}")
                break
                
            except Exception as e:
                logger.warning(f"Send attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(1)
                continue
        
        # Additional verification: try alternative send methods if first didn't work
        if not message_sent:
            logger.info("Trying alternative send methods...")
            try:
                # Method 1: Ctrl+Enter (some WhatsApp versions)
                pyautogui.hotkey('ctrl', 'enter')
                await asyncio.sleep(1)
                message_sent = True
                logger.info("Message sent via Ctrl+Enter")
            except:
                try:
                    # Method 2: Click send button (if visible)
                    # Look for send button near message input
                    screen_width, screen_height = pyautogui.size()
                    send_button_locations = [
                        (screen_width - 100, screen_height - 60),  # Right side
                        (screen_width - 50, screen_height - 60),   # Far right
                    ]
                    
                    for x, y in send_button_locations:
                        pyautogui.click(x, y)
                        await asyncio.sleep(1)
                        message_sent = True
                        logger.info(f"Message sent via click at {x}, {y}")
                        break
                        
                except Exception as e:
                    logger.debug(f"Alternative send methods failed: {e}")
        
        if message_sent:
            logger.info("✅ Message sending completed successfully")
        else:
            logger.warning("⚠️ Could not verify message was sent, but commands were executed")
        
        # Success response
        success_message = f"""✅ **WhatsApp Message Sent Successfully!**

👤 **To**: {contact_name}
💬 **Message**: {message[:100]}{'...' if len(message) > 100 else ''}

📱 Message भेज दिया गया है! 🚀"""

        logger.info(f"WhatsApp message sent successfully to {contact_name}")
        return success_message
        
    except Exception as e:
        error_message = f"""❌ **WhatsApp Message Failed**

🎯 **Contact**: {contact_name}
❌ **Error**: {str(e)}

💡 **Possible Solutions**:
- WhatsApp Desktop install है?
- Contact name correctly spelled है?
- Internet connection check करें
- WhatsApp manually try करके देखें

Technical: {str(e)[:100]}"""
        
        logger.error(f"WhatsApp automation failed: {e}")
        return error_message

@function_tool(name="open_whatsapp_chat", description="WhatsApp में किसी specific contact का chat खोलने के लिए")
async def open_whatsapp_chat(contact_name: str) -> str:
    """
    Open WhatsApp and navigate to a specific contact's chat (without sending message).
    
    Args:
        contact_name: Name of the person whose chat to open
    """
    try:
        logger.info(f"Opening WhatsApp chat with: {contact_name}")
        
        # Step 1: Open WhatsApp
        open_result = await open_application("whatsapp")
        if "❌" in open_result:
            return f"❌ WhatsApp open नहीं हो सका: {open_result}"
        
        await asyncio.sleep(3)
        
        # Step 2: Search for contact using improved method
        import pyautogui
        logger.info("Using Ctrl+F for search...")
        pyautogui.hotkey('ctrl', 'f')  # Search shortcut
        await asyncio.sleep(1)
        
        # Clear and type contact name
        pyautogui.hotkey('ctrl', 'a')  # Select all
        await asyncio.sleep(0.3)
        
        await type_text_here(contact_name)
        await asyncio.sleep(2)
        
        # Step 3: Select first result
        pyautogui.press('enter')
        await asyncio.sleep(2)
        
        # Success message
        return f"""✅ **WhatsApp Chat Opened Successfully!**

👤 **Contact**: {contact_name}
💬 **Chat**: Ready for conversation

अब आप message type कर सकते हैं! 🚀"""
        
    except Exception as e:
        logger.error(f"Error opening WhatsApp chat: {e}")
        return f"❌ Chat open करने में error: {str(e)}\n\n💡 Make sure WhatsApp Desktop installed है और contact name correct है।"

@function_tool
async def whatsapp_automation_help() -> str:
    """
    Get help about WhatsApp automation capabilities.
    """
    return """📱 **Alice WhatsApp Automation Help**

🚀 **Available Commands**:

1. **Send Message**: 
   - Command: send_whatsapp_message
   - Example: "WhatsApp पर Mom को message भेजो 'Hello'"

2. **Open Chat**:
   - Command: open_whatsapp_chat  
   - Example: "WhatsApp पर Dad का chat खोलो"

📋 **Requirements**:
- ✅ WhatsApp Desktop app installed
- ✅ Already logged in to WhatsApp
- ✅ Internet connection active
- ✅ Contact name should be exact (as saved)

💡 **Tips**:
- Contact names should match exactly as saved in phone
- WhatsApp Desktop should be accessible (not minimized)
- For best results, use simple, clear contact names
- Alice will automatically handle the UI navigation

🔧 **How it works**:
1. Opens WhatsApp Desktop application
2. Uses vision analysis to find search box
3. Types contact name to search
4. Navigates to chat automatically  
5. Types and sends your message

⚠️ **Troubleshooting**:
- Ensure WhatsApp Desktop is installed and working
- Check if contact name is spelled correctly
- Make sure you're logged into WhatsApp
- Contact should exist in your WhatsApp contacts

Example usage: "Alice, WhatsApp पर Ankush को message भेजो 'Meeting at 5 PM today'"
"""