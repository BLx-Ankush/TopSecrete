"""
Alice Advanced App Automation System
Allows Alice to perform operations and tasks within any opened application
"""

import subprocess
import time
import os
from pathlib import Path
from livekit.agents import function_tool
import logging

# Check if automation packages are available, install if needed
try:
    import pyautogui
    import pynput
    from pynput import keyboard, mouse
    import win32gui
    import win32con
    import win32api
    pyautogui.FAILSAFE = True  # Enable failsafe
    pyautogui.PAUSE = 0.5  # Add small delay between actions
except ImportError as e:
    print(f"Installing required automation packages: {e}")
    subprocess.run(['pip', 'install', 'pyautogui', 'pynput', 'pywin32'], check=True)
    import pyautogui
    import pynput
    from pynput import keyboard, mouse
    import win32gui
    import win32con
    import win32api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Semantic Vision Integration (replaces fragile pixel-coordinate clicking) ──
# The SemanticVisionEngine sends a screenshot to Gemini Flash and asks it to
# locate a named UI element, returning its center coordinate.  This is called
# for all click-based operations, making them resolution and DPI independent.
try:
    from alice_semantic_vision import get_semantic_vision_engine
    SEMANTIC_VISION_AVAILABLE = True
    logger.info("✅ SemanticVisionEngine loaded — using Gemini-powered semantic clicking")
except ImportError:
    SEMANTIC_VISION_AVAILABLE = False
    logger.warning("⚠️  SemanticVisionEngine not available — falling back to coordinate-based clicking")



class AdvancedAppAutomation:
    def __init__(self):
        self.current_app_window = None
        self.automation_enabled = False
        
        # Common keyboard shortcuts for different apps
        self.app_shortcuts = {
            'general': {
                'save': 'ctrl+s',
                'copy': 'ctrl+c', 
                'paste': 'ctrl+v',
                'undo': 'ctrl+z',
                'redo': 'ctrl+y',
                'select_all': 'ctrl+a',
                'find': 'ctrl+f',
                'new': 'ctrl+n',
                'open': 'ctrl+o',
                'close': 'alt+f4',
                'minimize': 'win+down',
                'maximize': 'win+up'
            },
            'chrome': {
                'new_tab': 'ctrl+t',
                'close_tab': 'ctrl+w',
                'reload': 'ctrl+r',
                'new_window': 'ctrl+n',
                'incognito': 'ctrl+shift+n',
                'bookmarks': 'ctrl+shift+o',
                'history': 'ctrl+h',
                'downloads': 'ctrl+j',
                'developer_tools': 'f12'
            },
            'word': {
                'bold': 'ctrl+b',
                'italic': 'ctrl+i',
                'underline': 'ctrl+u',
                'print': 'ctrl+p',
                'spell_check': 'f7',
                'word_count': 'ctrl+shift+g',
                'find_replace': 'ctrl+h'
            },
            'excel': {
                'insert_row': 'ctrl+shift+plus',
                'delete_row': 'ctrl+minus', 
                'auto_sum': 'alt+equals',
                'format_cells': 'ctrl+1',
                'insert_function': 'shift+f3',
                'save_as': 'f12'
            },
            'notepad': {
                'word_wrap': 'alt+z',
                'font': 'alt+o+f',
                'goto_line': 'ctrl+g',
                'time_date': 'f5'
            },
            'vscode': {
                'command_palette': 'ctrl+shift+p',
                'quick_open': 'ctrl+p',
                'new_file': 'ctrl+alt+n',
                'split_editor': 'ctrl+backslash',
                'toggle_terminal': 'ctrl+backtick',
                'format_code': 'shift+alt+f',
                'comment_line': 'ctrl+slash'
            }
        }
        
        # Common app tasks and their automation sequences
        self.app_tasks = {
            'notepad': {
                'write_text': self._notepad_write_text,
                'save_file': self._notepad_save_file,
                'find_text': self._notepad_find_text
            },
            'chrome': {
                'navigate_to': self._chrome_navigate,
                'search_google': self._chrome_google_search,
                'new_tab': self._chrome_new_tab
            },
            'calculator': {
                'calculate': self._calculator_calculate,
                'clear': self._calculator_clear
            },
            'word': {
                'type_document': self._word_type_document,
                'format_text': self._word_format_text
            },
            'excel': {
                'add_formula': self._excel_add_formula
            }
        }
    
    def find_window_by_title(self, title_contains: str):
        """Find application window by partial title match"""
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title_contains.lower() in window_title.lower():
                    windows.append((hwnd, window_title))
            return True
        
        windows = []
        win32gui.EnumWindows(callback, windows)
        return windows[0] if windows else None
    
    def focus_window(self, window_handle):
        """Bring window to focus"""
        try:
            win32gui.ShowWindow(window_handle, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(window_handle)
            time.sleep(0.5)  # Wait for window to come to focus
            return True
        except Exception as e:
            logger.error(f"Error focusing window: {e}")
            return False
    
    def send_shortcut(self, shortcut: str):
        """Send keyboard shortcut"""
        try:
            pyautogui.hotkey(*shortcut.split('+'))
            time.sleep(0.3)
            return True
        except Exception as e:
            logger.error(f"Error sending shortcut {shortcut}: {e}")
            return False
    
    def type_text(self, text: str, interval: float = 0.01):
        """Type text with specified interval"""
        try:
            pyautogui.typewrite(text, interval=interval)
            return True
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return False
    
    # Notepad automation methods
    def _notepad_write_text(self, text: str):
        """Write text in Notepad"""
        window = self.find_window_by_title("Notepad")
        if window:
            self.focus_window(window[0])
            self.send_shortcut('ctrl+a')  # Select all
            self.type_text(text)
            return f"✅ Text written in Notepad: '{text[:50]}...'"
        return "❌ Notepad window not found"
    
    def _notepad_save_file(self, filename: str = ""):
        """Save file in Notepad"""
        window = self.find_window_by_title("Notepad")
        if window:
            self.focus_window(window[0])
            self.send_shortcut('ctrl+s')
            time.sleep(1)
            if filename:
                self.type_text(filename)
                pyautogui.press('enter')
            return f"✅ File saved" + (f" as {filename}" if filename else "")
        return "❌ Notepad window not found"
    
    def _notepad_find_text(self, search_text: str):
        """Find text in Notepad"""
        window = self.find_window_by_title("Notepad")
        if window:
            self.focus_window(window[0])
            self.send_shortcut('ctrl+f')
            time.sleep(0.5)
            self.type_text(search_text)
            pyautogui.press('enter')
            return f"✅ Searching for '{search_text}' in Notepad"
        return "❌ Notepad window not found"
    
    # Chrome automation methods
    def _chrome_navigate(self, url: str):
        """Navigate to URL in Chrome"""
        window = self.find_window_by_title("Chrome")
        if window:
            self.focus_window(window[0])
            self.send_shortcut('ctrl+l')  # Focus address bar
            self.type_text(url)
            pyautogui.press('enter')
            return f"✅ Navigating to {url} in Chrome"
        return "❌ Chrome window not found"
    
    def _chrome_google_search(self, query: str):
        """Search on Google in Chrome"""
        window = self.find_window_by_title("Chrome")
        if window:
            self.focus_window(window[0])
            self.send_shortcut('ctrl+l')
            self.type_text(f"google.com/search?q={query}")
            pyautogui.press('enter')
            return f"✅ Searching '{query}' on Google"
        return "❌ Chrome window not found"
    
    def _chrome_new_tab(self, url: str = ""):
        """Open new tab in Chrome"""
        window = self.find_window_by_title("Chrome")
        if window:
            self.focus_window(window[0])
            self.send_shortcut('ctrl+t')
            if url:
                self.type_text(url)
                pyautogui.press('enter')
            return f"✅ New tab opened" + (f" with {url}" if url else "")
        return "❌ Chrome window not found"
    
    # Calculator automation methods
    def _calculator_calculate(self, expression: str):
        """Perform calculation in Calculator"""
        window = self.find_window_by_title("Calculator")
        if window:
            self.focus_window(window[0])
            # Convert expression to calculator button presses
            for char in expression:
                if char in "0123456789+-*/().":
                    if char == '*':
                        pyautogui.press('multiply')
                    elif char == '/':
                        pyautogui.press('divide')
                    else:
                        pyautogui.press(char)
                    time.sleep(0.1)
            pyautogui.press('enter')
            return f"✅ Calculated: {expression}"
        return "❌ Calculator window not found"
    
    def _calculator_clear(self):
        """Clear calculator"""
        window = self.find_window_by_title("Calculator")
        if window:
            self.focus_window(window[0])
            pyautogui.press('c')
            return "✅ Calculator cleared"
        return "❌ Calculator window not found"
    
    # Word automation methods  
    def _word_type_document(self, content: str):
        """Type document in Word"""
        window = self.find_window_by_title("Word")
        if window:
            self.focus_window(window[0])
            self.type_text(content)
            return f"✅ Document typed in Word: '{content[:50]}...'"
        return "❌ Word window not found"
    
    def _word_format_text(self, format_type: str):
        """Format text in Word (bold, italic, underline)"""
        window = self.find_window_by_title("Word") 
        if window:
            self.focus_window(window[0])
            self.send_shortcut('ctrl+a')  # Select all
            if format_type.lower() == 'bold':
                self.send_shortcut('ctrl+b')
            elif format_type.lower() == 'italic':
                self.send_shortcut('ctrl+i')
            elif format_type.lower() == 'underline':
                self.send_shortcut('ctrl+u')
            return f"✅ Applied {format_type} formatting in Word"
        return "❌ Word window not found"
    
    # Excel automation methods
    def _excel_add_formula(self, cell: str, formula: str):
        """Add formula to Excel cell"""
        window = self.find_window_by_title("Excel")
        if window:
            self.focus_window(window[0])
            self.send_shortcut('ctrl+g')  # Go to cell
            time.sleep(0.5)
            self.type_text(cell)
            pyautogui.press('enter')
            self.type_text(formula)
            pyautogui.press('enter')
            return f"✅ Added formula {formula} to cell {cell}"
        return "❌ Excel window not found"

# Initialize the automation system
app_automation = AdvancedAppAutomation()

@function_tool(
    name="perform_app_task",
    description=(
        "किसी भी open app में specific task perform करने के लिए। "
        "Examples: Notepad में text लिखना, Chrome में website खोलना, Calculator में calculation, etc."
    )
)
async def perform_app_task(app_name: str, task: str, parameters: str = "") -> str:
    """
    Perform specific tasks within opened applications
    
    Args:
        app_name: Name of the application (e.g., "notepad", "chrome", "calculator")
        task: Task to perform (e.g., "write_text", "navigate_to", "calculate")
        parameters: Additional parameters for the task
    """
    try:
        app_lower = app_name.lower()
        
        # Check if app has automation support
        if app_lower not in app_automation.app_tasks:
            return f"❌ Sorry! {app_name} के लिए automation support अभी available नहीं है।\n\nSupported apps: {list(app_automation.app_tasks.keys())}"
        
        # Check if task is supported for this app
        if task not in app_automation.app_tasks[app_lower]:
            available_tasks = list(app_automation.app_tasks[app_lower].keys())
            return f"❌ {app_name} में '{task}' task support नहीं है।\n\nAvailable tasks: {available_tasks}"
        
        # Execute the task
        task_function = app_automation.app_tasks[app_lower][task]
        
        if parameters:
            result = task_function(parameters)
        else:
            result = task_function()
        
        return f"🎯 Task completed in {app_name}!\n{result}\n\nऔर कोई task करना है? 😊"
        
    except Exception as e:
        logger.error(f"Error performing task {task} in {app_name}: {e}")
        return f"❌ Task execution में error आया: {str(e)}"

@function_tool(
    name="send_app_shortcut",
    description="किसी app में keyboard shortcut send करने के लिए (save, copy, paste, etc.)"
)
async def send_app_shortcut(app_name: str, shortcut_name: str) -> str:
    """
    Send keyboard shortcuts to applications
    
    Args:
        app_name: Name of the application
        shortcut_name: Name of shortcut (save, copy, paste, etc.)
    """
    try:
        app_lower = app_name.lower()
        shortcut_lower = shortcut_name.lower()
        
        # Get shortcut for specific app or general
        shortcut = None
        if app_lower in app_automation.app_shortcuts:
            shortcut = app_automation.app_shortcuts[app_lower].get(shortcut_lower)
        
        if not shortcut:
            shortcut = app_automation.app_shortcuts['general'].get(shortcut_lower)
        
        if not shortcut:
            available_shortcuts = list(app_automation.app_shortcuts.get(app_lower, {}).keys()) + \
                                list(app_automation.app_shortcuts['general'].keys())
            return f"❌ '{shortcut_name}' shortcut नहीं मिला।\n\nAvailable: {available_shortcuts[:10]}"
        
        # Find and focus the app window
        window = app_automation.find_window_by_title(app_name)
        if window:
            app_automation.focus_window(window[0])
            app_automation.send_shortcut(shortcut)
            return f"✅ {shortcut_name} shortcut sent to {app_name} ({shortcut})"
        else:
            return f"❌ {app_name} window नहीं मिला। App open है?"
        
    except Exception as e:
        logger.error(f"Error sending shortcut to {app_name}: {e}")
        return f"❌ Shortcut send करने में error: {str(e)}"

@function_tool(
    name="type_in_app",
    description="किसी भी active app में text type करने के लिए"
)
async def type_in_app(app_name: str, text: str) -> str:
    """
    Type text in any active application
    
    Args:
        app_name: Name of the application
        text: Text to type
    """
    try:
        # Find and focus the app window
        window = app_automation.find_window_by_title(app_name)
        if window:
            app_automation.focus_window(window[0])
            app_automation.type_text(text)
            return f"✅ Text typed in {app_name}: '{text[:50]}...'\n\nऔर कुछ type करना है? ⌨️"
        else:
            return f"❌ {app_name} window नहीं मिला। App open है?"
        
    except Exception as e:
        logger.error(f"Error typing in {app_name}: {e}")
        return f"❌ Text typing में error: {str(e)}"

@function_tool(
    name="get_app_automation_help",
    description="Available app automation tasks और shortcuts की list देता है"
)
async def get_app_automation_help(app_name: str = "") -> str:
    """Get help for app automation capabilities"""
    
    if app_name:
        app_lower = app_name.lower()
        help_text = f"🎯 **{app_name} Automation Help:**\n\n"
        
        # Show available tasks
        if app_lower in app_automation.app_tasks:
            tasks = list(app_automation.app_tasks[app_lower].keys())
            help_text += f"📋 **Available Tasks:**\n"
            for task in tasks:
                help_text += f"• {task}\n"
            help_text += "\n"
        
        # Show available shortcuts
        if app_lower in app_automation.app_shortcuts:
            shortcuts = list(app_automation.app_shortcuts[app_lower].keys())
            help_text += f"⌨️ **App Shortcuts:**\n"
            for shortcut in shortcuts[:10]:
                help_text += f"• {shortcut}\n"
            help_text += "\n"
        
        # Show general shortcuts
        general_shortcuts = list(app_automation.app_shortcuts['general'].keys())
        help_text += f"🔧 **General Shortcuts:**\n"
        for shortcut in general_shortcuts[:8]:
            help_text += f"• {shortcut}\n"
        
        return help_text
    
    else:
        # General automation help
        supported_apps = list(app_automation.app_tasks.keys())
        return f"""🎯 **Alice App Automation System**

📱 **Supported Apps:**
{chr(10).join([f'• {app}' for app in supported_apps])}

🔧 **General Capabilities:**
• Open any app
• Type text in any app
• Send keyboard shortcuts
• Perform specific app tasks
• Window management

💡 **Example Commands:**
• "notepad में text type karo 'Hello World'"
• "chrome में google.com open karo" 
• "calculator में 25+75 calculate karo"
• "word में bold formatting apply karo"
• "save shortcut send karo notepad में"

Use 'get_app_automation_help [app_name]' for specific app help! 😊"""


# ── Semantic Vision Tools (resolution-independent UI interaction) ──────────────

@function_tool(
    name="semantic_click",
    description=(
        "Click any UI element on screen by describing it in plain English. "
        "Uses Gemini Vision to visually locate the element — works regardless "
        "of screen resolution, DPI, or window position. "
        "Example: 'the blue Send button', 'the search bar at the top', 'the close X button'."
    )
)
async def semantic_click(element_description: str, double_click: bool = False) -> str:
    """
    Click a UI element on screen described in plain English using Gemini Vision.

    Args:
        element_description: Natural language description of the element to click.
        double_click: Set to True for a double-click (e.g. to open a file).

    Returns:
        Success or error message.
    """
    if not SEMANTIC_VISION_AVAILABLE:
        return "❌ Semantic vision not available — SemanticVisionEngine could not be loaded."
    try:
        engine = get_semantic_vision_engine()
        success = await engine.click_element(element_description, double_click=double_click)
        if success:
            return (
                f"✅ {'Double-clicked' if double_click else 'Clicked'} "
                f"'{element_description}' successfully."
            )
        return f"❌ Could not find '{element_description}' on screen. Is the window visible?"
    except Exception as e:
        return f"❌ Semantic click failed: {e}"


@function_tool(
    name="semantic_type_into",
    description=(
        "Click a specific input field on screen (described in plain English) "
        "and type text into it. Uses Gemini Vision to locate the field — "
        "immune to resolution changes. "
        "Example: 'the WhatsApp message box', 'the address bar', 'the search field'."
    )
)
async def semantic_type_into(element_description: str, text: str) -> str:
    """
    Find an input field by description and type text into it.

    Args:
        element_description: Natural language description of the input field.
        text: The text to type into the field.

    Returns:
        Success or error message.
    """
    if not SEMANTIC_VISION_AVAILABLE:
        return "❌ Semantic vision not available."
    try:
        engine = get_semantic_vision_engine()
        success = await engine.type_into_element(element_description, text)
        if success:
            return f"✅ Typed into '{element_description}': {text[:80]}"
        return f"❌ Could not find '{element_description}' on screen."
    except Exception as e:
        return f"❌ Semantic type failed: {e}"