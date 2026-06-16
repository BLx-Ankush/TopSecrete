"""
Secure tool-execution gate (Layer 1) for ALICE.
================================================
ALICE's LLM (Gemini Live) can call Python tools that take real OS actions. The
streaming client used to execute those calls directly:

    target_func(**args)          # no validation, no approval, no audit

That means a prompt-injection payload hidden in a web page, email, or document
that ALICE reads could make the model call a destructive tool. Production
agents (Gemini, OpenAI, Claude) gate tool execution; this module gives ALICE
the same property.

For every tool call it:
  1. classifies the tool's risk (SAFE / SENSITIVE / DANGEROUS),
  2. validates arguments through the alice_security validators,
  3. for SENSITIVE/DANGEROUS tools, consults the permission manager (verbal
     approval when an ask-callback is available; otherwise a safe default
     policy that never blocks the audio loop),
  4. writes an audit-log line for the decision.

It is intentionally fail-safe and non-blocking: if approval cannot be obtained
in a voice context it denies dangerous actions rather than hanging.
"""

import logging
import os
import time
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Dedicated audit logger — every tool decision is recorded here.
_audit_logger = logging.getLogger("alice.audit")
if not _audit_logger.handlers:
    try:
        _handler = logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "alice_tool_audit.log"),
            encoding="utf-8",
        )
        _handler.setFormatter(
            logging.Formatter("%(asctime)s | %(message)s")
        )
        _audit_logger.addHandler(_handler)
        _audit_logger.setLevel(logging.INFO)
        _audit_logger.propagate = False
    except Exception:  # pragma: no cover - never let logging setup break tools
        pass


class RiskLevel(str, Enum):
    SAFE = "safe"           # read-only / informational; run freely
    SENSITIVE = "sensitive" # takes a real action; approve (ask or policy)
    DANGEROUS = "dangerous" # destructive / system-altering; always gated


# ──────────────────────────────────────────────────────────────────────────
# Tool risk classification.
#
# Keys are tool names as registered with Gemini (see tool_registry.py). Tools
# not listed default to SENSITIVE — unknown actions are treated cautiously, not
# waved through.
# ──────────────────────────────────────────────────────────────────────────
TOOL_RISK: Dict[str, RiskLevel] = {
    # ── SAFE: read-only / informational ──────────────────────────────────
    "get_weather": RiskLevel.SAFE,
    "duckduckgo_search": RiskLevel.SAFE,
    "google_search": RiskLevel.SAFE,
    "capture_screenshot": RiskLevel.SAFE,        # reads the screen, no mutation
    "get_ultrasonic_distance": RiskLevel.SAFE,   # sensor read
    "check_personal_mode": RiskLevel.SAFE,
    "show_available_apps": RiskLevel.SAFE,
    "whatsapp_automation_help": RiskLevel.SAFE,
    "search_files_system": RiskLevel.SAFE,       # pure-Python read-only walk

    # ── SENSITIVE: real action, low blast radius ─────────────────────────
    "open_application": RiskLevel.SENSITIVE,
    "open_any_app": RiskLevel.SENSITIVE,
    "open_browser": RiskLevel.SENSITIVE,
    "open_vscode_new_window": RiskLevel.SENSITIVE,
    "create_file_and_open": RiskLevel.SENSITIVE,
    "create_and_research": RiskLevel.SENSITIVE,
    "perform_multi_app_task": RiskLevel.SENSITIVE,
    "semantic_click": RiskLevel.SENSITIVE,
    "semantic_type_into": RiskLevel.SENSITIVE,
    "send_whatsapp_message": RiskLevel.SENSITIVE,
    "open_whatsapp_chat": RiskLevel.SENSITIVE,
    "adjust_brightness": RiskLevel.SENSITIVE,
    "control_servo_motor": RiskLevel.SENSITIVE,    # moves physical hardware
    "enable_personal_mode": RiskLevel.SENSITIVE,
    "refresh_app_database_tool": RiskLevel.SENSITIVE,

    # ── DANGEROUS: destructive / broad system control ────────────────────
    "advanced_system_operations": RiskLevel.DANGEROUS,
    "disable_personal_mode": RiskLevel.SENSITIVE,
}

DEFAULT_RISK = RiskLevel.SENSITIVE

# Which argument names, per validator, to check when present. The validators
# raise SecurityValidationError on bad input.
#
# NOTE on `filename`: across ALICE's tools it always denotes a file PATH
# (create_file_and_open, capture_screenshot, create_and_research), never a
# loose search term — so it is validated as a path. Search tools use `query`.
_ARG_VALIDATORS = {
    "app_name": "app_name",
    "app": "app_name",
    "app_title": "app_name",
    "browser": "app_name",
    "url": "url",
    "folder_path": "path",
    "file_path": "path",
    "path": "path",
    "location": "path",
    "filename": "path",
    "query": "search_query",
}

# An async callable that speaks a yes/no question and returns the user's answer.
AskCallback = Callable[[str], Awaitable[bool]]


class SecureDispatcher:
    """
    Wraps tool execution with validation + approval + audit.

    Usage (from gemini_streaming_client):
        dispatcher = SecureDispatcher(ask_callback=session_reply_yes_no)
        allowed, reason = await dispatcher.authorize(name, args)
        if allowed:
            result = await run_tool(...)
        else:
            return {"error": reason}
    """

    def __init__(
        self,
        ask_callback: Optional[AskCallback] = None,
        *,
        # When no ask_callback is available (e.g. headless), how to treat each
        # level. Defaults: safe→run, sensitive→run (audited), dangerous→deny.
        allow_sensitive_without_ask: bool = True,
        allow_dangerous_without_ask: bool = False,
    ):
        self.ask_callback = ask_callback
        self.allow_sensitive_without_ask = allow_sensitive_without_ask
        self.allow_dangerous_without_ask = allow_dangerous_without_ask

    def classify(self, tool_name: str) -> RiskLevel:
        return TOOL_RISK.get(tool_name, DEFAULT_RISK)

    def validate_args(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        """
        Validate known argument types. Returns an error string if any argument
        is rejected, else None. Import is local so the dispatcher stays usable
        even if the security package is mid-reload.
        """
        from alice_security import (
            SecurityValidationError,
            validate_app_name,
            validate_path,
            validate_url,
            validate_search_query,
        )
        validator_map = {
            "app_name": validate_app_name,
            "url": validate_url,
            "path": lambda v: validate_path(v, must_exist=False),
            "search_query": validate_search_query,
        }
        for arg_name, value in (args or {}).items():
            kind = _ARG_VALIDATORS.get(arg_name)
            if not kind or value in (None, ""):
                continue
            if not isinstance(value, str):
                continue
            try:
                validator_map[kind](value)
            except SecurityValidationError as e:
                return f"Argument '{arg_name}' rejected: {e}"
        return None

    async def authorize(
        self, tool_name: str, args: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Decide whether `tool_name(**args)` may execute.

        Returns (allowed, reason). `reason` is safe to surface to the user/LLM.
        """
        risk = self.classify(tool_name)

        # 1) Argument validation applies at every level — this is the
        #    defense-in-depth backstop behind the per-tool safe_exec layer.
        arg_error = self.validate_args(tool_name, args)
        if arg_error:
            self._audit(tool_name, risk, "DENIED", arg_error, args)
            return False, f"I can't do that — {arg_error}"

        # 2) SAFE tools run freely.
        if risk == RiskLevel.SAFE:
            self._audit(tool_name, risk, "ALLOWED", "safe tool", args)
            return True, "ok"

        # 3) SENSITIVE / DANGEROUS — seek approval.
        if self.ask_callback is not None:
            granted, reason = await self._ask_permission(tool_name, risk, args)
            decision = "ALLOWED" if granted else "DENIED"
            self._audit(tool_name, risk, decision, reason, args)
            return granted, reason

        # 4) No interactive approval channel — fall back to policy.
        if risk == RiskLevel.SENSITIVE and self.allow_sensitive_without_ask:
            self._audit(tool_name, risk, "ALLOWED", "policy: sensitive auto-allow", args)
            return True, "ok"
        if risk == RiskLevel.DANGEROUS and self.allow_dangerous_without_ask:
            self._audit(tool_name, risk, "ALLOWED", "policy: dangerous auto-allow", args)
            return True, "ok"

        reason = (
            f"The action '{tool_name}' needs your confirmation, but I don't have "
            f"a way to ask right now, so I'm holding off for safety."
        )
        self._audit(tool_name, risk, "DENIED", "no ask channel; default-deny", args)
        return False, reason

    async def _ask_permission(
        self, tool_name: str, risk: RiskLevel, args: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Route the approval through the existing PermissionManager when a path
        is involved; otherwise ask a direct yes/no via the callback."""
        # If a path-like argument exists, reuse the manifest-backed tier system.
        path_arg = next(
            (args[a] for a in ("file_path", "folder_path", "path", "location")
             if isinstance(args.get(a), str) and args.get(a)),
            None,
        )
        try:
            if path_arg:
                from permission_manager import get_permission_manager
                pm = get_permission_manager()
                result = await pm.request_access(
                    path=path_arg,
                    operation=tool_name,
                    ask_callback=self.ask_callback,
                )
                return result.granted, result.reason

            # No path: ask a concise yes/no scoped to the action.
            summary = self._summarize(tool_name, args)
            verb = "potentially destructive" if risk == RiskLevel.DANGEROUS else "this"
            question = (
                f"You're asking me to run {verb} action: {summary}. "
                f"Should I go ahead?"
            )
            granted = await self.ask_callback(question)  # type: ignore[misc]
            return bool(granted), (
                "User approved" if granted else "User declined"
            )
        except Exception as e:  # never let approval crash the tool loop
            logger.error(f"[secure_dispatch] approval error for {tool_name}: {e}")
            # Fail safe: deny dangerous, allow sensitive (already validated).
            if risk == RiskLevel.DANGEROUS:
                return False, "Could not confirm — holding off for safety."
            return True, "approval channel error; sensitive action allowed after validation"

    @staticmethod
    def _summarize(tool_name: str, args: Dict[str, Any]) -> str:
        if not args:
            return tool_name
        shown = ", ".join(f"{k}={str(v)[:40]}" for k, v in list(args.items())[:3])
        return f"{tool_name}({shown})"

    @staticmethod
    def _audit(
        tool_name: str,
        risk: RiskLevel,
        decision: str,
        reason: str,
        args: Dict[str, Any],
    ) -> None:
        try:
            preview = SecureDispatcher._summarize(tool_name, args)
            _audit_logger.info(
                f"{decision} | {risk.value} | {preview} | {reason}"
            )
        except Exception:
            pass
