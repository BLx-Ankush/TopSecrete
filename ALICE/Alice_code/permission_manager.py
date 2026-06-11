"""
Permission Manager — Phase 4 v2.0
===================================
The brain behind ALICE's Conversational Security System.

Instead of failing silently or returning a cold error, ALICE:
  1. Detects the permission tier of any path she is asked to access
  2. For unknown paths → pauses and verbally asks the user for approval
  3. Tracks access frequency per path across sessions
  4. Auto-suggests making frequently-accessed paths permanent ("always_allowed")
  5. Writes approved paths directly into security_manifest.json — no manual editing needed

Tier System:
  ┌─────────────────────┬────────────────────────────────────────────────┐
  │ always_allowed      │ ALICE proceeds silently. No confirmation ever. │
  │ ask_each_time       │ ALICE asks verbally on every session access.    │
  │ never_allowed       │ Hard-blocked. Even ALICE's requests can't fix.  │
  │ unknown (new path)  │ ALICE asks, then writes to manifest if approved.│
  └─────────────────────┴────────────────────────────────────────────────┘

Usage:
    from permission_manager import get_permission_manager, PermissionResult

    pm = get_permission_manager()
    result = await pm.request_access(
        path="E:/Projects/MyApp",
        operation="read_file",
        ask_callback=session.generate_reply   # async fn that speaks to the user
    )
    if result.granted:
        # proceed with operation
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Awaitable, Callable, Dict, Optional

logger = logging.getLogger(__name__)

MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "security_manifest.json")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Tier(str, Enum):
    ALWAYS   = "always_allowed"
    ASK      = "ask_each_time"
    NEVER    = "never_allowed"
    UNKNOWN  = "unknown"


@dataclass
class PermissionResult:
    granted: bool
    tier: Tier
    reason: str
    # If this approval triggered a manifest write, what was written?
    written_to_manifest: bool = False
    promoted_to_permanent: bool = False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Ask Callback Type
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# The callback ALICE uses to ask the user a yes/no question verbally.
# It must be an async function that:
#   1. Speaks `question_text` to the user
#   2. Listens for a response
#   3. Returns True if the user said yes/confirm/okay, False otherwise
AskCallback = Callable[[str], Awaitable[bool]]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Permission Manager
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PermissionManager:
    """
    ALICE's conversational permission system.
    Manages the security_manifest.json lifecycle entirely through dialogue.
    """

    def __init__(self, manifest_path: str = MANIFEST_PATH):
        self._manifest_path = manifest_path
        self._manifest: dict = {}
        self._reload()

    # ── Manifest I/O ──────────────────────────────────────────────────────────

    def _reload(self):
        """Load the manifest from disk into memory."""
        try:
            with open(self._manifest_path, encoding="utf-8") as f:
                self._manifest = json.load(f)
            logger.debug("[PermissionManager] Manifest loaded")
        except FileNotFoundError:
            logger.warning("[PermissionManager] Manifest not found — using empty defaults")
            self._manifest = self._default_manifest()
        except json.JSONDecodeError as e:
            logger.error(f"[PermissionManager] Manifest JSON error: {e}")
            self._manifest = self._default_manifest()

    def _save(self):
        """Write the in-memory manifest back to disk (atomic write)."""
        tmp_path = self._manifest_path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._manifest, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self._manifest_path)
            logger.info("[PermissionManager] Manifest saved to disk")
        except Exception as e:
            logger.error(f"[PermissionManager] Failed to save manifest: {e}")

    def _default_manifest(self) -> dict:
        return {
            "version": "2.0",
            "tiers": {
                "always_allowed": [],
                "ask_each_time": [],
                "never_allowed": [
                    "C:\\Windows\\System32",
                    "C:\\Windows\\SysWOW64"
                ]
            },
            "allowed_executables": [],
            "require_confirmation_for": ["delete_file", "write_file", "shutdown", "restart"],
            "access_history": {"paths": {}},
            "settings": {
                "strict_mode": False,
                "log_all_checks": True,
                "auto_deny_outside_manifest": False,
                "confirmation_timeout_seconds": 15,
                "auto_suggest_after_accesses": 3,
                "onboarding_complete": False
            }
        }

    # ── Tier Resolution ───────────────────────────────────────────────────────

    def _resolve_tier(self, path: str) -> Tier:
        """
        Determine which permission tier a path falls into.
        Checks from most restrictive to most permissive.
        """
        norm = str(Path(path).resolve()).upper()
        tiers = self._manifest.get("tiers", {})

        def _in_list(key: str) -> bool:
            return any(
                norm.startswith(str(Path(p).resolve()).upper())
                for p in tiers.get(key, [])
            )

        if _in_list("never_allowed"):
            return Tier.NEVER
        if _in_list("always_allowed"):
            return Tier.ALWAYS
        if _in_list("ask_each_time"):
            return Tier.ASK
        return Tier.UNKNOWN

    # ── Access History Tracking ───────────────────────────────────────────────

    def _record_access(self, path: str) -> int:
        """
        Increment the access count for this path and return the new count.
        Persists to disk after each increment.
        """
        norm = str(Path(path).resolve())
        history = self._manifest.setdefault("access_history", {}).setdefault("paths", {})
        count = history.get(norm, 0) + 1
        history[norm] = count
        self._manifest["access_history"]["paths"] = history
        self._save()
        return count

    def _get_access_count(self, path: str) -> int:
        norm = str(Path(path).resolve())
        return self._manifest.get("access_history", {}).get("paths", {}).get(norm, 0)

    # ── Manifest Writers ──────────────────────────────────────────────────────

    def _add_to_tier(self, path: str, tier: Tier):
        """
        Add a path to a specific tier in the manifest and save.
        If it exists in another tier, removes it there first.
        """
        norm_path = str(Path(path).resolve())
        tiers = self._manifest.setdefault("tiers", {})

        # Remove from all other tiers to avoid conflicts
        for tier_key in ["always_allowed", "ask_each_time", "never_allowed"]:
            bucket: list = tiers.setdefault(tier_key, [])
            tiers[tier_key] = [p for p in bucket if str(Path(p).resolve()) != norm_path]

        # Add to the target tier
        tiers.setdefault(tier.value, []).append(norm_path)
        self._save()
        logger.info(f"[PermissionManager] Added '{norm_path}' to tier '{tier.value}'")

    # ── Core Public API ───────────────────────────────────────────────────────

    async def request_access(
        self,
        path: str,
        operation: str = "access",
        ask_callback: Optional[AskCallback] = None,
    ) -> PermissionResult:
        """
        The single entry point for all permission checks.

        Flow:
          1. Resolve the path's tier
          2. ALWAYS  → grant immediately, track access, maybe suggest promotion
          3. NEVER   → deny immediately with an explanation
          4. ASK     → verbally ask, grant for this session only
          5. UNKNOWN → verbally ask, if granted write to ask_each_time,
                       if access count >= threshold also offer always_allowed

        Args:
            path:          The file/directory path being requested.
            operation:     Human-readable operation name ('read_file', 'delete_file', etc.)
            ask_callback:  Async fn(question: str) -> bool that speaks to the user.
                           If None, falls back to non-interactive deny for unknown paths.
        """
        self._reload()
        tier = self._resolve_tier(path)
        short_path = Path(path).name or path

        # ── Tier: NEVER ───────────────────────────────────────────────────────
        if tier == Tier.NEVER:
            msg = (
                f"I cannot access '{short_path}'. "
                f"This path is in your permanent no-access list. "
                f"It's there for your security and I won't override it."
            )
            logger.warning(f"[PermissionManager] HARD BLOCKED | {operation} | {path}")
            return PermissionResult(granted=False, tier=tier, reason=msg)

        # ── Tier: ALWAYS ──────────────────────────────────────────────────────
        if tier == Tier.ALWAYS:
            count = self._record_access(path)
            logger.info(f"[PermissionManager] ALWAYS ALLOWED | {operation} | {path} (access #{count})")
            return PermissionResult(granted=True, tier=tier, reason="Path is in always_allowed tier")

        # ── Tier: ASK or UNKNOWN — need verbal confirmation ───────────────────
        if ask_callback is None:
            # No interactive session — default to deny for unknown paths
            msg = (
                f"I don't have permission to access '{path}'. "
                f"No confirmation mechanism is available in this context."
            )
            return PermissionResult(granted=False, tier=tier, reason=msg)

        # Build the verbal question
        if tier == Tier.ASK:
            question = (
                f"I need access to '{path}' to {operation}. "
                f"This is marked as 'ask each time'. Do you want me to proceed?"
            )
        else:  # UNKNOWN
            question = (
                f"I'd like to access '{path}' for {operation}, "
                f"but that path isn't in my permission list yet. "
                f"Should I go ahead? I'll remember your answer for this session."
            )

        # Ask the user verbally
        granted = await self._ask_with_timeout(ask_callback, question)

        if not granted:
            return PermissionResult(
                granted=False, tier=tier,
                reason=f"User denied access to '{path}' for {operation}"
            )

        # ── User said YES ─────────────────────────────────────────────────────
        written = False
        promoted = False

        if tier == Tier.UNKNOWN:
            # Write to ask_each_time so next access in this session doesn't ask again
            self._add_to_tier(path, Tier.ASK)
            written = True
            logger.info(f"[PermissionManager] Approved '{path}' → written to ask_each_time")

        # Track access count and check if we should suggest permanent promotion
        count = self._record_access(path)
        threshold = self._manifest.get("settings", {}).get("auto_suggest_after_accesses", 3)

        if count >= threshold and tier in (Tier.ASK, Tier.UNKNOWN):
            suggestion = (
                f"You've accessed '{path}' {count} times now. "
                f"Would you like me to add it to your always-allowed list "
                f"so you don't have to confirm every time?"
            )
            promote = await self._ask_with_timeout(ask_callback, suggestion)
            if promote:
                self._add_to_tier(path, Tier.ALWAYS)
                promoted = True
                logger.info(f"[PermissionManager] Promoted '{path}' to always_allowed (accessed {count}x)")

        return PermissionResult(
            granted=True, tier=tier, reason=f"User verbally approved {operation} on '{path}'",
            written_to_manifest=written, promoted_to_permanent=promoted
        )

    async def _ask_with_timeout(self, ask_callback: AskCallback, question: str) -> bool:
        """
        Call the ask_callback with a timeout. Returns False on timeout/error.
        """
        timeout = self._manifest.get("settings", {}).get("confirmation_timeout_seconds", 15)
        try:
            result = await asyncio.wait_for(ask_callback(question), timeout=float(timeout))
            return bool(result)
        except asyncio.TimeoutError:
            logger.warning(f"[PermissionManager] User didn't respond to permission request in {timeout}s — denying")
            return False
        except Exception as e:
            logger.error(f"[PermissionManager] ask_callback error: {e}")
            return False

    # ── High-Risk Operations ──────────────────────────────────────────────────

    async def confirm_high_risk(
        self,
        operation: str,
        description: str,
        ask_callback: Optional[AskCallback] = None,
    ) -> bool:
        """
        Ask the user to confirm a high-risk operation (delete, shutdown, etc.)
        regardless of path tier.
        """
        confirm_ops = [op.lower() for op in self._manifest.get("require_confirmation_for", [])]
        if operation.lower() not in confirm_ops:
            return True  # Not a high-risk operation, proceed silently

        if ask_callback is None:
            logger.warning(f"[PermissionManager] High-risk op '{operation}' has no confirmation channel — denying")
            return False

        question = (
            f"This is a high-risk action: {description}. "
            f"Are you sure you want me to proceed?"
        )
        return await self._ask_with_timeout(ask_callback, question)

    # ── Utility: Add a path conversationally ─────────────────────────────────

    def grant_permanent(self, path: str) -> bool:
        """Directly grant always_allowed without asking (used by onboarding wizard)."""
        try:
            self._add_to_tier(path, Tier.ALWAYS)
            return True
        except Exception as e:
            logger.error(f"[PermissionManager] grant_permanent failed: {e}")
            return False

    def revoke(self, path: str) -> bool:
        """Remove a path from all tiers."""
        try:
            norm_path = str(Path(path).resolve())
            tiers = self._manifest.setdefault("tiers", {})
            for key in ["always_allowed", "ask_each_time"]:
                tiers[key] = [p for p in tiers.get(key, []) if str(Path(p).resolve()) != norm_path]
            self._save()
            return True
        except Exception as e:
            logger.error(f"[PermissionManager] revoke failed: {e}")
            return False

    def get_summary(self) -> dict:
        """Return a human-readable summary of the current manifest state."""
        tiers = self._manifest.get("tiers", {})
        history = self._manifest.get("access_history", {}).get("paths", {})
        return {
            "always_allowed": tiers.get("always_allowed", []),
            "ask_each_time": tiers.get("ask_each_time", []),
            "never_allowed": tiers.get("never_allowed", []),
            "total_paths_tracked": len(history),
            "most_accessed": sorted(history.items(), key=lambda x: x[1], reverse=True)[:5]
        }

    # ── Onboarding helpers ────────────────────────────────────────────────────

    def mark_onboarding_complete(self):
        self._manifest.setdefault("settings", {})["onboarding_complete"] = True
        self._save()

    def is_onboarding_needed(self) -> bool:
        return not self._manifest.get("settings", {}).get("onboarding_complete", False)


# ── Singleton ─────────────────────────────────────────────────────────────────
_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    global _manager
    if _manager is None:
        _manager = PermissionManager()
    return _manager
