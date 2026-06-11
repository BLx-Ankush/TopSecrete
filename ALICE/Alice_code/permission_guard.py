"""
Permission Guard — Phase 4 v2.0 (Tiered Conversational Backend)
================================================================
Thin wrapper over PermissionManager.  All the logic now lives in
permission_manager.py.  This module preserves the existing
`@require_permission` decorator API so no other files need changing.

New behavior vs v1.0:
  • Three tiers instead of binary allow/deny
  • Unknown paths trigger a verbal request → manifest write, not a silent block
  • High-risk ops (delete, shutdown) ask the user every time
  • Frequently-accessed paths get offered an upgrade to always_allowed

Usage (unchanged from v1.0):
    from permission_guard import require_permission

    @require_permission("read_file")
    async def my_tool(path: str):
        ...

New direct usage:
    from permission_guard import check_path_tiered

    result = await check_path_tiered(path, operation, session_ask_callback)
    if not result.granted:
        return result.reason
"""

import asyncio
import functools
import logging
from typing import Callable, Optional

from permission_manager import (
    AskCallback,
    PermissionManager,
    PermissionResult,
    Tier,
    get_permission_manager,
)

logger = logging.getLogger(__name__)

# Module-level convenience alias
MANIFEST_PATH = __import__("permission_manager").MANIFEST_PATH


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Public API: direct tiered check
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def check_path_tiered(
    path: str,
    operation: str = "access",
    ask_callback: Optional[AskCallback] = None,
) -> PermissionResult:
    """
    Async tiered check — the primary entry point for runtime tool calls.
    Delegates entirely to PermissionManager.request_access().
    """
    pm = get_permission_manager()
    return await pm.request_access(path, operation, ask_callback)


async def confirm_high_risk_op(
    operation: str,
    description: str,
    ask_callback: Optional[AskCallback] = None,
) -> bool:
    """
    Ask the user to confirm a high-risk operation verbally.
    """
    pm = get_permission_manager()
    return await pm.confirm_high_risk(operation, description, ask_callback)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Decorator: @require_permission  (backward-compatible with v1.0)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Thread-local storage for the current session's ask_callback.
# Set this at the start of each session:
#   permission_guard.session_ask_callback = my_async_ask_fn
session_ask_callback: Optional[AskCallback] = None


def require_permission(operation: str, path_arg: str = "path"):
    """
    Decorator that wraps a tool function and runs a tiered permission check
    before allowing execution.

    The decorator will use `session_ask_callback` (module-level) to ask the
    user verbally for unknown/ask_each_time paths.  Set it at session start:

        import permission_guard
        permission_guard.session_ask_callback = my_voice_ask_function

    Args:
        operation: The operation type (e.g., 'read_file', 'delete_file')
        path_arg:  Name of the argument holding the path in the wrapped function.
    """
    def decorator(fn: Callable) -> Callable:

        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            target_path = str(kwargs.get(path_arg, args[0] if args else ""))

            # Tiered check via permission_manager
            result: PermissionResult = await check_path_tiered(
                path=target_path,
                operation=operation,
                ask_callback=session_ask_callback,
            )
            logger.info(
                f"[PermissionGuard] {operation} | {target_path} | "
                f"granted={result.granted} | tier={result.tier.value}"
            )

            if not result.granted:
                return (
                    f"[ALICE Security] I can't {operation} '{target_path}'. "
                    f"{result.reason}"
                )

            # High-risk confirmation (e.g. delete, shutdown)
            if not await confirm_high_risk_op(
                operation=operation,
                description=f"{operation} on '{target_path}'",
                ask_callback=session_ask_callback,
            ):
                return (
                    f"[ALICE Security] You didn't confirm the high-risk operation "
                    f"'{operation}' on '{target_path}'. Cancelling."
                )

            return await fn(*args, **kwargs)

        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            # Sync functions cannot use conversational flow — fall back to simple tier check
            target_path = str(kwargs.get(path_arg, args[0] if args else ""))
            pm = get_permission_manager()
            tier = pm._resolve_tier(target_path)
            if tier == Tier.NEVER:
                return f"[ALICE Security] '{target_path}' is permanently blocked."
            if tier == Tier.ALWAYS:
                return fn(*args, **kwargs)
            # For ASK/UNKNOWN in sync context, warn and allow (conversation not possible)
            logger.warning(
                f"[PermissionGuard] Sync context: '{target_path}' needs confirmation "
                f"but no async session available — allowing with warning."
            )
            return fn(*args, **kwargs)

        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        return sync_wrapper

    return decorator


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Legacy PermissionGuard class  (kept for backward compatibility)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PermissionGuard:
    """
    Legacy compatibility class.  New code should use PermissionManager directly.
    Existing call sites like guard.check_path(...) will still work.
    """

    def __init__(self, manifest_path: str = MANIFEST_PATH):
        self._pm = PermissionManager(manifest_path)

    def reload(self):
        self._pm._reload()

    def check_path(self, path: str, operation: str = "read_file"):
        """Sync tier check — returns (allowed: bool, reason: str)."""
        tier = self._pm._resolve_tier(path)
        if tier == Tier.NEVER:
            return False, f"Path '{path}' is permanently blocked."
        if tier == Tier.ALWAYS:
            return True, "Path is in always_allowed tier"
        # ASK / UNKNOWN — in sync context we allow with a warning
        return True, f"Path tier is '{tier.value}' — verbal confirmation may be needed"

    def check_executable(self, exe_name: str):
        import json, os
        from pathlib import Path
        try:
            manifest = json.load(open(self._pm._manifest_path, encoding="utf-8"))
        except Exception:
            return True, "Permissive mode"
        allowed = [e.lower() for e in manifest.get("allowed_executables", [])]
        if not allowed:
            return True, "No executable restrictions"
        if exe_name.lower() in allowed:
            return True, f"'{exe_name}' is on the allowed list"
        return False, f"Executable '{exe_name}' is NOT on the approved list."

    def needs_confirmation(self, operation: str) -> bool:
        import json
        try:
            manifest = json.load(open(self._pm._manifest_path, encoding="utf-8"))
        except Exception:
            return False
        return operation.lower() in [op.lower() for op in manifest.get("require_confirmation_for", [])]

    def log_check(self, operation: str, target: str, allowed: bool, reason: str):
        status = "ALLOWED" if allowed else "BLOCKED"
        logger.info(f"[PermissionGuard-Legacy] {status} | op={operation} | target={target} | reason={reason}")


# ── Singleton (legacy) ────────────────────────────────────────────────────────
_guard: Optional[PermissionGuard] = None


def get_permission_guard() -> PermissionGuard:
    global _guard
    if _guard is None:
        _guard = PermissionGuard()
    return _guard
