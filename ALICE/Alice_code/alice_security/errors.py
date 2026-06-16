"""Security exceptions for the ALICE safe-execution layer."""


class SecurityValidationError(Exception):
    """
    Raised when input fails a security validation check before it would reach
    an OS-level action (process launch, file open, URL open, file search).

    Callers (tools) should catch this and return a graceful, user-facing
    refusal rather than letting it crash the agent loop. The message is safe
    to surface to the user/LLM; it never contains secrets.
    """

    def __init__(self, message: str, *, field: str = "", value: str = ""):
        self.field = field
        # Keep a short, redacted echo of the offending value for logs/debugging.
        self.value_preview = (value[:64] + "…") if len(value) > 64 else value
        super().__init__(message)
