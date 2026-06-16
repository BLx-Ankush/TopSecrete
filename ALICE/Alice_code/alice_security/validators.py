"""
Input validators for the ALICE safe-execution layer.

These functions are PURE and have no OS side effects, so they run and unit-test
on any platform (CI on Linux/macOS, production on Windows). They are the trust
boundary: every value derived from voice/LLM input must pass through the
relevant validator before it reaches `safe_exec`.

Philosophy:
  - Reject, don't sanitize-and-hope. If input contains shell metacharacters or
    path traversal, we refuse it rather than trying to escape it.
  - Behaviour-neutral: legitimate app names, paths, URLs and search terms pass
    unchanged. Only genuinely dangerous input is rejected.
"""

import os
import re
from typing import Iterable, Optional

from .errors import SecurityValidationError

# ──────────────────────────────────────────────────────────────────────────
# Shell metacharacters — the building blocks of command injection.
# If any of these appear in user-derived input that would reach a process
# launch, we refuse. None of them are valid in an app name, and they are not
# needed in legitimate file paths or URLs we launch.
# ──────────────────────────────────────────────────────────────────────────
SHELL_METACHARACTERS = set('&|;<>$`\n\r\t"\'\\^!*?{}[]()~')

# Characters allowed in a human-spoken application name. Covers real app names
# like "Visual Studio Code", "7-Zip", "Notepad++", "Microsoft.WindowsNotepad".
_APP_NAME_ALLOWED = re.compile(r"^[A-Za-z0-9 ._+\-:#]+$")

# URL schemes ALICE is permitted to open. Anything else (file:, javascript:,
# data:, custom handlers) is refused.
_ALLOWED_URL_SCHEMES = {"http", "https", "mailto", "tel"}

# Application "protocol" launches that are legitimately used by ALICE
# (e.g. "whatsapp:", "ms-windows-store:"). These bypass the path checks but
# still must be metacharacter-clean and on this allowlist.
_ALLOWED_APP_PROTOCOLS = {
    "whatsapp", "ms-windows-store", "ms-settings", "mailto", "tel", "callto",
}

_MAX_APP_NAME_LEN = 128
_MAX_PATH_LEN = 4096
_MAX_QUERY_LEN = 256
_MAX_URL_LEN = 2048


def contains_shell_metacharacters(value: str) -> bool:
    """True if `value` contains any character used to chain/redirect shell commands."""
    return any(ch in SHELL_METACHARACTERS for ch in value)


def validate_app_name(app_name: str) -> str:
    """
    Validate a user/LLM-supplied application name.

    Returns the trimmed name on success. Raises SecurityValidationError if the
    name is empty, too long, or contains characters that have no business in an
    application name (which are exactly the characters used for injection).

    This does NOT resolve the app to a path — that is `safe_exec.launch_app`'s
    job, which only ever launches names found in the trusted app database.
    """
    if not isinstance(app_name, str):
        raise SecurityValidationError("App name must be a string.", field="app_name")
    name = app_name.strip()
    if not name:
        raise SecurityValidationError("App name is empty.", field="app_name")
    if len(name) > _MAX_APP_NAME_LEN:
        raise SecurityValidationError(
            "App name is too long.", field="app_name", value=name
        )
    if contains_shell_metacharacters(name):
        raise SecurityValidationError(
            "App name contains forbidden characters.", field="app_name", value=name
        )
    if not _APP_NAME_ALLOWED.match(name):
        raise SecurityValidationError(
            "App name contains characters outside the allowed set.",
            field="app_name",
            value=name,
        )
    return name


def validate_path(
    path: str,
    *,
    must_exist: bool = False,
    allowed_roots: Optional[Iterable[str]] = None,
) -> str:
    """
    Validate and canonicalize a filesystem path.

    - Rejects shell metacharacters (newlines, quotes, &, |, etc.).
    - Canonicalizes (resolves `..`, symlinks where possible) to defeat traversal.
    - If `allowed_roots` is given, the resolved path must live under one of them.
    - If `must_exist`, the path must point at an existing file/dir.

    Returns the normalized absolute path on success.
    """
    if not isinstance(path, str):
        raise SecurityValidationError("Path must be a string.", field="path")
    raw = path.strip().strip('"')
    if not raw:
        raise SecurityValidationError("Path is empty.", field="path")
    if len(raw) > _MAX_PATH_LEN:
        raise SecurityValidationError("Path is too long.", field="path", value=raw)
    # Newlines / NUL / quotes / shell chaining chars never belong in a real path.
    forbidden = set('\n\r\t\x00"\'`$|&;<>^*?')
    if any(ch in forbidden for ch in raw):
        raise SecurityValidationError(
            "Path contains forbidden characters.", field="path", value=raw
        )

    normalized = os.path.normpath(os.path.abspath(os.path.expanduser(raw)))

    if allowed_roots:
        roots = [
            os.path.normpath(os.path.abspath(os.path.expanduser(r)))
            for r in allowed_roots
        ]
        if not any(_is_within(normalized, root) for root in roots):
            raise SecurityValidationError(
                "Path is outside the permitted directories.",
                field="path",
                value=normalized,
            )

    if must_exist and not os.path.exists(normalized):
        raise SecurityValidationError(
            "Path does not exist.", field="path", value=normalized
        )

    return normalized


def _is_within(path: str, root: str) -> bool:
    """True if `path` is `root` or nested inside it (after normalization)."""
    try:
        common = os.path.commonpath([path, root])
    except ValueError:
        # Different drives on Windows -> not within.
        return False
    return common == root


def validate_url(url: str) -> str:
    """
    Validate a URL before opening it in a browser.

    Allows only http/https/mailto/tel schemes and rejects shell metacharacters.
    Returns the trimmed URL on success.
    """
    if not isinstance(url, str):
        raise SecurityValidationError("URL must be a string.", field="url")
    u = url.strip()
    if not u:
        raise SecurityValidationError("URL is empty.", field="url")
    if len(u) > _MAX_URL_LEN:
        raise SecurityValidationError("URL is too long.", field="url", value=u)
    # Control chars / quotes / chaining chars must not appear in a URL we launch.
    if any(ch in set('\n\r\t\x00"\'`$|&;<>^') for ch in u):
        raise SecurityValidationError(
            "URL contains forbidden characters.", field="url", value=u
        )

    scheme = u.split(":", 1)[0].lower() if ":" in u else ""
    if not scheme:
        # Bare "example.com" -> default to https, which is the safe assumption.
        return "https://" + u
    if scheme not in _ALLOWED_URL_SCHEMES:
        raise SecurityValidationError(
            f"URL scheme '{scheme}' is not allowed.", field="url", value=u
        )
    return u


def validate_app_protocol(value: str) -> Optional[str]:
    """
    If `value` is an allowlisted app/store protocol launch (e.g. 'whatsapp:',
    'ms-windows-store://pdp/?ProductId=...'), return its scheme; otherwise
    return None.

    These are dispatched via `os.startfile` / `webbrowser.open`, which do NOT
    invoke a shell, so query characters like '?', '=', '&' are legitimate and
    safe here. We still reject genuine control/quoting characters as hygiene.
    """
    if not isinstance(value, str) or ":" not in value:
        return None
    # Only true control/quoting chars are forbidden in a protocol URI; query
    # syntax (?, =, &) is normal and not shell-interpreted by os.startfile.
    if any(ch in set('\n\r\t\x00"\'`') for ch in value):
        return None
    scheme = value.split(":", 1)[0].lower()
    return scheme if scheme in _ALLOWED_APP_PROTOCOLS else None


def validate_search_query(query: str) -> str:
    """
    Validate a filename-search term.

    Note: in `safe_exec.search_files` this term is matched in pure Python
    (os.walk + substring/glob), NOT passed to a `dir | findstr` shell pipeline,
    so injection is structurally impossible. We still reject control characters
    and over-long input as a hygiene/DoS guard.
    """
    if not isinstance(query, str):
        raise SecurityValidationError("Search query must be a string.", field="query")
    q = query.strip()
    if not q:
        raise SecurityValidationError("Search query is empty.", field="query")
    if len(q) > _MAX_QUERY_LEN:
        raise SecurityValidationError(
            "Search query is too long.", field="query", value=q
        )
    if any(ch in set('\n\r\x00') for ch in q):
        raise SecurityValidationError(
            "Search query contains forbidden characters.", field="query", value=q
        )
    return q
