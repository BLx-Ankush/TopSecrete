"""
ALICE Real-Time Memory Injector
Bridges Mem0 long-term memory into the active Gemini Live API WebSocket stream.

Previously, memory was a snapshot loaded once at startup and saved once at shutdown.
This module creates a lightweight background task that:
  1. Periodically queries Mem0 for memories relevant to recent conversation turns
  2. Formats them into a context update message
  3. Injects them into the active Gemini WebSocket via clientContent without
     interrupting or restarting the audio stream

This gives ALICE dynamic, mid-conversation memory recall — similar to how
a human naturally remembers context from earlier in a conversation.
"""

import asyncio
import logging
import os
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from gemini_streaming_client import GeminiStreamingClient

logger = logging.getLogger(__name__)

# How often to check for new relevant memories (seconds)
INJECT_INTERVAL_SECONDS = 45

# Maximum number of memories to inject at once (to avoid token overload)
MAX_MEMORIES_TO_INJECT = 5


class MemoryInjector:
    """
    Background worker that injects Mem0 memories into an active Gemini WebSocket session.
    """

    def __init__(
        self,
        user_id: str,
        streaming_client: "GeminiStreamingClient",
        inject_interval: int = INJECT_INTERVAL_SECONDS,
    ):
        self.user_id = user_id
        self.streaming_client = streaming_client
        self.inject_interval = inject_interval

        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_injected_memory_ids: set = set()

        # The conversation buffer stores the last few turns for semantic querying
        self._recent_turns: list[str] = []

        try:
            from memory_store import ConversationMemory
            self._memory = ConversationMemory(user_id)
            self._mem0_available = True
            logger.info(f"[MemoryInjector] Initialized for user: {user_id}")
        except Exception as e:
            self._memory = None
            self._mem0_available = False
            logger.warning(f"[MemoryInjector] Mem0 not available: {e}")

    # ── Public API ─────────────────────────────────────────────────────────────

    def record_turn(self, text: str):
        """
        Called every time a new conversation turn happens.
        Keeps a rolling window of the last 6 turns for context querying.
        """
        if text and text.strip():
            self._recent_turns.append(text.strip())
            if len(self._recent_turns) > 6:
                self._recent_turns.pop(0)

    def start(self):
        """Start the background memory injection task."""
        if not self._mem0_available:
            logger.info("[MemoryInjector] Skipping start — Mem0 not configured")
            return
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._injection_loop())
        logger.info(
            f"[MemoryInjector] Background task started "
            f"(interval={self.inject_interval}s)"
        )

    def stop(self):
        """Stop the background task gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("[MemoryInjector] Background task stopped")

    # ── Background loop ────────────────────────────────────────────────────────

    async def _injection_loop(self):
        """
        Main loop: waits for the interval, fetches relevant memories,
        then injects them into the WebSocket stream.
        """
        while self._running:
            try:
                await asyncio.sleep(self.inject_interval)

                if not self._running:
                    break

                # Only inject if there is an active stream
                from gemini_streaming_client import ConnectionState
                if self.streaming_client.state != ConnectionState.CONNECTED:
                    logger.debug("[MemoryInjector] Skipping — stream not connected")
                    continue

                await self._fetch_and_inject()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MemoryInjector] Error in injection loop: {e}", exc_info=True)
                # Don't crash the loop — wait and retry
                await asyncio.sleep(10)

    async def _fetch_and_inject(self):
        """
        Queries Mem0 for memories relevant to recent conversation turns,
        then injects new ones into the Gemini stream.
        """
        if not self._memory or not self._recent_turns:
            return

        # Build a query from the last couple of turns
        query = " ".join(self._recent_turns[-2:])
        if not query.strip():
            return

        try:
            # Search for semantically relevant memories (non-blocking)
            loop = asyncio.get_event_loop()
            memories = await loop.run_in_executor(
                None,
                lambda: self._memory.search_memories(query, limit=MAX_MEMORIES_TO_INJECT)
            )

            if not memories:
                logger.debug("[MemoryInjector] No relevant memories found")
                return

            # Filter out already-injected memories to avoid repetition
            new_memories = [
                m for m in memories
                if m.get("id") not in self._last_injected_memory_ids
            ]

            if not new_memories:
                logger.debug("[MemoryInjector] All relevant memories already injected")
                return

            # Format for injection
            memory_texts = [
                m.get("memory", "").strip()
                for m in new_memories
                if m.get("memory", "").strip()
            ]
            if not memory_texts:
                return

            context_text = (
                "[MEMORY CONTEXT — Long-term facts relevant to this conversation:]\n"
                + "\n".join(f"• {t}" for t in memory_texts)
            )

            # Inject as a system-role clientContent message into the WebSocket
            await self._inject_context(context_text)

            # Mark these as injected
            for m in new_memories:
                if m.get("id"):
                    self._last_injected_memory_ids.add(m["id"])

            logger.info(
                f"[MemoryInjector] Injected {len(memory_texts)} memories "
                f"into active stream"
            )

        except Exception as e:
            logger.error(f"[MemoryInjector] Failed to fetch/inject memories: {e}")

    async def _inject_context(self, context_text: str):
        """
        Sends a silent system context message over the Gemini WebSocket.
        Uses clientContent with role='user' and turnComplete=False so that
        the model absorbs the context without generating an audio response.
        """
        msg = {
            "clientContent": {
                "turns": [
                    {
                        "role": "user",
                        "parts": [{"text": f"[system context] {context_text}"}]
                    }
                ],
                "turnComplete": False  # False = don't trigger a model response
            }
        }
        try:
            await self.streaming_client._send_message(msg)
            logger.debug("[MemoryInjector] Context message sent to WebSocket")
        except Exception as e:
            logger.error(f"[MemoryInjector] Failed to send context message: {e}")
