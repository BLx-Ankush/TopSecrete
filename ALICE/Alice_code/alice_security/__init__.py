"""
ALICE Security Layer
====================
Hardened, injection-proof primitives for executing OS actions on behalf of ALICE.

ALICE is a voice-driven autonomous agent: natural-language (and therefore
attacker-influenceable) input flows from the LLM into real OS actions. This
package is the *single* place where those actions are validated and executed,
so that no user/LLM-derived string is ever interpolated into a shell command
line.

Design rules (do not break):
  1. NEVER build a shell command string from input. No `shell=True` with
     user-derived data. Ever.
  2. Validate first (see `validators`), execute second (see `safe_exec`).
  3. Behaviour-neutral: for legitimate input the observable result is identical
     to the old code. We change *how* we execute, never *what* ALICE can do.

Public API:
    from alice_security import (
        SecurityValidationError,
        validate_app_name, validate_path, validate_url, validate_search_query,
        launch_app, launch_executable, open_path_with, open_url, search_files,
    )
"""

from .errors import SecurityValidationError
from .validators import (
    validate_app_name,
    validate_path,
    validate_url,
    validate_search_query,
    contains_shell_metacharacters,
    SHELL_METACHARACTERS,
)
from .safe_exec import (
    launch_app,
    launch_executable,
    launch_protocol,
    open_path_with,
    open_url,
    search_files,
)

__all__ = [
    "SecurityValidationError",
    "validate_app_name",
    "validate_path",
    "validate_url",
    "validate_search_query",
    "contains_shell_metacharacters",
    "SHELL_METACHARACTERS",
    "launch_app",
    "launch_executable",
    "launch_protocol",
    "open_path_with",
    "open_url",
    "search_files",
]
