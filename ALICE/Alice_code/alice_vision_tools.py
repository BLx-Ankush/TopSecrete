"""
Alice Vision Tools - LiveKit Agent Integration
Provides Alice with vision capabilities through LiveKit agent tools with intelligent VLM optimization
"""

from typing import Optional, List, Dict, Any, Union, Tuple
from livekit.agents import function_tool
import logging
import asyncio
import hashlib
import json
import time
import tempfile
from pathlib import Path

from alice_vision import AliceVision, UIElement, WindowInfo
from free_vlm_providers import analyze_with_free_vlm, get_free_vlm_status

logger = logging.getLogger(__name__)

# Enhanced caching and optimization
_analysis_cache = {}
_cache_max_age = 300  # 5 minutes
_api_failure_count = 0
_last_api_failure = 0

# Global vision instance
_vision_system = None

def get_vision_system():
    """Get or create the vision system instance"""
    global _vision_system
    if _vision_system is None:
        _vision_system = AliceVision()
    return _vision_system

# === IMAGE PREPROCESSING UTILITIES ===

def preprocess_image_for_analysis(image_path: str, enhancement_type: str = "auto") -> str:
    """
    Preprocess image for better VLM/OCR analysis
    
    Args:
        image_path: Path to the original image
        enhancement_type: Type of enhancement ('auto', 'text', 'ui', 'chart')
    
    Returns:
        Path to the processed image
    """
    try:
        from PIL import Image, ImageEnhance, ImageFilter
        import cv2
        import numpy as np
        
        # Load image
        image = Image.open(image_path)
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Determine best enhancement based on type
        if enhancement_type == "auto":
            # Analyze image to determine best enhancement
            enhancement_type = _detect_image_type(image)
        
        if enhancement_type == "text":
            # Enhance for text recognition
            image = _enhance_for_text(image)
        elif enhancement_type == "ui":
            # Enhance for UI element detection
            image = _enhance_for_ui(image)
        elif enhancement_type == "chart":
            # Enhance for chart/diagram analysis
            image = _enhance_for_charts(image)
        
        # Save processed image
        temp_path = str(Path(tempfile.gettempdir()) / f"alice_processed_{int(time.time())}.png")
        image.save(temp_path, optimize=True, quality=95)
        
        logger.debug(f"Preprocessed image saved to: {temp_path}")
        return temp_path
        
    except ImportError:
        logger.warning("Image preprocessing libraries not available. Using original image.")
        return image_path
    except Exception as e:
        logger.error(f"Image preprocessing failed: {e}. Using original image.")
        return image_path

def _detect_image_type(image: Any) -> str:
    """Detect the type of content in an image"""
    try:
        import cv2
        import numpy as np
        
        # Convert PIL to OpenCV
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # Detect text regions
        text_score = _calculate_text_density(gray)
        
        # Detect UI elements
        ui_score = _calculate_ui_density(gray)
        
        # Detect charts/graphs
        chart_score = _calculate_chart_density(gray)
        
        # Return the dominant type
        scores = {"text": text_score, "ui": ui_score, "chart": chart_score}
        return max(scores, key=scores.get)
        
    except Exception:
        return "text"  # Default fallback

def _calculate_text_density(gray_image: Any) -> float:
    """Calculate text density in image"""
    try:
        import cv2
        import numpy as np
        
        # Use text detection heuristics
        edges = cv2.Canny(gray_image, 50, 150)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        detected_lines = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, horizontal_kernel, iterations=2)
        
        return np.sum(detected_lines) / detected_lines.size
    except Exception:
        return 0.5

def _calculate_ui_density(gray_image: Any) -> float:
    """Calculate UI element density in image"""
    try:
        import cv2
        
        # Detect rectangles and UI patterns
        edges = cv2.Canny(gray_image, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        rect_count = sum(1 for c in contours if cv2.contourArea(c) > 100)
        return min(rect_count / 100, 1.0)  # Normalize
    except Exception:
        return 0.3

def _calculate_chart_density(gray_image: Any) -> float:
    """Calculate chart/diagram density in image"""
    try:
        import cv2
        import numpy as np
        
        # Detect lines and circular patterns
        edges = cv2.Canny(gray_image, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30, maxLineGap=10)
        
        line_score = len(lines) / 50 if lines is not None else 0
        
        # Detect circles
        circles = cv2.HoughCircles(gray_image, cv2.HOUGH_GRADIENT, 1, 20, param1=50, param2=30, minRadius=10, maxRadius=100)
        circle_score = len(circles[0]) / 10 if circles is not None else 0
        
        return min(line_score + circle_score, 1.0)
    except Exception:
        return 0.2

def _enhance_for_text(image: Any) -> Any:
    """Enhance image for better text recognition"""
    try:
        from PIL import ImageEnhance, ImageFilter
        
        # Increase contrast and sharpness
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)
        
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)
        
        # Slight denoising
        image = image.filter(ImageFilter.MedianFilter(size=1))
        
        return image
    except Exception:
        return image

def _enhance_for_ui(image: Any) -> Any:
    """Enhance image for UI element detection"""
    try:
        from PIL import ImageEnhance
        
        # Increase contrast for better element boundaries
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.3)
        
        # Slight brightness adjustment
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.05)
        
        return image
    except Exception:
        return image

def _enhance_for_charts(image: Any) -> Any:
    """Enhance image for chart/diagram analysis"""
    try:
        from PIL import ImageEnhance
        
        # Enhance color saturation for better chart distinction
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.1)
        
        # Increase sharpness for line clarity
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        return image
    except Exception:
        return image

# === CACHING UTILITIES ===

def _get_image_hash(image_path: str) -> str:
    """Generate hash of image for caching"""
    try:
        with open(image_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return str(time.time())

def _cache_analysis(cache_key: str, result: Dict[str, Any]) -> None:
    """Cache analysis result"""
    global _analysis_cache
    _analysis_cache[cache_key] = {
        'result': result,
        'timestamp': time.time()
    }
    
    # Clean old cache entries
    current_time = time.time()
    _analysis_cache = {
        k: v for k, v in _analysis_cache.items() 
        if current_time - v['timestamp'] < _cache_max_age
    }

def _get_cached_analysis(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached analysis result"""
    global _analysis_cache
    cached = _analysis_cache.get(cache_key)
    
    if cached and time.time() - cached['timestamp'] < _cache_max_age:
        logger.debug(f"Using cached analysis for key: {cache_key[:10]}...")
        return cached['result']
    
    return None

# === API FAILURE TRACKING ===

def _should_use_fallback() -> bool:
    """Determine if we should use fallback due to API issues"""
    global _api_failure_count, _last_api_failure
    
    # If too many recent failures, use fallback
    if _api_failure_count >= 3 and time.time() - _last_api_failure < 300:  # 5 minutes
        return True
    
    return False

def _record_api_failure() -> None:
    """Record an API failure for fallback logic"""
    global _api_failure_count, _last_api_failure
    _api_failure_count += 1
    _last_api_failure = time.time()

def _record_api_success() -> None:
    """Record API success - reset failure count"""
    global _api_failure_count
    _api_failure_count = 0

# === ENHANCED PROMPTS ===

def _get_structured_prompt(analysis_type: str, task_description: str) -> str:
    """Generate structured prompt based on analysis type"""
    
    base_prompt = f"""You are an expert visual analyst. Analysis type: {analysis_type}

Task: {task_description}

Please provide a structured analysis with the following sections:"""

    if analysis_type == "text_extraction":
        return base_prompt + """
1. **TEXT CONTENT**: All readable text found in the image
2. **LAYOUT**: How the text is organized (paragraphs, lists, headers)
3. **FORMATTING**: Font sizes, bold/italic text, special formatting
4. **KEY INFORMATION**: Main points, important data, action items
5. **CONTEXT**: What type of document/content this appears to be

Focus on accuracy and completeness of text extraction."""

    elif analysis_type == "ui_analysis":
        return base_prompt + """
1. **INTERFACE TYPE**: What kind of application/interface (web, desktop, mobile)
2. **LAYOUT STRUCTURE**: Main sections, navigation, content areas
3. **INTERACTIVE ELEMENTS**: Buttons, links, forms, controls (with locations)
4. **CURRENT STATE**: What's selected, active, or highlighted
5. **NAVIGATION PATH**: How to accomplish specific tasks
6. **ACCESSIBILITY**: Any issues or important UI patterns

Focus on actionable interface guidance."""

    elif analysis_type == "presentation":
        return base_prompt + """
1. **SLIDE PURPOSE**: Main message and objective
2. **CONTENT STRUCTURE**: Headers, bullet points, sections
3. **KEY POINTS**: Most important information and takeaways
4. **VISUAL ELEMENTS**: Charts, images, diagrams and their meaning
5. **DATA INSIGHTS**: Numbers, statistics, trends shown
6. **ACTION ITEMS**: Next steps or calls to action mentioned

Focus on extracting actionable insights and main messages."""

    elif analysis_type == "document":
        return base_prompt + """
1. **DOCUMENT TYPE**: Kind of document (report, article, form, etc.)
2. **MAIN CONTENT**: Primary text and information
3. **STRUCTURE**: Sections, headers, organization
4. **IMPORTANT DATA**: Key facts, numbers, dates, names
5. **CONCLUSIONS**: Main findings or results
6. **NEXT STEPS**: Any actions or follow-ups mentioned

Focus on comprehensive information extraction."""

    elif analysis_type == "chart_diagram":
        return base_prompt + """
1. **CHART TYPE**: What kind of visualization (bar, line, pie, flowchart, etc.)
2. **DATA POINTS**: Specific values, labels, categories shown
3. **TRENDS**: Patterns, relationships, correlations visible
4. **KEY INSIGHTS**: Most important findings from the data
5. **CONTEXT**: What the chart is measuring and why
6. **CONCLUSIONS**: What the data tells us

Focus on extracting quantitative insights and data interpretation."""

    else:  # general analysis
        return base_prompt + """
1. **CONTENT TYPE**: What kind of visual content this is
2. **MAIN ELEMENTS**: Key components, text, images visible
3. **LAYOUT**: How elements are arranged and organized
4. **KEY INFORMATION**: Most important details and data
5. **CONTEXT**: Purpose and intended use of this content
6. **INSIGHTS**: What this tells us or what actions are suggested

Provide comprehensive visual understanding."""
    if _vision_system is None:
        _vision_system = AliceVision()
    return _vision_system

@function_tool
async def scan_screen() -> str:
    """
    Scan the current screen to see all windows and UI elements.
    This gives Alice awareness of what's currently visible and clickable.
    """
    try:
        vision = get_vision_system()
        
        # Get windows
        windows = vision.get_all_windows()
        
        # Get elements from active window
        elements = vision.scan_active_window()
        clickable_elements = [e for e in elements if e.is_clickable]
        
        result = f"""🔍 SCREEN SCAN RESULTS:

📊 Found {len(windows)} windows:"""
        
        # Show windows
        active_window = None
        for i, window in enumerate(windows[:10]):
            status = "🔸 ACTIVE" if window.is_active else "🔹"
            result += f"\\n{status} {window.title} ({window.process_name})"
            if window.is_active:
                active_window = window.title
        
        if len(windows) > 10:
            result += f"\\n... and {len(windows) - 10} more windows"
        
        # Show clickable elements in active window
        if active_window:
            result += f"\\n\\n🖱️ Clickable elements in '{active_window}' ({len(clickable_elements)} found):"
            for i, element in enumerate(clickable_elements[:8]):
                coords = element.coordinates
                result += f"\\n  {i+1}. {element.name} ({element.element_type}) at ({coords[0]}, {coords[1]})"
        
        if len(clickable_elements) > 8:
            result += f"\\n  ... and {len(clickable_elements) - 8} more elements"
        
        return result
        
    except Exception as e:
        logger.error(f"Screen scan failed: {e}")
        return f"❌ Screen scan failed: {e}"

@function_tool
async def click_on(description: str) -> str:
    """
    Click on a UI element based on its description.
    
    Args:
        description: Description of what to click (e.g., "close button", "OK", "file menu")
    """
    try:
        vision = get_vision_system()
        
        # Find the element
        element = vision.find_element(description)
        
        if element:
            # Click on it
            success = vision.click_element(element)
            
            if success:
                coords = element.coordinates
                return f"✅ Successfully clicked on '{element.name}' ({element.element_type}) at coordinates ({coords[0]}, {coords[1]})"
            else:
                return f"❌ Found '{element.name}' but failed to click on it"
        else:
            return f"❌ Could not find any element matching '{description}'"
            
    except Exception as e:
        logger.error(f"Click action failed: {e}")
        return f"❌ Click failed: {e}"

@function_tool
async def type_text_here(text: str) -> str:
    """
    Type text at the current cursor position.
    
    Args:
        text: Text to type
    """
    try:
        vision = get_vision_system()
        success = vision.type_text(text)
        
        if success:
            preview = text[:50] + "..." if len(text) > 50 else text
            return f"✅ Typed: '{preview}'"
        else:
            return "❌ Failed to type text"
            
    except Exception as e:
        logger.error(f"Text typing failed: {e}")
        return f"❌ Typing failed: {e}"

@function_tool
async def send_key_combination(keys: str) -> str:
    """
    Send keyboard shortcut or key combination.
    
    Args:
        keys: Key combination (e.g., "ctrl+c", "alt+tab", "enter", "esc")
    """
    try:
        vision = get_vision_system()
        success = vision.send_keys(keys)
        
        if success:
            return f"✅ Sent key combination: {keys}"
        else:
            return f"❌ Failed to send keys: {keys}"
            
    except Exception as e:
        logger.error(f"Key combination failed: {e}")
        return f"❌ Key combination failed: {e}"

@function_tool
async def take_screenshot_now() -> str:
    """
    Take a screenshot of the current screen and save it.
    """
    try:
        vision = get_vision_system()
        screenshot_path = vision.take_screenshot()
        
        if screenshot_path:
            return f"📸 Screenshot saved: {screenshot_path}"
        else:
            return "❌ Failed to take screenshot"
            
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        return f"❌ Screenshot failed: {e}"

@function_tool
async def find_elements_like(description: str) -> str:
    """
    Find all UI elements matching a description.
    
    Args:
        description: What to look for (e.g., "button", "text field", "menu")
    """
    try:
        vision = get_vision_system()
        elements = vision.scan_active_window()
        
        description_lower = description.lower()
        matches = []
        
        for element in elements:
            if (description_lower in element.name.lower() or 
                description_lower in element.element_type.lower()):
                matches.append(element)
        
        if matches:
            result = f"🔍 Found {len(matches)} elements matching '{description}':\\n"
            for i, element in enumerate(matches[:10]):
                coords = element.coordinates
                clickable = "🖱️" if element.is_clickable else "👁️"
                result += f"\\n{clickable} {i+1}. {element.name} ({element.element_type}) at ({coords[0]}, {coords[1]})"
            
            if len(matches) > 10:
                result += f"\\n... and {len(matches) - 10} more matches"
            
            return result
        else:
            return f"❌ No elements found matching '{description}'"
            
    except Exception as e:
        logger.error(f"Element search failed: {e}")
        return f"❌ Search failed: {e}"

@function_tool
async def get_active_window_info() -> str:
    """
    Get information about the currently active window.
    """
    try:
        vision = get_vision_system()
        windows = vision.get_all_windows()
        
        active_window = None
        for window in windows:
            if window.is_active:
                active_window = window
                break
        
        if active_window:
            elements = vision.scan_active_window()
            clickable_count = len([e for e in elements if e.is_clickable])
            
            return f"""🪟 ACTIVE WINDOW INFO:
📌 Title: {active_window.title}
🖥️ Process: {active_window.process_name}
📐 Size: {active_window.bounds[2] - active_window.bounds[0]}x{active_window.bounds[3] - active_window.bounds[1]}
🖱️ Clickable Elements: {clickable_count}
👁️ Total Elements: {len(elements)}"""
        else:
            return "❌ No active window found"
            
    except Exception as e:
        logger.error(f"Window info failed: {e}")
        return f"❌ Failed to get window info: {e}"

@function_tool
async def export_screen_data() -> str:
    """
    Export detailed screen data to a JSON file for analysis.
    """
    try:
        vision = get_vision_system()
        export_path = vision.export_scan_data()
        
        if export_path:
            return f"📋 Screen data exported to: {export_path}\\n\\nThis file contains detailed information about all windows and UI elements."
        else:
            return "❌ Failed to export screen data"
            
    except Exception as e:
        logger.error(f"Export failed: {e}")
        return f"❌ Export failed: {e}"

# === OCR TOOLS ===

@function_tool
async def read_text_from_image(image_path: str) -> str:
    """
    Read and extract text from an image file using OCR.
    Provide the full path to an image file to extract any text content.
    
    Args:
        image_path: Path to the image file to read text from
    """
    try:
        vision = get_vision_system()
        # Run OCR in thread pool to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, vision.extract_text_from_image, image_path)
        
        if result['success']:
            if result['text']:
                response = f"📖 TEXT EXTRACTED FROM IMAGE:\\n\\n"
                response += f"📁 File: {image_path}\\n"
                response += f"📝 Text Found: {result['text']}\\n\\n"
                
                if result['details']:
                    response += f"📊 Text Details ({result['total_items']} items):\\n"
                    for i, detail in enumerate(result['details'][:5]):
                        response += f"   {i+1}. '{detail['text']}' (confidence: {detail['confidence']:.2f}) {detail['position']}\\n"
                        
                    if result['total_items'] > 5:
                        response += f"   ... and {result['total_items'] - 5} more text items\\n"
                
                return response
            else:
                return f"👁️ Scanned image but found no readable text: {image_path}"
        else:
            return f"❌ OCR failed: {result['error']}"
            
    except Exception as e:
        logger.error(f"Image OCR failed: {e}")
        return f"❌ Error reading image: {e}"

@function_tool
async def read_screen_text() -> str:
    """
    Take a screenshot and read all text visible on the screen using OCR.
    This allows Alice to read text from any application, image, or document currently visible.
    """
    try:
        vision = get_vision_system()
        # Run OCR in thread pool to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, vision.extract_text_from_screenshot)
        
        if result['success']:
            if result['text']:
                text_preview = result['text'][:200] + "..." if len(result['text']) > 200 else result['text']
                
                response = f"📱 SCREEN TEXT READING:\\n\\n"
                response += f"📸 Screenshot: {result['screenshot']}\\n"
                response += f"📝 Text Length: {len(result['text'])} characters\\n"
                response += f"📊 Text Items: {result['total_items']}\\n\\n"
                response += f"📖 Text Content Preview:\\n{text_preview}\\n\\n"
                
                if result['total_items'] > 0 and 'details' in result:
                    response += f"🎯 Top Text Items:\\n"
                    for i, detail in enumerate(result['details'][:3]):
                        response += f"   {i+1}. '{detail['text']}' {detail['position']}\\n"
                
                return response
            else:
                return f"📱 Screenshot taken but no text found on screen\\n📸 Screenshot: {result['screenshot']}"
        else:
            return f"❌ Screen text reading failed: {result['error']}"
            
    except Exception as e:
        logger.error(f"Screen text reading failed: {e}")
        return f"❌ Error reading screen text: {e}"

# === SMART VISION ANALYSIS FUNCTIONS ===

@function_tool
async def smart_vision_analysis(
    image_path: Optional[str] = None,
    task_description: str = "Analyze this visual content",
    analysis_type: str = "auto",
    use_preprocessing: bool = True,
    force_refresh: bool = False
) -> str:
    """
    Intelligent vision analysis that automatically chooses the best method (VLM vs OCR) based on content and task.
    
    Args:
        image_path: Path to image file (if None, takes screenshot)
        task_description: What you want to analyze or extract
        analysis_type: 'auto', 'text_extraction', 'ui_analysis', 'presentation', 'document', 'chart_diagram'
        use_preprocessing: Whether to enhance image before analysis
        force_refresh: Skip cache and force new analysis
    """
    try:
        # Take screenshot if no image provided
        if not image_path:
            vision = get_vision_system()
            image_path = vision.take_screenshot()
            if not image_path:
                return "❌ Could not capture screenshot"
        
        # Check cache first (unless forcing refresh)
        cache_key = f"{_get_image_hash(image_path)}_{analysis_type}_{task_description}"
        if not force_refresh:
            cached_result = _get_cached_analysis(cache_key)
            if cached_result:
                return cached_result.get('analysis', 'Cached analysis failed')
        
        # Preprocess image if requested
        processed_image_path = image_path
        if use_preprocessing:
            processed_image_path = preprocess_image_for_analysis(image_path, analysis_type)
        
        # Determine best analysis method
        if analysis_type == "auto":
            analysis_type = await _auto_detect_analysis_type(processed_image_path, task_description)
        
        # Choose analysis method based on type and API status
        if _should_use_fallback() or analysis_type == "simple_text":
            logger.info("Using local OCR analysis")
            result = await _analyze_with_ocr(processed_image_path, task_description, analysis_type)
        else:
            logger.info(f"Using VLM analysis (type: {analysis_type})")
            result = await _analyze_with_vlm(processed_image_path, task_description, analysis_type)
            
            # Fallback to OCR if VLM fails
            if "❌" in result or "failed" in result.lower():
                _record_api_failure()
                logger.warning("VLM failed, falling back to OCR")
                result = await _analyze_with_ocr(processed_image_path, task_description, analysis_type)
            else:
                _record_api_success()
        
        # Cache the result
        _cache_analysis(cache_key, {'analysis': result})
        
        return result
        
    except Exception as e:
        logger.error(f"Smart vision analysis failed: {e}")
        return f"❌ Analysis failed: {e}"

@function_tool
async def combined_vision_analysis(
    image_path: Optional[str] = None,
    task_description: str = "Provide comprehensive analysis",
    include_ocr: bool = True,
    include_vlm: bool = True
) -> str:
    """
    Run both OCR and VLM analysis and combine results for maximum accuracy and insights.
    Perfect for complex documents where you need both text extraction and contextual understanding.
    
    Args:
        image_path: Path to image (if None, takes screenshot)
        task_description: What you want to analyze
        include_ocr: Whether to include OCR text extraction
        include_vlm: Whether to include VLM contextual analysis
    """
    try:
        # Take screenshot if needed
        if not image_path:
            vision = get_vision_system()
            image_path = vision.take_screenshot()
            if not image_path:
                return "❌ Could not capture screenshot"
        
        results = []
        
        # Run OCR analysis
        if include_ocr:
            try:
                ocr_result = await _analyze_with_ocr(image_path, "Extract all text content", "text_extraction")
                results.append(f"📝 **OCR TEXT EXTRACTION**\\n{ocr_result}\\n")
            except Exception as e:
                results.append(f"📝 **OCR ANALYSIS**: ❌ Failed - {e}\\n")
        
        # Run VLM analysis
        if include_vlm:
            try:
                vlm_result = await _analyze_with_vlm(image_path, task_description, "auto")
                results.append(f"🧠 **VLM CONTEXTUAL ANALYSIS**\\n{vlm_result}\\n")
                _record_api_success()
            except Exception as e:
                _record_api_failure()
                results.append(f"🧠 **VLM ANALYSIS**: ❌ Failed - {e}\\n")
        
        # Combine results
        combined_result = f"""🔍 **COMPREHENSIVE VISION ANALYSIS**

📊 **Task**: {task_description}
📸 **Source**: {image_path}

{''.join(results)}

💡 **COMBINED INSIGHTS**:
- Text content extracted via OCR for accuracy
- Contextual understanding provided by VLM
- Use this comprehensive view for complete understanding

"""
        return combined_result
        
    except Exception as e:
        logger.error(f"Combined analysis failed: {e}")
        return f"❌ Combined analysis failed: {e}"

@function_tool
async def check_free_vlm_providers() -> str:
    """
    Check the status of all available free VLM providers and get setup instructions.
    Shows which providers are ready to use and how to set up the unavailable ones.
    """
    try:
        status_report = get_free_vlm_status()
        return status_report
    except Exception as e:
        return f"❌ Error checking VLM providers: {e}"

@function_tool
async def analyze_with_free_vlm_only(
    image_path: Optional[str] = None,
    task_description: str = "Analyze this image",
    force_provider: Optional[str] = None
) -> str:
    """
    Analyze image using only free VLM providers (skips paid APIs).
    Perfect when you want to avoid API costs completely.
    
    Args:
        image_path: Path to image (if None, takes screenshot)
        task_description: What you want to analyze
        force_provider: Specific provider to use ('Ollama', 'Hugging Face', 'Together AI')
    """
    try:
        # Take screenshot if needed
        if not image_path:
            vision = get_vision_system()
            image_path = vision.take_screenshot()
            if not image_path:
                return "❌ Could not capture screenshot"
        
        # Use only free VLM providers
        result = await analyze_with_free_vlm(image_path, task_description)
        return result
        
    except Exception as e:
        logger.error(f"Free VLM analysis failed: {e}")
        return f"❌ Free VLM analysis failed: {e}"
    
    # Keyword-based detection from task description
    task_lower = task_description.lower()
    
    if any(word in task_lower for word in ["text", "extract", "read", "transcribe", "ocr"]):
        return "text_extraction"
    elif any(word in task_lower for word in ["ui", "interface", "button", "click", "navigate", "control"]):
        return "ui_analysis"
    elif any(word in task_lower for word in ["slide", "presentation", "powerpoint", "keynote"]):
        return "presentation"
    elif any(word in task_lower for word in ["chart", "graph", "diagram", "plot", "data", "visualization"]):
        return "chart_diagram"
    elif any(word in task_lower for word in ["document", "report", "article", "paper", "form"]):
        return "document"
    else:
        # Try to detect from image content
        try:
            processed_path = preprocess_image_for_analysis(image_path, "auto")
            from PIL import Image
            image = Image.open(processed_path)
            detected_type = _detect_image_type(image)
            
            type_mapping = {
                "text": "text_extraction",
                "ui": "ui_analysis", 
                "chart": "chart_diagram"
            }
            
            return type_mapping.get(detected_type, "document")
            
        except Exception:
            return "document"  # Safe fallback

async def _analyze_with_ocr(image_path: str, task_description: str, analysis_type: str) -> str:
    """Analyze image using local OCR"""
    try:
        vision = get_vision_system()
        ocr_result = vision.extract_text_from_image(image_path)
        
        if not ocr_result['success']:
            return f"❌ OCR analysis failed: {ocr_result.get('error', 'Unknown error')}"
        
        extracted_text = ocr_result['text']
        
        if not extracted_text.strip():
            return "ℹ️ No text content found in image via OCR"
        
        # Format based on analysis type
        if analysis_type == "text_extraction":
            return f"""📝 **LOCAL OCR ANALYSIS**

🎯 **Task**: {task_description}

📋 **Extracted Text**:
{extracted_text}

📊 **Details**:
- Found {ocr_result['total_items']} text regions
- Confidence levels available for each region
- Total characters: {len(extracted_text)}

💡 **Note**: This is raw text extraction. For context and layout understanding, consider using VLM analysis.
"""
        else:
            return f"""📝 **LOCAL OCR FALLBACK**

🎯 **Task**: {task_description}
⚠️ **Note**: Using OCR fallback - limited contextual understanding

📋 **Text Content Found**:
{extracted_text}

💡 **Suggestion**: For better analysis of {analysis_type}, try VLM when API is available.
"""
            
    except Exception as e:
        logger.error(f"OCR analysis failed: {e}")
        return f"❌ OCR analysis failed: {e}"

async def _analyze_with_vlm(image_path: str, task_description: str, analysis_type: str) -> str:
    """Analyze image using VLM - tries paid APIs first, then free alternatives"""
    
    # First try Gemini (paid API)
    gemini_result = await _try_gemini_vlm(image_path, task_description, analysis_type)
    if gemini_result and "❌" not in gemini_result:
        return gemini_result
    
    # If Gemini fails, try free VLM providers
    logger.info("Gemini unavailable, trying free VLM providers...")
    free_vlm_result = await analyze_with_free_vlm(
        image_path, 
        _get_structured_prompt(analysis_type, task_description)
    )
    
    return free_vlm_result

async def _try_gemini_vlm(image_path: str, task_description: str, analysis_type: str) -> Optional[str]:
    """Try Gemini VLM specifically"""
    try:
        import os
        from dotenv import load_dotenv
        import google.generativeai as genai
        
        load_dotenv()
        api_key = os.getenv('GOOGLE_API_KEY')
        
        if not api_key:
            return None
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Read image
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
        
        # Get structured prompt
        analysis_prompt = _get_structured_prompt(analysis_type, task_description)
        
        # Generate content
        response = model.generate_content([
            analysis_prompt,
            {"mime_type": "image/png", "data": image_data}
        ])
        
        return f"""🧠 **GEMINI VLM ANALYSIS** ({analysis_type.upper()})

🎯 **Task**: {task_description}
📸 **Image**: {image_path}

{response.text}

✨ **Analysis powered by**: Gemini 2.0 Flash VLM
⚡ **Processing**: Enhanced with structured prompting
"""
        
    except Exception as e:
        logger.error(f"Gemini VLM failed: {e}")
        return None

@function_tool
async def analyze_image_content(image_path: str) -> str:
    """
    Analyze an image file for text content and provide detailed information.
    This gives comprehensive analysis including image properties and all extracted text.
    
    Args:
        image_path: Path to the image file to analyze
    """
    try:
        vision = get_vision_system()
        # Run analysis in thread pool to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, vision.analyze_image_content, image_path)
        
        if result['success']:
            response = f"🔍 IMAGE ANALYSIS RESULTS:\\n\\n"
            response += f"📁 File: {result['image_path']}\\n"
            response += f"📏 Size: {result['image_size']}\\n"
            response += f"🎨 Format: {result['image_format']} ({result['image_mode']})\\n"
            response += f"📝 Text Found: {'Yes' if result['text_found'] else 'No'}\\n"
            
            if result['text_found']:
                response += f"📊 Text Length: {result['text_length']} characters\\n"
                response += f"📋 Text Items: {result['text_items']}\\n\\n"
                
                ocr_result = result['ocr_result']
                if ocr_result['success'] and ocr_result['text']:
                    response += f"📖 EXTRACTED TEXT:\\n{ocr_result['text']}\\n\\n"
                    
                    if ocr_result['details']:
                        response += f"🎯 TEXT DETAILS:\\n"
                        for i, detail in enumerate(ocr_result['details']):
                            response += f"   {i+1}. '{detail['text']}' (confidence: {detail['confidence']:.2f}) {detail['position']}\\n"
            else:
                response += "\\n👁️ No readable text found in the image."
                
            return response
        else:
            return f"❌ Image analysis failed: {result['error']}"
            
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        return f"❌ Error analyzing image: {e}"

@function_tool
async def analyze_screen_with_gemini(task_description: str = "Describe what you see on the screen") -> str:
    """
    Use Gemini vision AI to analyze the current screen content with advanced understanding.
    Perfect for analyzing presentations, documents, UI elements, charts, and complex visual content.
    
    Args:
        task_description: Specific task or question about the screen content (e.g., "What are the main points in this presentation?")
    """
    try:
        import os
        from dotenv import load_dotenv
        import base64
        import tempfile
        
        load_dotenv()
        api_key = os.getenv('GOOGLE_API_KEY')
        
        if not api_key:
            return "❌ Google API key not found. Cannot use Gemini vision analysis."
        
        # Take a screenshot first
        vision = get_vision_system()
        screenshot_path = vision.take_screenshot()
        
        if not screenshot_path:
            return "❌ Could not capture screenshot"
        
        # Use Gemini for advanced vision analysis
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            # Initialize Gemini vision model
            model = genai.GenerativeModel('gemini-2.0-flash')  # Use regular model instead of experimental
            
            # Read and encode the image
            with open(screenshot_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Create a more sophisticated prompt for presentation analysis
            analysis_prompt = f"""
You are an expert visual analyst. Please analyze this screen capture and provide a detailed analysis.

Specific task: {task_description}

Please provide:
1. **Overall Description**: What type of content is displayed (presentation, document, website, etc.)
2. **Main Content**: Key information, text, or data visible
3. **Structure**: Layout, sections, and organization
4. **Important Elements**: Notable UI elements, buttons, or interactive areas
5. **Key Insights**: Main points, conclusions, or actionable information

If this is a presentation or document:
- Summarize the main points or slides content
- Identify the topic and key themes
- Note any important data, charts, or visual elements

Be detailed and specific in your analysis. Focus on providing actionable insights about what's displayed.
"""

            # Send to Gemini for analysis
            response = model.generate_content([
                analysis_prompt,
                {"mime_type": "image/png", "data": image_data}
            ])
            
            # Format the response
            analysis_result = f"""🧠 **GEMINI VISION ANALYSIS** 🎯

📋 **Task**: {task_description}

🔍 **Analysis Results**:
{response.text}

📸 **Screenshot**: {screenshot_path}
"""
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return f"❌ Gemini vision analysis failed: {e}\\n\\nFalling back to basic image analysis..."
            
    except Exception as e:
        logger.error(f"Screen analysis failed: {e}")
        return f"❌ Error analyzing screen: {e}"

@function_tool  
async def analyze_image_with_gemini(image_path: str, analysis_request: str = "Analyze this image") -> str:
    """
    Use Gemini vision AI to analyze any image file with advanced understanding.
    Perfect for analyzing presentations, documents, charts, screenshots, and complex visual content.
    
    Args:
        image_path: Path to the image file to analyze
        analysis_request: Specific analysis request (e.g., "What are the key points in this slide?", "Explain this chart")
    """
    try:
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        api_key = os.getenv('GOOGLE_API_KEY')
        
        if not api_key:
            return "❌ Google API key not found. Cannot use Gemini vision analysis."
        
        if not os.path.exists(image_path):
            return f"❌ Image file not found: {image_path}"
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            # Initialize Gemini vision model  
            model = genai.GenerativeModel('gemini-2.0-flash')  # Use regular model instead of experimental
            
            # Read and encode the image
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Create sophisticated analysis prompt
            analysis_prompt = f"""
You are an expert visual analyst with deep understanding of presentations, documents, and complex visual content.

Analysis Request: {analysis_request}

Please provide a comprehensive analysis including:

1. **Content Type**: What kind of document/content is this? (presentation slide, chart, document, etc.)
2. **Main Message**: What is the primary message or purpose?
3. **Key Information**: All important text, data, and details visible
4. **Visual Elements**: Charts, graphs, images, and their significance  
5. **Structure & Layout**: How the content is organized
6. **Action Items**: Any tasks, conclusions, or next steps mentioned
7. **Context**: Subject matter and intended audience

Be thorough and extract all meaningful information. If this is a presentation slide, identify:
- Slide title and main topic
- Bullet points and key messages
- Any data, statistics, or examples
- Visual aids and their meaning

Provide specific, actionable insights about the content.
"""

            # Send to Gemini for analysis
            response = model.generate_content([
                analysis_prompt,
                {"mime_type": "image/png", "data": image_data}
            ])
            
            # Format the response
            analysis_result = f"""🧠 **GEMINI VISION ANALYSIS** 🎯

📁 **File**: {image_path}
📋 **Request**: {analysis_request}

🔍 **Detailed Analysis**:
{response.text}
"""
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Gemini image analysis failed: {e}")
            return f"❌ Gemini vision analysis failed: {e}"
            
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        return f"❌ Error analyzing image: {e}"

# List of all vision tools for easy import
ALICE_VISION_TOOLS = [
    scan_screen,
    click_on,
    type_text_here,
    send_key_combination,
    take_screenshot_now,
    find_elements_like,
    get_active_window_info,
    export_screen_data,
    read_text_from_image,
    read_screen_text,
    smart_vision_analysis,        # NEW: Intelligent VLM/OCR routing
    combined_vision_analysis,     # NEW: Comprehensive dual analysis
    check_free_vlm_providers,     # NEW: Check free VLM status
    analyze_with_free_vlm_only,   # NEW: Use only free VLMs
    analyze_image_content,
    analyze_screen_with_gemini,
    analyze_image_with_gemini
]