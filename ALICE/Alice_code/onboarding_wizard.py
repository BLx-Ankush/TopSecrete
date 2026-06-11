"""
ALICE Onboarding Wizard — Phase 4
===================================
Runs once on first launch. Walks the user through populating their
security_manifest.json through a natural voice conversation, so the manifest
is already populated before any task-based friction can occur.

Flow:
  1. Detect if onboarding has been completed (manifest settings.onboarding_complete)
  2. If needed, greet the user and explain the permission concept
  3. Ask about common locations: project folders, external drives, work directories
  4. For each path the user mentions, call grant_permanent()
  5. Ask about any apps/executables to add
  6. Mark onboarding complete
  7. Summarize what was set up

Integration in agent.py:
    from onboarding_wizard import maybe_run_onboarding
    await maybe_run_onboarding(session_ask_callback=my_ask_fn, speak_fn=session.generate_reply)
"""

import logging
import os
import re
from pathlib import Path
from typing import Awaitable, Callable, List, Optional

from permission_manager import get_permission_manager

logger = logging.getLogger(__name__)

# Type aliases
AskFn    = Callable[[str], Awaitable[bool]]    # returns True/False (yes/no)
SpeakFn  = Callable[[str], Awaitable[None]]    # just speaks, no reply expected
ListenFn = Callable[[], Awaitable[str]]        # listens and returns raw transcript


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Wizard
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class OnboardingWizard:
    """
    Guides the user through setting up ALICE's permission manifest the first time.

    All interaction goes through three callbacks:
      speak_fn    — ALICE says something (no user response expected)
      ask_fn      — ALICE asks a yes/no question, waits for answer
      listen_fn   — ALICE listens for a free-form path/app name from the user
    """

    # Common locations to ask about
    COMMON_PATHS = [
        ("your main Projects or code folder", None),
        ("an external hard drive", None),
        ("a work or university directory", None),
        ("a OneDrive or cloud sync folder", None),
    ]

    COMMON_APPS = [
        "Photoshop", "Illustrator", "Premiere", "After Effects",
        "OBS", "Blender", "Unity", "Unreal Engine",
        "VS Code", "PyCharm", "IntelliJ",
        "Slack", "Zoom", "Telegram"
    ]

    def __init__(
        self,
        speak_fn: SpeakFn,
        ask_fn: AskFn,
        listen_fn: ListenFn,
    ):
        self._speak  = speak_fn
        self._ask    = ask_fn
        self._listen = listen_fn
        self._pm     = get_permission_manager()

    # ── Entry point ───────────────────────────────────────────────────────────

    async def run(self) -> List[str]:
        """
        Run the full onboarding flow.
        Returns the list of paths that were added to always_allowed.
        """
        granted_paths: List[str] = []

        await self._speak(
            "Hi! This is your first time setting me up, so let me take a minute to get your permissions sorted. "
            "I work best when I know which folders I'm allowed to touch. "
            "Don't worry, I'll ask you for everything, and you're always in control."
        )

        # ── Step 1: Common known folders ──────────────────────────────────────
        await self._speak(
            "Let me start by checking if you want me to have access to some common locations."
        )

        for label, default_path in self.COMMON_PATHS:
            try:
                wants = await self._ask(
                    f"Do you have {label} that you'd like me to access freely?"
                )
                if wants:
                    await self._speak(f"Great. What's the full path to {label}?")
                    raw_path = await self._listen()
                    norm = self._extract_path(raw_path)
                    if norm and os.path.exists(norm):
                        self._pm.grant_permanent(norm)
                        granted_paths.append(norm)
                        await self._speak(
                            f"Perfect. I've added '{norm}' to my always-allowed list. "
                            f"I can access it freely from now on."
                        )
                    elif norm:
                        await self._speak(
                            f"I couldn't find that path right now, but I've noted it. "
                            f"You can ask me to add it again later."
                        )
            except Exception as e:
                logger.warning(f"[OnboardingWizard] Error on step '{label}': {e}")
                continue

        # ── Step 2: User's own common locations from system ───────────────────
        try:
            user_home = str(Path.home())
            common_dirs = [
                os.path.join(user_home, "Documents"),
                os.path.join(user_home, "Desktop"),
                os.path.join(user_home, "Downloads"),
            ]
            existing_always = self._pm._manifest.get("tiers", {}).get("always_allowed", [])

            for d in common_dirs:
                if os.path.exists(d) and not any(
                    str(Path(d).resolve()) == str(Path(p).resolve())
                    for p in existing_always
                ):
                    wants = await self._ask(
                        f"Do you want me to always have access to your {Path(d).name} folder at '{d}'?"
                    )
                    if wants:
                        self._pm.grant_permanent(d)
                        granted_paths.append(d)
        except Exception as e:
            logger.warning(f"[OnboardingWizard] Common dirs step failed: {e}")

        # ── Step 3: Ask about external drives ─────────────────────────────────
        try:
            external = await self._ask(
                "Do you have any external hard drives or USB drives that I should have access to?"
            )
            if external:
                await self._speak("Tell me the drive letter or path, like 'E drive' or 'F colon backslash'.")
                raw = await self._listen()
                norm = self._extract_path(raw)
                if norm:
                    self._pm.grant_permanent(norm)
                    granted_paths.append(norm)
                    await self._speak(f"Added '{norm}' to my access list.")
        except Exception as e:
            logger.warning(f"[OnboardingWizard] External drive step failed: {e}")

        # ── Step 4: Apps ──────────────────────────────────────────────────────
        try:
            more_apps = await self._ask(
                "Are there any applications beyond the defaults — like Blender, Photoshop, or OBS — "
                "that you'd like me to be able to launch?"
            )
            if more_apps:
                await self._speak("Just say the app names and I'll note them down.")
                raw_apps = await self._listen()
                for app in self.COMMON_APPS:
                    if app.lower() in raw_apps.lower():
                        self._add_executable(app.lower().replace(" ", "") + ".exe")
                        await self._speak(f"Added {app}.")
        except Exception as e:
            logger.warning(f"[OnboardingWizard] Apps step failed: {e}")

        # ── Step 5: Summary & completion ─────────────────────────────────────
        self._pm.mark_onboarding_complete()

        if granted_paths:
            path_list = ", ".join(Path(p).name for p in granted_paths[:5])
            await self._speak(
                f"All set! I've added {len(granted_paths)} location{'s' if len(granted_paths) > 1 else ''} "
                f"to my always-allowed list: {path_list}. "
                f"If you ever need to change anything, just tell me and I'll update my permissions right away. "
                f"Let's get started!"
            )
        else:
            await self._speak(
                "No problem! I'll ask you each time I need access to a new location, "
                "and I'll remember your answer. Let's get started!"
            )

        logger.info(f"[OnboardingWizard] Complete. {len(granted_paths)} paths granted: {granted_paths}")
        return granted_paths

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_path(self, raw: str) -> Optional[str]:
        """
        Try to extract a file-system path from a raw transcript string.
        Handles:
          - 'D drive' / 'E colon backslash'
          - 'D:/Projects/MyApp'
          - 'C:\\Users\\NSPIRA\\Documents'
        """
        if not raw:
            return None
        raw = raw.strip()

        # Direct path-like strings
        path_match = re.search(r"([A-Za-z]:[/\\][^\s,;]*)", raw)
        if path_match:
            candidate = path_match.group(1).replace("/", os.sep).replace("\\", os.sep)
            return candidate

        # Spoken drive letters: "D drive", "E colon"
        drive_match = re.search(r"\b([A-Fa-f])\s*(drive|colon|:)", raw, re.IGNORECASE)
        if drive_match:
            letter = drive_match.group(1).upper()
            return f"{letter}:\\"

        return None

    def _add_executable(self, exe_name: str):
        """Add an executable to the manifest's allowed_executables list."""
        exes: list = self._pm._manifest.setdefault("allowed_executables", [])
        if exe_name.lower() not in [e.lower() for e in exes]:
            exes.append(exe_name)
            self._pm._save()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience entry point for agent.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def maybe_run_onboarding(
    speak_fn: SpeakFn,
    ask_fn: AskFn,
    listen_fn: ListenFn,
) -> bool:
    """
    Run the onboarding wizard only if it hasn't been completed yet.
    Call this once near the beginning of the agent session.

    Returns True if the wizard ran, False if onboarding was already done.

    Example usage in agent.py entrypoint:

        from onboarding_wizard import maybe_run_onboarding

        async def _speak(text: str):
            await session.generate_reply(instructions=text)

        async def _ask(question: str) -> bool:
            await session.generate_reply(instructions=question)
            # Wait for user voice response
            return True  # integrate with your response listener

        async def _listen() -> str:
            # Return the next user utterance
            return ""

        await maybe_run_onboarding(speak_fn=_speak, ask_fn=_ask, listen_fn=_listen)
    """
    pm = get_permission_manager()
    if not pm.is_onboarding_needed():
        logger.info("[Onboarding] Already complete — skipping wizard")
        return False

    logger.info("[Onboarding] First run detected — starting wizard")
    wizard = OnboardingWizard(speak_fn=speak_fn, ask_fn=ask_fn, listen_fn=listen_fn)
    await wizard.run()
    return True
