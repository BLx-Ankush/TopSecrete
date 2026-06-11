"""
Offline Fallback Router — Domain 2A (Phase 4)
=============================================
When ALICE detects high API latency or a network failure, she gracefully
degrades from Cloud (Gemini Live) to a local stack (Whisper-Tiny STT +
Ollama LLM) instead of crashing.

Architecture
------------
                        ┌─────────────────────┐
   User Audio ──────►  │  PingWatchdog        │
                        │  (checks API every   │
                        │   5 s in background) │
                        └──────┬──────────────┘
                               │  ping OK?
                     Yes ──────┘           No (>300ms or timeout)
                     │                     │
                     ▼                     ▼
              CLOUD MODE             OFFLINE MODE
         (Gemini Live + WebSocket)  (Whisper-tiny + Ollama)
                                         │
                               plays "offline chime"

Usage
-----
    from offline_fallback import OfflineFallbackRouter, ConnectionMode

    router = OfflineFallbackRouter()
    await router.start_watchdog()           # background ping loop

    mode = router.current_mode             # ConnectionMode.CLOUD or .OFFLINE
    answer = await router.respond(audio_bytes_or_text)

    await router.stop_watchdog()
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Optional, Callable, Awaitable

import httpx

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
PING_INTERVAL_S       = 5       # seconds between watchdog checks
PING_TIMEOUT_MS       = 300     # ms — if slower, switch to offline mode
PING_TARGET_URL       = "https://generativelanguage.googleapis.com/"
RECOVERY_CHECKS       = 3       # consecutive good pings before switching back to cloud
OFFLINE_CHIME         = "🔔 [Offline mode activated — using local models]"

# ── Optional Whisper (local STT) ──────────────────────────────────────────────
try:
    import whisper as _whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("⚠️  openai-whisper not installed. Offline STT unavailable. "
                   "Install with: pip install openai-whisper")

# ── Optional Ollama client (local LLM) ───────────────────────────────────────
try:
    import ollama as _ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("⚠️  ollama not installed. Offline LLM unavailable. "
                   "Install with: pip install ollama  (+ run: ollama pull llama3)")


class ConnectionMode(str, Enum):
    CLOUD   = "cloud"
    OFFLINE = "offline"


class OfflineFallbackRouter:
    """
    Monitors network health and routes ALICE's voice pipeline between
    the cloud (Gemini Live) and local offline models.
    """

    def __init__(
        self,
        ping_interval: float = PING_INTERVAL_S,
        ping_timeout_ms: float = PING_TIMEOUT_MS,
        on_mode_change: Optional[Callable[[ConnectionMode], Awaitable[None]]] = None,
    ):
        self.ping_interval    = ping_interval
        self.ping_timeout     = ping_timeout_ms / 1000.0   # convert to seconds
        self.on_mode_change   = on_mode_change

        self.current_mode: ConnectionMode = ConnectionMode.CLOUD
        self._good_ping_streak: int = 0
        self._watchdog_task: Optional[asyncio.Task] = None

        # Lazy-load whisper model only when needed (saves RAM in cloud mode)
        self._whisper_model = None

    # ── Watchdog ──────────────────────────────────────────────────────────────

    async def start_watchdog(self):
        """Start the background ping loop."""
        if self._watchdog_task and not self._watchdog_task.done():
            return
        self._watchdog_task = asyncio.create_task(self._ping_loop())
        logger.info("[OfflineFallback] Watchdog started (ping every %ss, timeout %sms)",
                    self.ping_interval, PING_TIMEOUT_MS)

    async def stop_watchdog(self):
        if self._watchdog_task:
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass
        logger.info("[OfflineFallback] Watchdog stopped")

    async def _ping_loop(self):
        while True:
            try:
                await asyncio.sleep(self.ping_interval)
                ping_ok = await self._check_ping()
                await self._update_mode(ping_ok)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"[OfflineFallback] Ping loop error: {e}")

    async def _check_ping(self) -> bool:
        """Returns True if API is reachable within timeout."""
        try:
            t0 = time.monotonic()
            async with httpx.AsyncClient(timeout=self.ping_timeout) as client:
                await client.head(PING_TARGET_URL)
            latency_ms = (time.monotonic() - t0) * 1000
            logger.debug(f"[OfflineFallback] Ping OK — {latency_ms:.0f}ms")
            return latency_ms < (PING_TIMEOUT_MS * 1.5)  # allow small overrun
        except Exception as e:
            logger.debug(f"[OfflineFallback] Ping FAIL — {e}")
            return False

    async def _update_mode(self, ping_ok: bool):
        old_mode = self.current_mode

        if ping_ok:
            self._good_ping_streak += 1
            if (self.current_mode == ConnectionMode.OFFLINE
                    and self._good_ping_streak >= RECOVERY_CHECKS):
                self.current_mode = ConnectionMode.CLOUD
                self._good_ping_streak = 0
                logger.info("[OfflineFallback] ✅ Network recovered → switching back to CLOUD mode")
                if self.on_mode_change:
                    await self.on_mode_change(self.current_mode)
        else:
            self._good_ping_streak = 0
            if self.current_mode == ConnectionMode.CLOUD:
                self.current_mode = ConnectionMode.OFFLINE
                logger.warning("[OfflineFallback] ⚠️  Network lost → switching to OFFLINE mode")
                print(OFFLINE_CHIME)
                if self.on_mode_change:
                    await self.on_mode_change(self.current_mode)

    # ── Local offline respond ─────────────────────────────────────────────────

    async def respond_offline(self, text_query: str) -> str:
        """
        Generate a response using the local Ollama LLM when in offline mode.
        Returns a plain text response string.
        """
        if not OLLAMA_AVAILABLE:
            return ("I'm currently offline and my local language model is not installed. "
                    "Please check your internet connection.")
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: _ollama.chat(
                    model="llama3",
                    messages=[
                        {"role": "system",  "content": "You are ALICE, a helpful AI assistant running in offline mode. Keep answers brief and practical."},
                        {"role": "user",    "content": text_query},
                    ]
                )
            )
            return response["message"]["content"]
        except Exception as e:
            logger.error(f"[OfflineFallback] Ollama error: {e}")
            return f"I'm in offline mode but my local model encountered an error: {e}"

    async def transcribe_offline(self, audio_path: str) -> str:
        """
        Transcribe an audio file using Whisper-Tiny when offline.
        Returns transcribed text.
        """
        if not WHISPER_AVAILABLE:
            return ""
        try:
            if self._whisper_model is None:
                loop = asyncio.get_event_loop()
                logger.info("[OfflineFallback] Loading Whisper-Tiny model…")
                self._whisper_model = await loop.run_in_executor(
                    None, lambda: _whisper.load_model("tiny")
                )
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._whisper_model.transcribe(audio_path)
            )
            text = result.get("text", "").strip()
            logger.info(f"[OfflineFallback] Whisper transcription: {text[:80]}")
            return text
        except Exception as e:
            logger.error(f"[OfflineFallback] Whisper error: {e}")
            return ""

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "current_mode": self.current_mode.value,
            "good_ping_streak": self._good_ping_streak,
            "whisper_available": WHISPER_AVAILABLE,
            "ollama_available": OLLAMA_AVAILABLE,
            "watchdog_running": bool(self._watchdog_task and not self._watchdog_task.done()),
        }
