"""
Exception classes for Alice Browser Automation.

This module defines all custom exceptions used throughout the browser automation system.
Each exception type corresponds to specific error scenarios with appropriate recovery strategies.
"""


class BrowserAutomationError(Exception):
    """
    Base exception for all browser automation errors.
    
    All custom exceptions in this package inherit from this base class,
    allowing for broad exception handling when needed.
    """
    pass


class ElementNotFoundError(BrowserAutomationError):
    """
    Raised when an element selector fails to find the target element.
    
    Recovery Strategy:
    - Try alternative selectors from accessibility tree
    - Try CSS selector, XPath, ARIA label, text content match
    - Ask Qwen for alternative element identification
    
    Attributes:
        selector: The selector that failed
        page_url: URL of the page where element was not found
        dom_snapshot: Optional DOM snapshot for debugging
    """
    
    def __init__(self, message: str, selector: str = None, page_url: str = None):
        super().__init__(message)
        self.selector = selector
        self.page_url = page_url


class PageLoadTimeoutError(BrowserAutomationError):
    """
    Raised when page load exceeds timeout threshold.
    
    Recovery Strategy:
    - Check network connectivity
    - Retry navigation with longer timeout (up to 2 retries)
    - Report to user if all retries fail
    
    Attributes:
        url: The URL that failed to load
        timeout_seconds: The timeout value that was exceeded
        retry_count: Number of retries attempted
    """
    
    def __init__(self, message: str, url: str = None, timeout_seconds: float = None):
        super().__init__(message)
        self.url = url
        self.timeout_seconds = timeout_seconds


class InvalidActionError(BrowserAutomationError):
    """
    Raised when Qwen model generates an invalid or malformed action.
    
    Recovery Strategy:
    - Parse error details
    - Build correction prompt with error context
    - Request new action from Qwen (up to 3 attempts)
    - Fail task if still invalid after max attempts
    
    Attributes:
        invalid_json: The invalid JSON string that was generated
        validation_error: The specific validation error message
        retry_count: Number of correction attempts made
    """
    
    def __init__(self, message: str, invalid_json: str = None, validation_error: str = None):
        super().__init__(message)
        self.invalid_json = invalid_json
        self.validation_error = validation_error


class NetworkError(BrowserAutomationError):
    """
    Raised when network connectivity issues prevent browser operations.
    
    Recovery Strategy:
    - Check network connectivity
    - Retry operation with exponential backoff (up to 2 retries)
    - Report connectivity issue to user via Alice
    
    Attributes:
        operation: The operation that failed due to network error
        original_error: The underlying network error
    """
    
    def __init__(self, message: str, operation: str = None, original_error: Exception = None):
        super().__init__(message)
        self.operation = operation
        self.original_error = original_error


class SessionCrashedError(BrowserAutomationError):
    """
    Raised when a browser session crashes unexpectedly.
    
    Recovery Strategy:
    - Log crash details
    - Close crashed session
    - Create new session with same profile
    - Restore state (navigate to last URL)
    - Resume task from last successful action
    
    Attributes:
        session_id: ID of the crashed session
        last_url: Last known URL before crash
        crash_reason: Reason for crash if available
    """
    
    def __init__(self, message: str, session_id: str = None, last_url: str = None):
        super().__init__(message)
        self.session_id = session_id
        self.last_url = last_url


class QwenModelUnavailableError(BrowserAutomationError):
    """
    Raised when Qwen model is not available via Ollama.
    
    Recovery Strategy:
    - Check if Ollama service is running
    - Check if Qwen model is installed
    - Return error message to Alice with instructions
    
    Attributes:
        host: Ollama host that was unreachable
        model: Model name that was unavailable
        original_error: The underlying connection error
    """
    
    def __init__(self, message: str, host: str = None, model: str = None, original_error: Exception = None):
        super().__init__(message)
        self.host = host
        self.model = model
        self.original_error = original_error


class OTPVerificationError(BrowserAutomationError):
    """
    Raised when OTP verification fails.
    
    Recovery Strategy:
    - Request OTP again from user
    - Retry OTP entry (up to 3 attempts)
    - Report verification failure to user
    
    Attributes:
        verification_type: Type of verification (SMS, email, etc.)
        retry_count: Number of OTP entry attempts made
    """
    
    def __init__(self, message: str, verification_type: str = None):
        super().__init__(message)
        self.verification_type = verification_type


class ProfileError(BrowserAutomationError):
    """
    Raised when browser profile operations fail.
    
    Recovery Strategy:
    - Create new profile if profile doesn't exist
    - Repair corrupted profile data
    - Use default profile as fallback
    
    Attributes:
        profile_name: Name of the profile that caused the error
        operation: The operation that failed (create, load, delete)
    """
    
    def __init__(self, message: str, profile_name: str = None, operation: str = None):
        super().__init__(message)
        self.profile_name = profile_name
        self.operation = operation


class SecurityError(BrowserAutomationError):
    """
    Raised when security checks fail or are violated.
    
    Recovery Strategy:
    - Request explicit user permission
    - Abort operation if permission denied
    - Log security violation
    
    Attributes:
        security_check: The security check that failed
        resource: The resource that triggered the security error
    """
    
    def __init__(self, message: str, security_check: str = None, resource: str = None):
        super().__init__(message)
        self.security_check = security_check
        self.resource = resource


class ConfigurationError(BrowserAutomationError):
    """
    Raised when configuration is invalid or missing.
    
    Recovery Strategy:
    - Use default configuration values
    - Prompt user to fix configuration
    - Fail initialization if critical config missing
    
    Attributes:
        config_key: The configuration key that is invalid
        config_value: The invalid configuration value
    """
    
    def __init__(self, message: str, config_key: str = None, config_value: str = None):
        super().__init__(message)
        self.config_key = config_key
        self.config_value = config_value


class TaskCancelledException(BrowserAutomationError):
    """
    Raised when a task is cancelled by user request.
    
    This is not an error condition but a normal cancellation flow.
    
    Attributes:
        task_id: ID of the cancelled task
        reason: Reason for cancellation
    """
    
    def __init__(self, message: str, task_id: str = None, reason: str = None):
        super().__init__(message)
        self.task_id = task_id
        self.reason = reason


class SessionError(BrowserAutomationError):
    """
    Raised when browser session operations fail.
    
    Recovery Strategy:
    - Retry session creation
    - Use alternative profile
    - Report error to user
    
    Attributes:
        session_id: ID of the session that caused the error
        operation: The operation that failed (create, close, restart)
    """
    
    def __init__(self, message: str, session_id: str = None, operation: str = None):
        super().__init__(message)
        self.session_id = session_id
        self.operation = operation


class SessionLimitError(BrowserAutomationError):
    """
    Raised when maximum concurrent session limit is reached.
    
    Recovery Strategy:
    - Close idle sessions
    - Wait for existing session to complete
    - Report limit to user
    
    Attributes:
        current_count: Current number of active sessions
        max_limit: Maximum allowed concurrent sessions
    """
    
    def __init__(self, message: str, current_count: int = None, max_limit: int = None):
        super().__init__(message)
        self.current_count = current_count
        self.max_limit = max_limit
