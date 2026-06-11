"""
Alice Semantic Vision Engine — Phase 4 Upgraded
================================================
Replaces fragile pyautogui pixel-coordinate clicking with Gemini multimodal
screenshot analysis. Instead of hardcoding (x, y) positions, this module:

  1. Captures a screenshot cropped to the ACTIVE WINDOW only (1B — Intelligent Cropping)
  2. Waits for screen animations to fully stop (1C — Animation Quiescence)
  3. Checks an in-memory cache keyed by (window_title, pixel_hash, element) (1A — Mental Map)
  4. On cache miss: sends the cropped image to Gemini Flash Vision API
  5. Stores the result in the cache for future calls on the same static screen
  6. Clicks the returned absolute screen coordinate via pyautogui

Phase 4 Domain 1 Improvements:
  1A. Mental Map Cache   — skips Gemini entirely when same screen + same element
  1B. Intelligent Crop   — sends only the active window, not the full 1080p desktop
  1C. Quiescence Check   — waits ≤1.5s for pixel-diff to drop below threshold
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import time
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ── PIL / Pillow ──────────────────────────────────────────────────────────────
try:
    from PIL import ImageGrab, Image, ImageChops
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("⚠️  PIL not available — install with: pip install Pillow")

# ── numpy (for pixel-diff RMS in quiescence check) ───────────────────────────
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("⚠️  numpy not available — install with: pip install numpy")

# ── pygetwindow (active window cropping) ──────────────────────────────────────
try:
    import pygetwindow as gw
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    PYGETWINDOW_AVAILABLE = False
    logger.warning("⚠️  pygetwindow not available — install with: pip install pygetwindow")

# ── pyautogui (mouse clicks) ──────────────────────────────────────────────────
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logger.warning("⚠️  pyautogui not available — install with: pip install pyautogui")

# ── httpx (Gemini REST calls) ─────────────────────────────────────────────────
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("⚠️  httpx not available — install with: pip install httpx")


VISION_MODEL = "gemini-2.0-flash"
GEMINI_VISION_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{VISION_MODEL}:generateContent"
)

# Quiescence thresholds
QUIESCENCE_TIMEOUT_S   = 1.5    # max wait for UI to settle
QUIESCENCE_INTERVAL_S  = 0.10   # check every 100ms
QUIESCENCE_THRESHOLD   = 1.0    # mean pixel diff below this = settled


class SemanticVisionEngine:
    """
    ALICE's Gemini-powered semantic vision engine.
    Locates UI elements by natural language, not pixel coordinates.

    Phase 4 Upgrades built in:
      • Mental Map Cache (1A)   — (window_title, img_hash, description) → (rel_x, rel_y)
      • Active Window Crop (1B) — only the active window is sent to Gemini
      • Quiescence Guard (1C)   — waits for animations to finish before screenshot
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        if not self.api_key:
            logger.warning("⚠️  SemanticVisionEngine: GOOGLE_API_KEY not set")

        # 1A: Mental Map Cache
        # Key:   (window_title: str, img_hash: str, element_description: str)
        # Value: (rel_x: int, rel_y: int)  — coordinates relative to window top-left
        self.element_cache: Dict[Tuple[str, str, str], Tuple[int, int]] = {}
        self._cache_hits   = 0
        self._cache_misses = 0

    # ── 1C: Animation Quiescence ──────────────────────────────────────────────

    def wait_for_ui_to_settle(
        self,
        bbox: Optional[Tuple[int, int, int, int]] = None,
        timeout: float = QUIESCENCE_TIMEOUT_S,
    ) -> None:
        """
        Block until the screen region stops changing (animations finished).
        Uses mean pixel difference between two consecutive frames.
        Falls back gracefully if PIL or numpy are unavailable.
        """
        if not PIL_AVAILABLE or not NUMPY_AVAILABLE:
            time.sleep(0.15)   # conservative fixed wait as fallback
            return

        deadline = time.monotonic() + timeout
        prev_arr = np.array(ImageGrab.grab(bbox=bbox), dtype=np.float32)

        while time.monotonic() < deadline:
            time.sleep(QUIESCENCE_INTERVAL_S)
            curr_arr = np.array(ImageGrab.grab(bbox=bbox), dtype=np.float32)
            mean_diff = float(np.mean(np.abs(curr_arr - prev_arr)))

            if mean_diff < QUIESCENCE_THRESHOLD:
                logger.debug(f"[SemanticVision] UI settled (mean_diff={mean_diff:.3f})")
                return

            prev_arr = curr_arr

        logger.debug("[SemanticVision] Quiescence timeout — proceeding anyway")

    # ── 1B: Active Window Crop ────────────────────────────────────────────────

    def get_active_window_bbox(self) -> Tuple[Optional[Tuple[int, int, int, int]], str]:
        """
        Returns ((left, top, right, bottom), window_title) for the active window.
        Falls back to (None, 'FULLSCREEN') if pygetwindow is unavailable.
        """
        if not PYGETWINDOW_AVAILABLE:
            return None, "FULLSCREEN"
        try:
            win = gw.getActiveWindow()
            if win and win.width > 0 and win.height > 0:
                bbox = (win.left, win.top, win.right, win.bottom)
                return bbox, win.title or "UNTITLED"
        except Exception as e:
            logger.debug(f"[SemanticVision] pygetwindow error: {e}")
        return None, "FULLSCREEN"

    # ── Screen capture (crop + hash) ──────────────────────────────────────────

    def capture_window_b64(
        self, scale: float = 0.5
    ) -> Tuple[Optional[str], Optional[Tuple[int, int, int, int]], str, str]:
        """
        Capture the active window (cropped), downscale, and base64-encode.

        Returns:
            (b64_str, original_bbox, window_title, pixel_hash)
            original_bbox is (left, top, right, bottom) of the captured region
            in ORIGINAL screen coordinates.
        """
        if not PIL_AVAILABLE:
            logger.error("[SemanticVision] PIL not installed — cannot capture")
            return None, None, "UNKNOWN", ""

        try:
            # 1B: Get active window bounds
            bbox, win_title = self.get_active_window_bbox()

            # 1C: Wait for animations to stop BEFORE taking the screenshot
            self.wait_for_ui_to_settle(bbox=bbox)

            # Grab the cropped region (or full screen if no active window found)
            img: Image.Image = ImageGrab.grab(bbox=bbox)

            # 1A: Compute pixel hash on the ORIGINAL resolution image
            pixel_hash = hashlib.md5(img.tobytes()).hexdigest()

            # Downscale for Gemini (reduces token cost)
            if scale != 1.0:
                w, h = img.size
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64_str = base64.b64encode(buf.getvalue()).decode()

            # Normalise bbox: if None (full screen), create a bbox covering the full screen
            if bbox is None:
                screen = ImageGrab.grab()
                bbox = (0, 0, screen.width, screen.height)

            return b64_str, bbox, win_title, pixel_hash

        except Exception as e:
            logger.error(f"[SemanticVision] Screen capture failed: {e}")
            return None, None, "UNKNOWN", ""

    # ── 1A: Mental Map Cache helpers ──────────────────────────────────────────

    def _cache_key(self, win_title: str, pixel_hash: str, description: str) -> tuple:
        return (win_title, pixel_hash, description.lower().strip())

    def _cache_get(self, win_title: str, pixel_hash: str, description: str) -> Optional[Tuple[int, int]]:
        return self.element_cache.get(self._cache_key(win_title, pixel_hash, description))

    def _cache_set(self, win_title: str, pixel_hash: str, description: str, rel_xy: Tuple[int, int]):
        self.element_cache[self._cache_key(win_title, pixel_hash, description)] = rel_xy

    def cache_stats(self) -> dict:
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total else 0
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "total": total,
            "hit_rate_pct": round(hit_rate, 1),
            "cached_elements": len(self.element_cache),
        }

    def invalidate_cache(self):
        """Call this when the user switches apps or resizes a window."""
        self.element_cache.clear()
        logger.info("[SemanticVision] Mental Map Cache invalidated")

    # ── Core element finder ───────────────────────────────────────────────────

    async def find_element(
        self,
        element_description: str,
        scale: float = 0.5,
    ) -> Optional[Tuple[int, int]]:
        """
        Locate a UI element by natural language description.

        Returns:
            Absolute (x, y) screen coordinates, or None if not found.

        Flow:
            1. Capture window (with quiescence + crop)
            2. Check Mental Map Cache → return instantly if hit
            3. On miss → call Gemini Vision API
            4. Store result in cache
            5. Convert relative window coords → absolute screen coords
        """
        if not HTTPX_AVAILABLE:
            logger.error("[SemanticVision] httpx not installed")
            return None

        # Step 1: Capture + crop + hash
        img_b64, bbox, win_title, pixel_hash = self.capture_window_b64(scale=scale)
        if not img_b64 or not bbox:
            return None

        left, top, right, bottom = bbox
        win_w = right - left
        win_h = bottom - top

        # Step 2: 1A Cache Check
        cached = self._cache_get(win_title, pixel_hash, element_description)
        if cached is not None:
            rel_x, rel_y = cached
            abs_x = left + rel_x
            abs_y = top + rel_y
            self._cache_hits += 1
            logger.info(
                f"[SemanticVision] CACHE HIT '{element_description}' "
                f"→ abs({abs_x}, {abs_y})  [stats: {self.cache_stats()}]"
            )
            return (abs_x, abs_y)

        self._cache_misses += 1
        logger.info(
            f"[SemanticVision] CACHE MISS '{element_description}' "
            f"— querying Gemini (window='{win_title}')"
        )

        # Step 3: Gemini Vision API call
        prompt = (
            f"Look at this screenshot of an active application window titled '{win_title}'. "
            f"Locate '{element_description}'. "
            f"Reply ONLY with a JSON object in this exact format: "
            f"{{\"found\": true, \"x\": <center_x_percent>, \"y\": <center_y_percent>}} "
            f"where x and y are the element's center position as PERCENTAGES (0–100) "
            f"of the IMAGE width and height respectively. "
            f"If you cannot find the element, reply: {{\"found\": false}}"
        )

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": img_b64}}
                ]
            }],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 120}
        }

        try:
            t0 = time.monotonic()
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(
                    GEMINI_VISION_URL,
                    params={"key": self.api_key},
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
            latency_ms = (time.monotonic() - t0) * 1000

            result_text = (
                resp.json()
                .get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )

            # Strip markdown code fences if Gemini wraps the response
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1].strip()
                if result_text.startswith("json"):
                    result_text = result_text[4:].strip()

            data = json.loads(result_text)

            if not data.get("found", False):
                logger.info(f"[SemanticVision] Element not found: '{element_description}'")
                return None

            x_pct = float(data["x"]) / 100.0
            y_pct = float(data["y"]) / 100.0

            # Convert percentages → relative coordinates within the window
            rel_x = int(x_pct * win_w)
            rel_y = int(y_pct * win_h)

            # Step 4: Store in Mental Map Cache
            self._cache_set(win_title, pixel_hash, element_description, (rel_x, rel_y))

            # Step 5: Convert to absolute screen coordinates
            abs_x = left + rel_x
            abs_y = top + rel_y

            logger.info(
                f"[SemanticVision] Found '{element_description}' "
                f"at abs({abs_x}, {abs_y}) via Gemini in {latency_ms:.0f}ms"
            )
            return (abs_x, abs_y)

        except json.JSONDecodeError as e:
            logger.error(f"[SemanticVision] JSON parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"[SemanticVision] Vision API call failed: {e}", exc_info=True)
            return None

    # ── Public actions ────────────────────────────────────────────────────────

    async def click_element(
        self,
        element_description: str,
        double_click: bool = False,
        scale: float = 0.5,
    ) -> bool:
        """Find an element by description and click it."""
        coords = await self.find_element(element_description, scale=scale)
        if not coords:
            logger.warning(f"[SemanticVision] Cannot click — '{element_description}' not found")
            return False

        if not PYAUTOGUI_AVAILABLE:
            logger.error("[SemanticVision] pyautogui not available")
            return False

        x, y = coords
        try:
            if double_click:
                pyautogui.doubleClick(x, y)
            else:
                pyautogui.click(x, y)
            logger.info(
                f"[SemanticVision] {'Double-clicked' if double_click else 'Clicked'} "
                f"'{element_description}' at ({x}, {y})"
            )
            return True
        except Exception as e:
            logger.error(f"[SemanticVision] Click failed: {e}")
            return False

    async def type_into_element(
        self,
        element_description: str,
        text: str,
        scale: float = 0.5,
    ) -> bool:
        """Find an input field, click it, and type text (Unicode-safe via clipboard)."""
        clicked = await self.click_element(element_description, scale=scale)
        if not clicked:
            return False

        time.sleep(0.2)  # Let the element gain focus

        try:
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            logger.info(f"[SemanticVision] Typed (clipboard) into '{element_description}': {text[:50]}")
        except ImportError:
            pyautogui.typewrite(text, interval=0.02)
            logger.info(f"[SemanticVision] Typed (typewrite) into '{element_description}': {text[:50]}")
        except Exception as e:
            logger.error(f"[SemanticVision] Type failed: {e}")
            return False

        return True

    async def semantic_click(self, element_description: str) -> bool:
        """Alias for click_element — matches tool_registry export name."""
        return await self.click_element(element_description)

    async def semantic_type_into(self, element_description: str, text: str) -> bool:
        """Alias for type_into_element — matches tool_registry export name."""
        return await self.type_into_element(element_description, text)


# ── Module-level singleton ────────────────────────────────────────────────────
_engine: Optional[SemanticVisionEngine] = None


def get_semantic_vision_engine() -> SemanticVisionEngine:
    """Returns the shared SemanticVisionEngine instance (created on first call)."""
    global _engine
    if _engine is None:
        _engine = SemanticVisionEngine()
    return _engine


# ── Convenience functions (used by tool_registry) ────────────────────────────

async def semantic_click(element_description: str) -> bool:
    """Module-level convenience wrapper used by tool_registry."""
    return await get_semantic_vision_engine().click_element(element_description)


async def semantic_type_into(element_description: str, text: str) -> bool:
    """Module-level convenience wrapper used by tool_registry."""
    return await get_semantic_vision_engine().type_into_element(element_description, text)
