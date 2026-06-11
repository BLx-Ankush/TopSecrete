"""
Session Summarizer — Domain 3A (Phase 4)
=========================================
At the end of each ALICE session (on LiveKit room disconnect), this module:
  1. Takes the full in-session conversation transcript
  2. Calls Gemini Flash to generate a compact structured summary
  3. Injects that summary into Mem0 so future sessions have continuity

This bridges the gap between ALICE (only remembers what was spoken) and
Windows Copilot Recall (passive screenshot memory), giving ALICE a
lightweight but meaningful session context history.

Usage (call at on_disconnect in agent.py):

    from session_summarizer import SessionSummarizer

    summarizer = SessionSummarizer(user_id="nspira", mem0_api_key=MEM0_KEY, google_api_key=GOOGLE_KEY)
    await summarizer.summarize_and_save(conversation_turns)
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    from mem0 import MemoryClient
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False


GEMINI_FLASH_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

SUMMARY_PROMPT = """You are a memory summarizer for an AI assistant called ALICE.
Analyze this conversation transcript and produce a concise structured summary that will help ALICE remember important context in future conversations.

Format your response as JSON ONLY:
{
  "key_facts": ["fact1", "fact2"],
  "tasks_discussed": ["task1", "task2"],
  "apps_used": ["app1", "app2"],
  "user_preferences": ["preference1"],
  "open_threads": ["unfinished topic 1"]
}

Rules:
- Keep each item under 15 words
- Only include items that are genuinely useful for future context
- Maximum 5 items per category
- If a category has nothing relevant, use an empty list

Transcript:
{transcript}"""


class SessionSummarizer:
    """
    Summarizes completed ALICE sessions and persists them to Mem0.
    """

    def __init__(
        self,
        user_id: str,
        mem0_api_key: Optional[str] = None,
        google_api_key: Optional[str] = None,
    ):
        self.user_id        = user_id
        self.mem0_api_key   = mem0_api_key   or os.getenv("MEM0_API_KEY", "")
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY", "")

    # ── Main entry point ──────────────────────────────────────────────────────

    async def summarize_and_save(self, conversation_turns: List[Dict]) -> bool:
        """
        Summarize a completed session and save to Mem0.

        Args:
            conversation_turns: List of {"role": "user"|"assistant", "content": "..."}

        Returns:
            True if summary was successfully saved.
        """
        if not conversation_turns:
            logger.info("[SessionSummarizer] No turns to summarize — skipping")
            return False

        # Build a readable transcript
        transcript = self._format_transcript(conversation_turns)

        # Generate summary via Gemini
        summary = await self._generate_summary(transcript)
        if not summary:
            logger.warning("[SessionSummarizer] Failed to generate summary — skipping Mem0 save")
            return False

        # Persist to Mem0
        saved = await self._save_to_mem0(summary, len(conversation_turns))
        return saved

    # ── Transcript formatter ──────────────────────────────────────────────────

    @staticmethod
    def _format_transcript(turns: List[Dict]) -> str:
        lines = []
        for t in turns:
            role    = t.get("role", "unknown").upper()
            content = t.get("content", "").strip()
            if content:
                lines.append(f"{role}: {content}")
        return "\n".join(lines[-60:])   # last 60 turns max to keep prompt small

    # ── Gemini summary call ───────────────────────────────────────────────────

    async def _generate_summary(self, transcript: str) -> Optional[Dict]:
        if not HTTPX_AVAILABLE:
            logger.error("[SessionSummarizer] httpx not installed")
            return None
        if not self.google_api_key:
            logger.error("[SessionSummarizer] GOOGLE_API_KEY not set")
            return None

        prompt = SUMMARY_PROMPT.replace("{transcript}", transcript)

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 400}
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    GEMINI_FLASH_URL,
                    params={"key": self.google_api_key},
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()

            raw = (
                resp.json()
                .get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )

            # Strip markdown fences
            if raw.startswith("```"):
                raw = raw.split("```")[1].strip()
                if raw.startswith("json"):
                    raw = raw[4:].strip()

            summary = json.loads(raw)
            logger.info(f"[SessionSummarizer] Summary generated: {list(summary.keys())}")
            return summary

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"[SessionSummarizer] Failed to parse summary JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"[SessionSummarizer] Gemini call failed: {e}")
            return None

    # ── Mem0 persistence ──────────────────────────────────────────────────────

    async def _save_to_mem0(self, summary: Dict, turn_count: int) -> bool:
        if not MEM0_AVAILABLE:
            logger.warning("[SessionSummarizer] mem0 not installed — cannot save")
            return False
        if not self.mem0_api_key:
            logger.error("[SessionSummarizer] MEM0_API_KEY not set")
            return False

        try:
            # Build a readable memory string from the structured summary
            parts = []
            for key_facts in summary.get("key_facts", []):
                parts.append(f"Fact: {key_facts}")
            for task in summary.get("tasks_discussed", []):
                parts.append(f"Task discussed: {task}")
            for app in summary.get("apps_used", []):
                parts.append(f"App used: {app}")
            for pref in summary.get("user_preferences", []):
                parts.append(f"User preference: {pref}")
            for thread in summary.get("open_threads", []):
                parts.append(f"Open thread: {thread}")

            if not parts:
                logger.info("[SessionSummarizer] Summary was empty — nothing to save")
                return False

            memory_content = "\n".join(parts)
            session_date   = datetime.now().strftime("%Y-%m-%d %H:%M")

            # Run blocking Mem0 call in executor
            loop = asyncio.get_event_loop()
            client = MemoryClient(api_key=self.mem0_api_key)

            await loop.run_in_executor(
                None,
                lambda: client.add(
                    messages=[{
                        "role": "assistant",
                        "content": f"Session summary ({session_date}):\n{memory_content}"
                    }],
                    user_id=self.user_id,
                    metadata={
                        "type": "session_summary",
                        "date": session_date,
                        "turn_count": turn_count,
                        "categories": list(summary.keys()),
                    }
                )
            )

            logger.info(f"[SessionSummarizer] ✅ Session summary saved to Mem0 for user '{self.user_id}'")
            return True

        except Exception as e:
            logger.error(f"[SessionSummarizer] Mem0 save failed: {e}")
            return False


# Fix missing Optional import
from typing import Optional
