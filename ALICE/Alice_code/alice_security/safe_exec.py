"""
Safe execution primitives for ALICE.

Every OS action that used to be done with `subprocess(..., shell=True)` and an
interpolated, user-derived string is replaced by one of these helpers. They:

  - validate input via `validators` first,
  - execute with `shell=False` argument lists (or OS APIs that do not parse a
    shell, like `os.startfile`),
  - are behaviour-neutral for legitimate input.

Why `os.startfile` for app/URL launches on Windows: it calls ShellExecute,
which is exactly what the old `start "" "..."` shell command did (handles
.exe, documents, URL protocols, store apps) — but it takes the target as a
single parameter with NO shell parsing, so command chaining is impossible.
"""

import logging
import os
import subprocess
import sys
import webbrowser
from typing import List, Optional

from .errors import SecurityValidationError
from .validators import (
    validate_app_name,
    validate_path,
    validate_url,
    validate_search_query,
    validate_app_protocol,
)

logger = logging.getLogger(__name__)

_IS_WINDOWS = os.name == "nt"


def _audit(action: str, target: str) -> None:
    """Single chokepoint log line for every OS action we execute."""
    logger.info("[alice_security] %s -> %s", action, target[:200])


# ──────────────────────────────────────────────────────────────────────────
# Application / executable launch
# ──────────────────────────────────────────────────────────────────────────

def launch_app(app_name: str, app_database: Optional[dict] = None) -> str:
    """
    Launch an application by human name, injection-proof.

    Resolution order (all safe):
      1. If `app_database` maps the (lowercased) name to an exe path, launch
         that exact path with `os.startfile` / arg-list — never a shell string.
      2. If the name is an allowlisted protocol launch (e.g. 'whatsapp:'),
         open it via `os.startfile` / webbrowser.
      3. Otherwise hand the *validated* bare name to `os.startfile`, which asks
         the OS shell-association layer to resolve it (same effect as the old
         `start "<name>"`) but without any shell command-line to inject into.

    Returns the resolved target that was launched (for the caller's response).
    Raises SecurityValidationError if the name is malformed/dangerous.
    """
    # A protocol launch like "whatsapp:" is handled before app-name charset
    # validation (the ':' is legitimate here).
    proto = validate_app_protocol(app_name)
    if proto:
        return launch_protocol(app_name)

    name = validate_app_name(app_name)
    key = name.lower()

    if app_database:
        exe_path = app_database.get(key)
        if exe_path and isinstance(exe_path, str) and os.path.exists(exe_path):
            return launch_executable(exe_path)

    # Bare-name launch via OS association. No shell, no interpolation.
    _audit("launch_app(name)", name)
    if _IS_WINDOWS:
        try:
            os.startfile(name)  # type: ignore[attr-defined]
            return name
        except OSError as e:
            raise SecurityValidationError(
                f"Could not launch '{name}': {e}", field="app_name", value=name
            )
    # POSIX fallback (dev/testing): use the desktop opener with an arg list.
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, name], shell=False)
    return name


def launch_executable(exe_path: str) -> str:
    """
    Launch a concrete executable/file path with no shell.

    Uses `os.startfile` on Windows (ShellExecute — handles exes, documents,
    and respects file associations) and an arg-list opener elsewhere.
    """
    path = validate_path(exe_path, must_exist=True)
    _audit("launch_executable", path)
    if _IS_WINDOWS:
        try:
            os.startfile(path)  # type: ignore[attr-defined]
            return path
        except OSError:
            # Fall back to a direct, shell-free spawn for raw executables.
            subprocess.Popen([path], shell=False)
            return path
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, path], shell=False)
    return path


def launch_protocol(protocol_uri: str) -> str:
    """Open an allowlisted protocol URI (whatsapp:, ms-windows-store:, ...) safely."""
    scheme = validate_app_protocol(protocol_uri)
    if not scheme:
        raise SecurityValidationError(
            "Protocol is not allowed.", field="protocol", value=protocol_uri
        )
    _audit("launch_protocol", protocol_uri)
    if _IS_WINDOWS:
        os.startfile(protocol_uri)  # type: ignore[attr-defined]
    else:
        webbrowser.open(protocol_uri)
    return protocol_uri


def open_path_with(opener_exe: str, target_path: str) -> str:
    """
    Open `target_path` using a specific opener executable (e.g. notepad.exe,
    winword.exe), with no shell. `opener_exe` must be a bare program name or a
    validated path; `target_path` is validated as a path.
    """
    # Opener must itself be metacharacter-clean (it is code-chosen, but we keep
    # the boundary strict).
    opener = validate_app_name(os.path.basename(opener_exe)) if opener_exe else ""
    path = validate_path(target_path)
    _audit("open_path_with", f"{opener} {path}")
    # Arg-list spawn: the opener and the path are separate argv entries, so the
    # path can never be parsed as additional commands.
    subprocess.Popen([opener_exe, path], shell=False)
    return path


# ──────────────────────────────────────────────────────────────────────────
# URL / browser
# ──────────────────────────────────────────────────────────────────────────

def open_url(url: str, browser_path: Optional[str] = None) -> str:
    """
    Open a URL in the browser, injection-proof.

    Validates the scheme/characters, then uses `webbrowser` (default) or an
    arg-list spawn of a specific browser binary. Never a shell string.
    """
    safe = validate_url(url)
    _audit("open_url", safe)
    if browser_path and os.path.exists(browser_path):
        subprocess.Popen([browser_path, safe], shell=False)
    else:
        webbrowser.open(safe)
    return safe


# ──────────────────────────────────────────────────────────────────────────
# File search — replaces the `dir "<loc>" /s /b | findstr "<query>"` pipeline
# ──────────────────────────────────────────────────────────────────────────

def search_files(
    query: str,
    location: str,
    *,
    max_results: int = 200,
    case_insensitive: bool = True,
) -> List[str]:
    """
    Search for files whose name matches `query` under `location`, in PURE
    Python (os.walk). This structurally eliminates the previous shell-pipeline
    command injection: there is no shell, no `dir`, no `findstr`.

    Returns a list of matching absolute paths (capped at `max_results`).
    """
    q = validate_search_query(query)
    root = validate_path(location, must_exist=True)

    needle = q.lower() if case_insensitive else q
    results: List[str] = []
    _audit("search_files", f"{q} in {root}")

    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in filenames:
            hay = fname.lower() if case_insensitive else fname
            if needle in hay:
                results.append(os.path.join(dirpath, fname))
                if len(results) >= max_results:
                    return results
    return results
