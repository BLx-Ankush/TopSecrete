"""
Alice System Vision - Simple and Reliable Implementation
A working implementation that gives Alice the ability to "see" and interact with the OS
similar to how Comet browser reads the DOM.

This module focuses on:
1. Reliable Windows UI Automation
2. Simple element detection and interaction
3. Tested functionality that won't break Alice
"""

import logging
import time
import warnings
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json
from pathlib import Path

# Core Windows automation imports
try:
    import pyautogui
    import psutil
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    print("Installing required packages: pip install pyautogui psutil")
    PYAUTOGUI_AVAILABLE = False

# OCR imports for text recognition
try:
    import easyocr
    from PIL import Image, ImageDraw, ImageFont
    OCR_AVAILABLE = True
    warnings.filterwarnings(
        "ignore",
        message=".*pin_memory.*no accelerator.*",
        category=UserWarning,
    )
    print("OCR capabilities enabled (EasyOCR)")
except ImportError:
    OCR_AVAILABLE = False
    print("OCR not available - install with: pip install easyocr pillow")

try:
    # Try pywinauto first (more reliable for Windows)
    import pywinauto
    from pywinauto import Application, Desktop
    from pywinauto.findwindows import ElementNotFoundError
    from pywinauto import findwindows
    AUTOMATION_BACKEND = "pywinauto"
    print("Using pywinauto backend for UI automation")
except ImportError:
    try:
        # Fallback to basic window management
        import pygetwindow as gw
        AUTOMATION_BACKEND = "basic"
        print("Using basic window management (install pywinauto for better functionality)")
    except ImportError:
        AUTOMATION_BACKEND = "none"
        print("No automation backend available")

logger = logging.getLogger(__name__)

@dataclass
class UIElement:
    """Simple UI element representation"""
    name: str
    element_type: str
    coordinates: Tuple[int, int]  # x, y center point
    bounds: Tuple[int, int, int, int]  # left, top, right, bottom
    is_clickable: bool
    window_title: str

@dataclass
class WindowInfo:
    """Window information"""
    title: str
    process_name: str
    bounds: Tuple[int, int, int, int]
    is_active: bool
    area: int = 0  # Window area for sorting

class AliceVision:
    """Alice's vision system - simplified and reliable"""
    
    def __init__(self):
        self.temp_dir = Path("temp_alice_files/vision")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure pyautogui for safety
        if PYAUTOGUI_AVAILABLE:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
        
        self.last_scan_time = 0
        self.cache_duration = 2.0  # Cache results for 2 seconds
        self.cached_elements = []
        self.cached_windows = []
        
        logger.info(f"Alice Vision initialized with {AUTOMATION_BACKEND} backend")
    
    def get_all_windows(self) -> List[WindowInfo]:
        """Get list of all visible windows"""
        windows = []
        
        try:
            # Use the most reliable method first - PyGetWindow
            if AUTOMATION_BACKEND == "basic" or True:  # Always try this first
                windows = self._get_windows_basic()
                if windows:  # If we got results, use them
                    logger.debug(f"Successfully enumerated {len(windows)} windows with basic method")
                    self.cached_windows = windows
                    return windows
            
            # Fallback to pywinauto if basic method failed
            if AUTOMATION_BACKEND == "pywinauto":
                windows = self._get_windows_pywinauto()
                if windows:
                    logger.debug(f"Successfully enumerated {len(windows)} windows with pywinauto")
            else:
                logger.warning("No automation backend available")
                return []
            
            self.cached_windows = windows
            return windows
            
        except Exception as e:
            logger.error(f"Failed to get windows: {e}")
            # Return cached windows if available
            return self.cached_windows if hasattr(self, 'cached_windows') else []
    
    def _get_windows_pywinauto(self) -> List[WindowInfo]:
        """Get windows using pywinauto"""
        windows = []
        
        try:
            # Method 1: Try using findwindows to get all top-level windows
            try:
                from pywinauto import findwindows
                window_handles = findwindows.find_windows()
                
                for handle in window_handles:
                    try:
                        app = Application(backend="uia").connect(handle=handle)
                        window = app.window(handle=handle)
                        
                        # Skip if not visible or no title
                        if not window.is_visible() or not window.window_text().strip():
                            continue
                        
                        rect = window.rectangle()
                        
                        # Get process info
                        try:
                            process_id = window.process_id()
                            process = psutil.Process(process_id)
                            process_name = process.name()
                        except:
                            process_name = "unknown"
                        
                        window_info = WindowInfo(
                            title=window.window_text(),
                            process_name=process_name,
                            bounds=(rect.left, rect.top, rect.right, rect.bottom),
                            is_active=window.has_focus()
                        )
                        
                        windows.append(window_info)
                        
                    except Exception as e:
                        logger.debug(f"Skipped window handle {handle}: {e}")
                        continue
                        
            except Exception as e:
                logger.debug(f"findwindows method failed: {e}")
                
                # Method 2: Fallback to desktop windows enumeration
                try:
                    desktop = Desktop(backend="uia")
                    
                    for window in desktop.windows():
                        try:
                            # Skip invisible or system windows
                            if not window.is_visible() or not window.window_text():
                                continue
                            
                            rect = window.rectangle()
                            
                            # Get process name
                            try:
                                process_id = window.process_id()
                                process = psutil.Process(process_id)
                                process_name = process.name()
                            except:
                                process_name = "unknown"
                            
                            window_info = WindowInfo(
                                title=window.window_text(),
                                process_name=process_name,
                                bounds=(rect.left, rect.top, rect.right, rect.bottom),
                                is_active=window.has_focus()
                            )
                            
                            windows.append(window_info)
                            
                        except Exception as e:
                            logger.debug(f"Skipped window: {e}")
                            continue
                            
                except Exception as e:
                    logger.debug(f"Desktop windows method failed: {e}")
            
            return windows
            
        except Exception as e:
            logger.error(f"pywinauto window enumeration failed: {e}")
            return []
    
    def _get_windows_basic(self) -> List[WindowInfo]:
        """Basic window enumeration fallback using PyGetWindow"""
        windows = []
        
        try:
            import pygetwindow as gw
            
            for window in gw.getAllWindows():
                if window.visible and window.title.strip() and not window.isMinimized:
                    # Calculate area for better sorting
                    area = window.width * window.height
                    
                    windows.append(WindowInfo(
                        title=window.title.strip(),
                        process_name="unknown",
                        bounds=(window.left, window.top, 
                               window.left + window.width, 
                               window.top + window.height),
                        is_active=window == gw.getActiveWindow(),
                        area=area
                    ))
            
            # Sort by area (largest first) to prioritize main windows
            windows.sort(key=lambda x: getattr(x, 'area', 0), reverse=True)
            
            logger.debug(f"Basic method found {len(windows)} visible windows")
            return windows[:20]  # Limit to top 20 windows
                    
        except Exception as e:
            logger.error(f"Basic window enumeration failed: {e}")
            return []
    
    def scan_active_window(self) -> List[UIElement]:
        """Scan the currently active window for UI elements"""
        
        # Check cache first
        if time.time() - self.last_scan_time < self.cache_duration:
            return self.cached_elements
        
        try:
            if AUTOMATION_BACKEND == "pywinauto":
                elements = self._scan_active_window_pywinauto()
            else:
                logger.warning("Advanced element scanning not available without pywinauto")
                elements = []
            
            self.cached_elements = elements
            self.last_scan_time = time.time()
            
            logger.info(f"Scanned active window: found {len(elements)} elements")
            return elements
            
        except Exception as e:
            logger.error(f"Window scanning failed: {e}")
            return []
    
    def _scan_active_window_pywinauto(self) -> List[UIElement]:
        """Scan active window using pywinauto"""
        elements = []
        
        try:
            # Get the active window
            active_window = Desktop(backend="uia").windows()[0]  # Simplified - get first active
            
            # Try to connect to the active window more reliably
            try:
                from pywinauto import findwindows
                active_windows = findwindows.find_windows(active_only=True)
                if active_windows:
                    app = Application(backend="uia").connect(handle=active_windows[0])
                    window = app.window(handle=active_windows[0])
                else:
                    return []
            except Exception as e:
                logger.debug(f"Could not connect to active window: {e}")
                return []
            
            # Scan for clickable elements
            try:
                self._scan_controls_recursive(window, elements, window.window_text())
            except Exception as e:
                logger.debug(f"Control scanning failed: {e}")
            
            return elements
            
        except Exception as e:
            logger.error(f"Active window scanning failed: {e}")
            return []
    
    def _scan_controls_recursive(self, control, elements: List[UIElement], window_title: str):
        """Recursively scan controls for clickable elements"""
        
        try:
            # Get control info
            try:
                rect = control.rectangle()
                control_name = control.window_text()
                control_type = control.friendly_class_name()
                
                # Skip if no useful info
                if not control_name and control_type in ["Pane", "Window"]:
                    pass  # Skip but continue to children
                else:
                    # Determine if clickable
                    is_clickable = any(keyword in control_type.lower() for keyword in 
                                     ["button", "link", "menu", "tab", "check", "radio", "edit"])
                    
                    if is_clickable or control_name:
                        element = UIElement(
                            name=control_name or f"Unnamed {control_type}",
                            element_type=control_type,
                            coordinates=((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2),
                            bounds=(rect.left, rect.top, rect.right, rect.bottom),
                            is_clickable=is_clickable,
                            window_title=window_title
                        )
                        elements.append(element)
                
            except Exception as e:
                logger.debug(f"Failed to get control info: {e}")
            
            # Scan children (limit depth to avoid infinite recursion)
            try:
                if len(elements) < 50:  # Limit to prevent overwhelming results
                    children = control.children()
                    for child in children:
                        self._scan_controls_recursive(child, elements, window_title)
            except:
                pass  # Some controls don't have children
                
        except Exception as e:
            logger.debug(f"Control scanning error: {e}")
    
    def find_element(self, description: str) -> Optional[UIElement]:
        """Find an element by description"""
        
        elements = self.scan_active_window()
        description_lower = description.lower()
        
        best_match = None
        best_score = 0
        
        for element in elements:
            score = 0
            
            # Check name match
            if element.name and description_lower in element.name.lower():
                score += 3
            
            # Check type match
            if description_lower in element.element_type.lower():
                score += 2
            
            # Prefer clickable elements
            if element.is_clickable:
                score += 1
            
            if score > best_score:
                best_score = score
                best_match = element
        
        if best_match:
            logger.info(f"Found element '{description}': {best_match.name}")
        else:
            logger.warning(f"No element found for '{description}'")
        
        return best_match
    
    def click_element(self, element: UIElement) -> bool:
        """Click on a UI element"""
        
        if not PYAUTOGUI_AVAILABLE:
            logger.error("pyautogui not available for clicking")
            return False
        
        try:
            x, y = element.coordinates
            
            # Move to element and click
            pyautogui.moveTo(x, y, duration=0.2)
            pyautogui.click()
            
            logger.info(f"Clicked on '{element.name}' at ({x}, {y})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to click element: {e}")
            return False
    
    def take_screenshot(self) -> Optional[str]:
        """Take a screenshot and save it"""
        
        if not PYAUTOGUI_AVAILABLE:
            logger.error("pyautogui not available for screenshots")
            return None
        
        try:
            timestamp = int(time.time())
            filename = self.temp_dir / f"screenshot_{timestamp}.png"
            
            screenshot = pyautogui.screenshot()
            screenshot.save(str(filename))
            
            logger.info(f"Screenshot saved: {filename}")
            return str(filename)
            
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None
    
    def type_text(self, text: str) -> bool:
        """Type text at current cursor position"""
        
        if not PYAUTOGUI_AVAILABLE:
            logger.error("pyautogui not available for typing")
            return False
        
        try:
            pyautogui.typewrite(text, interval=0.02)
            logger.info(f"Typed text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return False
    
    def send_keys(self, keys: str) -> bool:
        """Send key combination"""
        
        if not PYAUTOGUI_AVAILABLE:
            return False
        
        try:
            if '+' in keys:
                key_list = [k.strip() for k in keys.split('+')]
                pyautogui.hotkey(*key_list)
            else:
                pyautogui.press(keys)
            
            logger.info(f"Sent keys: {keys}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send keys: {e}")
            return False
    
    def export_scan_data(self, output_file: Optional[str] = None) -> str:
        """Export current scan data to JSON"""
        
        if output_file is None:
            timestamp = int(time.time())
            output_file = str(self.temp_dir / f"scan_data_{timestamp}.json")
        
        try:
            windows = self.get_all_windows()
            elements = self.scan_active_window()
            
            data = {
                "timestamp": timestamp,
                "windows": [
                    {
                        "title": w.title,
                        "process": w.process_name,
                        "bounds": w.bounds,
                        "is_active": w.is_active
                    }
                    for w in windows
                ],
                "active_window_elements": [
                    {
                        "name": e.name,
                        "type": e.element_type,
                        "coordinates": e.coordinates,
                        "bounds": e.bounds,
                        "is_clickable": e.is_clickable,
                        "window": e.window_title
                    }
                    for e in elements
                ]
            }
            
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Scan data exported to: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Failed to export scan data: {e}")
            return ""
    
    # === OCR METHODS ===
    
    def extract_text_from_image(self, image_path: str) -> Dict[str, Any]:
        """Extract text from an image file using OCR"""
        
        if not OCR_AVAILABLE:
            return {
                'success': False,
                'error': 'OCR not available - install with: pip install easyocr pillow',
                'text': '',
                'details': []
            }
        
        try:
            # Initialize EasyOCR reader if not already done
            if not hasattr(self, 'ocr_reader'):
                logger.info("Initializing EasyOCR reader...")
                # Initialize with verbose=False to reduce console output
                self.ocr_reader = easyocr.Reader(['en'], verbose=False, gpu=False)
                logger.info("EasyOCR reader initialized successfully")
            
            # Read text from image
            logger.debug(f"Extracting text from: {image_path}")
            results = self.ocr_reader.readtext(image_path)
            
            # Process results
            extracted_text = []
            full_text = ""
            
            for result in results:
                bbox, text, confidence = result
                extracted_text.append({
                    'text': text,
                    'confidence': confidence,
                    'bbox': bbox,
                    'position': f"at ({int(bbox[0][0])}, {int(bbox[0][1])})"
                })
                full_text += text + " "
            
            return {
                'success': True,
                'text': full_text.strip(),
                'details': extracted_text,
                'total_items': len(extracted_text)
            }
            
        except Exception as e:
            logger.error(f"OCR failed for {image_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'details': []
            }
    
    def extract_text_from_screenshot(self) -> Dict[str, Any]:
        """Take screenshot and extract text from it"""
        
        if not OCR_AVAILABLE:
            return {
                'success': False,
                'error': 'OCR not available - install with: pip install easyocr pillow',
                'text': '',
                'screenshot': ''
            }
        
        try:
            # Take screenshot first
            screenshot_path = self.take_screenshot()
            if not screenshot_path:
                return {
                    'success': False,
                    'error': 'Failed to take screenshot',
                    'text': '',
                    'screenshot': ''
                }
            
            # Extract text from the screenshot
            ocr_result = self.extract_text_from_image(screenshot_path)
            ocr_result['screenshot'] = screenshot_path
            
            logger.info(f"Extracted text from screen: {len(ocr_result.get('text', ''))} characters")
            return ocr_result
            
        except Exception as e:
            logger.error(f"Screenshot OCR failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'screenshot': ''
            }
    
    def analyze_image_content(self, image_path: str) -> Dict[str, Any]:
        """Analyze image content including text and basic description"""
        
        try:
            # Get OCR results
            ocr_result = self.extract_text_from_image(image_path)
            
            # Add basic image info
            if OCR_AVAILABLE:
                with Image.open(image_path) as img:
                    width, height = img.size
                    mode = img.mode
                    format_info = img.format
            else:
                width = height = 0
                mode = format_info = "unknown"
            
            analysis = {
                'success': True,
                'image_path': image_path,
                'image_size': f"{width}x{height}",
                'image_mode': mode,
                'image_format': format_info,
                'ocr_result': ocr_result,
                'text_found': len(ocr_result.get('text', '')) > 0,
                'text_length': len(ocr_result.get('text', '')),
                'text_items': len(ocr_result.get('details', []))
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Image analysis failed for {image_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'image_path': image_path
            }

# Test function
def test_alice_vision():
    """Test Alice's vision system"""
    
    print("Testing Alice Vision System...")
    print("=" * 50)
    
    # Initialize vision
    vision = AliceVision()
    
    # Test 1: Get windows
    print("\\n1. Testing window enumeration...")
    windows = vision.get_all_windows()
    print(f"Found {len(windows)} windows:")
    for i, window in enumerate(windows[:5]):
        status = "[ACTIVE]" if window.is_active else ""
        print(f"  {i+1}. {window.title} ({window.process_name}) {status}")
    
    # Test 2: Scan active window
    print("\\n2. Testing active window scanning...")
    elements = vision.scan_active_window()
    print(f"Found {len(elements)} elements in active window:")
    
    clickable_elements = [e for e in elements if e.is_clickable]
    print(f"  - {len(clickable_elements)} clickable elements")
    
    for i, element in enumerate(clickable_elements[:5]):
        print(f"  {i+1}. {element.name} ({element.element_type}) at {element.coordinates}")
    
    # Test 3: Take screenshot
    print("\\n3. Testing screenshot...")
    screenshot_path = vision.take_screenshot()
    if screenshot_path:
        print(f"Screenshot saved: {screenshot_path}")
    
    # Test 4: Export data
    print("\\n4. Testing data export...")
    export_path = vision.export_scan_data()
    if export_path:
        print(f"Scan data exported: {export_path}")
    
    print("\\n" + "=" * 50)
    print("Alice Vision Test Complete!")
    
    return vision

if __name__ == "__main__":
    test_alice_vision()