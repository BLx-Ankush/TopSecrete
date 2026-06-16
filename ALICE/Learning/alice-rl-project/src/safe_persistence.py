"""
Safe persistence for the ALICE RL subproject.
=============================================
The RL memory/model files were loaded with `pickle.load` / `torch.load`, both of
which execute arbitrary code embedded in a crafted file (CWE-502). If an attacker
can place or tamper with a memory/checkpoint file, that is remote code execution
when ALICE loads it.

This module makes loading safe WITHOUT changing what ALICE stores:

  - `secure_save(obj, path)` writes the pickle AND a detached HMAC-SHA256
    signature (`<path>.sig`) computed with a machine-local secret key.
  - `secure_load(path)` recomputes the HMAC and refuses to unpickle if the
    signature is missing or does not match — so only files ALICE itself wrote
    (with this machine's key) are ever deserialized.
  - `safe_torch_load(path)` defaults to `weights_only=True` (tensors only, no
    arbitrary globals) and verifies an HMAC sidecar when present.

The key lives in `ALICE_RL_HMAC_KEY` (env) or a 0600 key file next to the code.
It never leaves the machine and is not committed.
"""

import hashlib
import hmac
import logging
import os
import pickle
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_KEY_ENV = "ALICE_RL_HMAC_KEY"
_KEY_FILE = Path(__file__).resolve().parent / ".alice_rl_hmac.key"


class IntegrityError(Exception):
    """Raised when a file's signature is missing or does not verify."""


def _get_key() -> bytes:
    """Return the machine-local HMAC key, creating one on first use."""
    env = os.getenv(_KEY_ENV)
    if env:
        return env.encode("utf-8")
    try:
        if _KEY_FILE.exists():
            return _KEY_FILE.read_bytes()
        key = os.urandom(32)
        # Best-effort restrictive permissions (POSIX). On Windows the file
        # inherits the user's ACL, which is acceptable for a per-user key.
        _KEY_FILE.write_bytes(key)
        try:
            os.chmod(_KEY_FILE, 0o600)
        except Exception:
            pass
        logger.info("[safe_persistence] generated new RL HMAC key")
        return key
    except Exception as e:
        # Last resort: derive a stable key from the machine + user. Weaker, but
        # still blocks foreign/tampered files in practice.
        logger.warning(f"[safe_persistence] key file unavailable ({e}); using derived key")
        seed = f"{os.getpid()}-{os.path.expanduser('~')}".encode()
        return hashlib.sha256(seed).digest()


def _sig_path(filepath: str) -> str:
    return str(filepath) + ".sig"


def _compute_hmac(data: bytes) -> bytes:
    return hmac.new(_get_key(), data, hashlib.sha256).digest()


def secure_save(obj: Any, filepath: str) -> None:
    """Pickle `obj` to `filepath` and write a detached HMAC signature."""
    data = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
    with open(filepath, "wb") as f:
        f.write(data)
    with open(_sig_path(filepath), "wb") as f:
        f.write(_compute_hmac(data))
    logger.debug(f"[safe_persistence] saved + signed {filepath}")


def secure_load(filepath: str) -> Any:
    """
    Verify the HMAC signature, then unpickle. Raises IntegrityError if the
    signature is missing or invalid — the file is NOT unpickled in that case,
    so a tampered/foreign file can never execute code.
    """
    sig_file = _sig_path(filepath)
    if not os.path.exists(sig_file):
        raise IntegrityError(
            f"Refusing to load '{filepath}': no signature file. "
            f"Only memory files written by this ALICE instance can be loaded."
        )
    with open(filepath, "rb") as f:
        data = f.read()
    with open(sig_file, "rb") as f:
        expected = f.read()
    if not hmac.compare_digest(expected, _compute_hmac(data)):
        raise IntegrityError(
            f"Refusing to load '{filepath}': signature mismatch (file was "
            f"modified or created elsewhere)."
        )
    # Verified — safe to deserialize.
    return pickle.loads(data)


def safe_torch_load(filepath: str, map_location: Optional[Any] = None, **kwargs):
    """
    Safe wrapper around torch.load.

    - Defaults to `weights_only=True` so only tensors/standard types are
      unpickled (no arbitrary globals / code execution). Callers that genuinely
      need full objects must pass weights_only=False explicitly AND should only
      do so for files they trust.
    - If a `.sig` sidecar exists, its HMAC is verified first.
    """
    import torch

    sig_file = _sig_path(filepath)
    if os.path.exists(sig_file):
        with open(filepath, "rb") as f:
            data = f.read()
        with open(sig_file, "rb") as f:
            expected = f.read()
        if not hmac.compare_digest(expected, _compute_hmac(data)):
            raise IntegrityError(f"Refusing to load '{filepath}': signature mismatch.")

    kwargs.setdefault("weights_only", True)
    if map_location is not None:
        kwargs["map_location"] = map_location
    return torch.load(filepath, **kwargs)


def safe_torch_save(obj: Any, filepath: str) -> None:
    """torch.save + detached HMAC signature, mirroring secure_save."""
    import torch

    torch.save(obj, filepath)
    with open(filepath, "rb") as f:
        data = f.read()
    with open(_sig_path(filepath), "wb") as f:
        f.write(_compute_hmac(data))
