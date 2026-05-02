"""
Security and Privacy Module for Alice Browser Automation.

This module implements security features including:
- Sensitive data filtering in logs
- Memory clearing for sensitive form data
- SSL certificate validation
- Banking website permission checks
- Payment confirmation workflow

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6
"""

import logging
import re
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from urllib.parse import urlparse
import ssl
import certifi


logger = logging.getLogger(__name__)


# ============================================================================
# Sensitive Data Patterns
# ============================================================================

# Patterns for detecting sensitive data
SENSITIVE_PATTERNS = {
    'password': re.compile(r'password|passwd|pwd|secret', re.IGNORECASE),
    'credit_card': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
    'cvv': re.compile(r'\b\d{3,4}\b'),
    'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    'otp': re.compile(r'\b\d{4,6}\b'),
    'api_key': re.compile(r'api[_-]?key|apikey|access[_-]?token', re.IGNORECASE),
    'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
}

# Banking and financial domains
BANKING_DOMAINS = {
    'chase.com', 'bankofamerica.com', 'wellsfargo.com', 'citibank.com',
    'usbank.com', 'pnc.com', 'capitalone.com', 'tdbank.com',
    'ally.com', 'discover.com', 'americanexpress.com', 'paypal.com',
    'venmo.com', 'cashapp.com', 'zelle.com', 'stripe.com',
    # Add more banking domains as needed
}

# Payment-related keywords
PAYMENT_KEYWORDS = {
    'payment', 'checkout', 'billing', 'credit card', 'debit card',
    'pay now', 'complete purchase', 'confirm order', 'place order',
    'submit payment', 'card number', 'cvv', 'expiry', 'expiration'
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SensitiveDataContext:
    """Context for sensitive data handling."""
    field_name: str
    field_type: str  # password, credit_card, cvv, etc.
    value: Optional[str] = None  # Only stored temporarily
    cleared: bool = False
    
    def clear(self):
        """Clear sensitive value from memory."""
        if self.value:
            # Overwrite with zeros before deletion
            self.value = '0' * len(self.value)
            self.value = None
        self.cleared = True


@dataclass
class PaymentConfirmation:
    """Payment confirmation details."""
    amount: Optional[str] = None
    merchant: Optional[str] = None
    payment_method: Optional[str] = None  # last 4 digits only
    confirmed: bool = False
    confirmation_callback: Optional[Any] = None


# ============================================================================
# Security Manager
# ============================================================================

class SecurityManager:
    """
    Manages security and privacy features for browser automation.
    
    **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6**
    
    Features:
    - Sensitive data filtering in logs
    - Memory clearing for sensitive data
    - SSL certificate validation
    - Banking website permission checks
    - Payment confirmation workflow
    """
    
    def __init__(
        self,
        require_payment_confirmation: bool = True,
        block_banking_sites: bool = False,
        validate_ssl: bool = True,
        clear_sensitive_data: bool = True
    ):
        """
        Initialize Security Manager.
        
        Args:
            require_payment_confirmation: Whether to require confirmation for payments
            block_banking_sites: Whether to block banking sites without permission
            validate_ssl: Whether to validate SSL certificates
            clear_sensitive_data: Whether to clear sensitive data from memory
        """
        self.require_payment_confirmation = require_payment_confirmation
        self.block_banking_sites = block_banking_sites
        self.validate_ssl = validate_ssl
        self.clear_sensitive_data = clear_sensitive_data
        
        # Track sensitive data contexts
        self._sensitive_contexts: List[SensitiveDataContext] = []
        
        # Track banking permissions
        self._banking_permissions: Set[str] = set()
        
        # Track pending payment confirmations
        self._pending_payments: Dict[str, PaymentConfirmation] = {}
        
        logger.info(
            f"SecurityManager initialized: "
            f"payment_confirmation={require_payment_confirmation}, "
            f"block_banking={block_banking_sites}, "
            f"validate_ssl={validate_ssl}"
        )
    
    # ========================================================================
    # Sensitive Data Filtering (Requirement 10.1, 10.2)
    # ========================================================================
    
    def filter_sensitive_data(self, text: str) -> str:
        """
        Filter sensitive data from text (for logging).
        
        **Validates: Requirement 10.2** - Not log sensitive data
        
        Args:
            text: Text that may contain sensitive data
            
        Returns:
            Text with sensitive data replaced with [REDACTED]
        """
        filtered = text
        
        # Replace credit card numbers
        filtered = SENSITIVE_PATTERNS['credit_card'].sub('[REDACTED_CC]', filtered)
        
        # Replace SSN
        filtered = SENSITIVE_PATTERNS['ssn'].sub('[REDACTED_SSN]', filtered)
        
        # Replace OTP codes (but be careful not to replace all numbers)
        # Only replace if it looks like an OTP in context
        if re.search(r'(otp|code|verification|pin)[\s:]+\d{4,6}', filtered, re.IGNORECASE):
            filtered = re.sub(r'(otp|code|verification|pin)([\s:]+)(\d{4,6})', r'\1\2[REDACTED_OTP]', filtered, flags=re.IGNORECASE)
        # Also handle "Your code is 123456" pattern
        filtered = re.sub(r'(your\s+code\s+is\s+)(\d{4,6})', r'\1[REDACTED_OTP]', filtered, flags=re.IGNORECASE)
        
        # Replace API keys
        filtered = SENSITIVE_PATTERNS['api_key'].sub('[REDACTED_KEY]', filtered)
        
        # Replace password values (look for password: value pattern)
        filtered = re.sub(
            r'(password|passwd|pwd|secret)([\s:=]+)([^\s,]+)',
            r'\1\2[REDACTED_PWD]',
            filtered,
            flags=re.IGNORECASE
        )
        
        # Replace email addresses (partial)
        def redact_email(match):
            email = match.group(0)
            parts = email.split('@')
            if len(parts) == 2:
                username = parts[0]
                if len(username) > 2:
                    return f"{username[:2]}***@{parts[1]}"
            return '[REDACTED_EMAIL]'
        
        filtered = SENSITIVE_PATTERNS['email'].sub(redact_email, filtered)
        
        return filtered
    
    def is_sensitive_field(self, field_name: str, field_type: str = "") -> bool:
        """
        Check if a field contains sensitive data.
        
        Args:
            field_name: Name of the field
            field_type: Type attribute of the field
            
        Returns:
            True if field is sensitive
        """
        field_lower = field_name.lower()
        type_lower = field_type.lower()
        
        # Check for password fields
        if SENSITIVE_PATTERNS['password'].search(field_lower):
            return True
        if type_lower == 'password':
            return True
        
        # Check for credit card fields
        if any(keyword in field_lower for keyword in ['card', 'cc', 'credit']):
            return True
        
        # Check for CVV fields
        if any(keyword in field_lower for keyword in ['cvv', 'cvc', 'security_code', 'securitycode']):
            return True
        
        # Check for SSN fields
        if any(keyword in field_lower for keyword in ['ssn', 'social_security', 'socialsecurity']):
            return True
        
        return False
    
    def register_sensitive_data(
        self,
        field_name: str,
        field_type: str,
        value: Optional[str] = None
    ) -> SensitiveDataContext:
        """
        Register sensitive data for tracking and clearing.
        
        **Validates: Requirement 10.4** - Clear sensitive data after task completion
        
        Args:
            field_name: Name of the sensitive field
            field_type: Type of sensitive data
            value: Optional value (will be cleared)
            
        Returns:
            SensitiveDataContext for tracking
        """
        context = SensitiveDataContext(
            field_name=field_name,
            field_type=field_type,
            value=value
        )
        self._sensitive_contexts.append(context)
        
        logger.debug(f"Registered sensitive field: {field_name} (type: {field_type})")
        
        return context
    
    def clear_all_sensitive_data(self):
        """
        Clear all registered sensitive data from memory.
        
        **Validates: Requirement 10.4** - Clear sensitive data after task completion
        """
        if not self.clear_sensitive_data:
            return
        
        cleared_count = 0
        for context in self._sensitive_contexts:
            if not context.cleared:
                context.clear()
                cleared_count += 1
        
        logger.info(f"Cleared {cleared_count} sensitive data contexts")
        
        # Clear the list
        self._sensitive_contexts.clear()
    
    # ========================================================================
    # SSL Certificate Validation (Requirement 10.5)
    # ========================================================================
    
    def validate_ssl_certificate(self, url: str) -> bool:
        """
        Validate SSL certificate for HTTPS connections.
        
        **Validates: Requirement 10.5** - Validate SSL certificates
        
        Args:
            url: URL to validate
            
        Returns:
            True if SSL certificate is valid
            
        Raises:
            ssl.SSLError: If certificate validation fails
        """
        if not self.validate_ssl:
            return True
        
        parsed = urlparse(url)
        
        # Only validate HTTPS URLs
        if parsed.scheme != 'https':
            logger.warning(f"Non-HTTPS URL: {url}")
            return True
        
        hostname = parsed.hostname
        port = parsed.port or 443
        
        try:
            # Create SSL context with certificate verification
            context = ssl.create_default_context(cafile=certifi.where())
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            
            # Test connection
            with ssl.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    logger.debug(f"SSL certificate valid for {hostname}")
                    return True
        
        except ssl.SSLError as e:
            logger.error(f"SSL certificate validation failed for {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error validating SSL certificate for {url}: {e}")
            return False
    
    # ========================================================================
    # Banking Website Permissions (Requirement 10.6)
    # ========================================================================
    
    def is_banking_website(self, url: str) -> bool:
        """
        Check if URL is a banking or financial website.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is a banking website
        """
        parsed = urlparse(url)
        domain = parsed.hostname
        
        if not domain:
            return False
        
        # Check exact match
        if domain in BANKING_DOMAINS:
            return True
        
        # Check subdomain match (e.g., online.chase.com)
        for banking_domain in BANKING_DOMAINS:
            if domain.endswith(f".{banking_domain}"):
                return True
        
        return False
    
    def check_banking_permission(self, url: str) -> bool:
        """
        Check if user has granted permission for banking website.
        
        **Validates: Requirement 10.6** - Explicit permission for banking sites
        
        Args:
            url: URL to check
            
        Returns:
            True if permission granted or not a banking site
            
        Raises:
            PermissionError: If banking site access blocked without permission
        """
        if not self.is_banking_website(url):
            return True
        
        parsed = urlparse(url)
        domain = parsed.hostname
        
        # Check if permission already granted
        if domain in self._banking_permissions:
            return True
        
        # Block if configured to block banking sites
        if self.block_banking_sites:
            logger.error(f"Banking website access blocked: {url}")
            raise PermissionError(
                f"Access to banking website {domain} requires explicit permission"
            )
        
        logger.warning(f"Banking website access without explicit permission: {url}")
        return True
    
    def grant_banking_permission(self, url: str):
        """
        Grant permission to access a banking website.
        
        Args:
            url: URL to grant permission for
        """
        parsed = urlparse(url)
        domain = parsed.hostname
        
        if domain:
            self._banking_permissions.add(domain)
            logger.info(f"Banking permission granted for: {domain}")
    
    def revoke_banking_permission(self, url: str):
        """
        Revoke permission to access a banking website.
        
        Args:
            url: URL to revoke permission for
        """
        parsed = urlparse(url)
        domain = parsed.hostname
        
        if domain and domain in self._banking_permissions:
            self._banking_permissions.remove(domain)
            logger.info(f"Banking permission revoked for: {domain}")
    
    # ========================================================================
    # Payment Confirmation (Requirement 10.3, 10.4)
    # ========================================================================
    
    def is_payment_action(self, action_description: str, page_content: str = "") -> bool:
        """
        Check if action involves payment processing.
        
        Args:
            action_description: Description of the action
            page_content: Content of the current page
            
        Returns:
            True if action involves payment
        """
        text = (action_description + " " + page_content).lower()
        
        # Check for payment keywords
        for keyword in PAYMENT_KEYWORDS:
            if keyword in text:
                return True
        
        return False
    
    def create_payment_confirmation(
        self,
        task_id: str,
        amount: Optional[str] = None,
        merchant: Optional[str] = None,
        payment_method: Optional[str] = None
    ) -> PaymentConfirmation:
        """
        Create a payment confirmation request.
        
        **Validates: Requirement 10.3** - Require explicit confirmation for payments
        
        Args:
            task_id: ID of the task requiring confirmation
            amount: Payment amount
            merchant: Merchant name
            payment_method: Payment method (last 4 digits only)
            
        Returns:
            PaymentConfirmation object
        """
        confirmation = PaymentConfirmation(
            amount=amount,
            merchant=merchant,
            payment_method=payment_method,
            confirmed=False
        )
        
        self._pending_payments[task_id] = confirmation
        
        logger.info(
            f"Payment confirmation required for task {task_id}: "
            f"amount={amount}, merchant={merchant}"
        )
        
        return confirmation
    
    def confirm_payment(self, task_id: str) -> bool:
        """
        Confirm a pending payment.
        
        Args:
            task_id: ID of the task to confirm
            
        Returns:
            True if payment was confirmed
        """
        if task_id not in self._pending_payments:
            logger.warning(f"No pending payment for task {task_id}")
            return False
        
        confirmation = self._pending_payments[task_id]
        confirmation.confirmed = True
        
        logger.info(f"Payment confirmed for task {task_id}")
        
        return True
    
    def is_payment_confirmed(self, task_id: str) -> bool:
        """
        Check if payment has been confirmed.
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            True if payment confirmed or no confirmation required
        """
        if not self.require_payment_confirmation:
            return True
        
        if task_id not in self._pending_payments:
            return True
        
        return self._pending_payments[task_id].confirmed
    
    def cancel_payment(self, task_id: str):
        """
        Cancel a pending payment.
        
        Args:
            task_id: ID of the task to cancel
        """
        if task_id in self._pending_payments:
            del self._pending_payments[task_id]
            logger.info(f"Payment cancelled for task {task_id}")
    
    def get_payment_summary(self, task_id: str) -> Optional[str]:
        """
        Get a summary of pending payment for user confirmation.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Human-readable payment summary
        """
        if task_id not in self._pending_payments:
            return None
        
        confirmation = self._pending_payments[task_id]
        
        parts = []
        if confirmation.amount:
            parts.append(f"Amount: {confirmation.amount}")
        if confirmation.merchant:
            parts.append(f"Merchant: {confirmation.merchant}")
        if confirmation.payment_method:
            parts.append(f"Payment method ending in: {confirmation.payment_method}")
        
        return ", ".join(parts) if parts else "Payment confirmation required"


# ============================================================================
# Logging Filter
# ============================================================================

class SensitiveDataFilter(logging.Filter):
    """
    Logging filter to redact sensitive data from log messages.
    
    **Validates: Requirement 10.2** - Not log sensitive data
    """
    
    def __init__(self, security_manager: SecurityManager):
        """
        Initialize filter with security manager.
        
        Args:
            security_manager: SecurityManager instance for filtering
        """
        super().__init__()
        self.security_manager = security_manager
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record to redact sensitive data.
        
        Args:
            record: Log record to filter
            
        Returns:
            True (always allow record, but modify message)
        """
        # Filter the message
        if isinstance(record.msg, str):
            record.msg = self.security_manager.filter_sensitive_data(record.msg)
        
        # Filter arguments
        if record.args:
            filtered_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    filtered_args.append(
                        self.security_manager.filter_sensitive_data(arg)
                    )
                else:
                    filtered_args.append(arg)
            record.args = tuple(filtered_args)
        
        return True


def install_sensitive_data_filter(security_manager: SecurityManager):
    """
    Install sensitive data filter on all loggers.
    
    Args:
        security_manager: SecurityManager instance for filtering
    """
    filter_instance = SensitiveDataFilter(security_manager)
    
    # Install on root logger
    root_logger = logging.getLogger()
    root_logger.addFilter(filter_instance)
    
    # Install on package logger
    package_logger = logging.getLogger('alice_browser_automation')
    package_logger.addFilter(filter_instance)
    
    logger.info("Sensitive data filter installed on loggers")
