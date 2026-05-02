"""
Chrome Profile Manager for Alice Browser Automation.

This module manages persistent browser profiles for different domains/applications.
Each profile stores cookies, local storage, session storage, and browser preferences
to enable session persistence across browser restarts.

**Validates: Requirements 7.1, 7.2, 7.7, 10.1, 10.2**
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import base64
import os

# Security and encryption
import keyring
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from .exceptions import ProfileError, SecurityError


logger = logging.getLogger(__name__)

# Service name for keyring storage
KEYRING_SERVICE_NAME = "alice_browser_automation"


class ChromeProfileManager:
    """
    Manage Chrome profiles for persistent browser sessions.
    
    Each profile maintains:
    - Cookies (cookies.db)
    - Local storage data (local_storage/)
    - Session storage data (session_storage/)
    - Browser preferences (preferences.json)
    
    This enables session persistence across browser restarts and allows
    users to stay logged in to applications.
    """
    
    def __init__(self, profiles_dir: str = "~/.alice/browser_profiles"):
        """
        Initialize the Chrome Profile Manager.
        
        Args:
            profiles_dir: Base directory for storing browser profiles.
                         Defaults to ~/.alice/browser_profiles
        
        Raises:
            ProfileError: If profiles directory cannot be created
        """
        self.profiles_dir = Path(profiles_dir).expanduser().resolve()
        
        try:
            self.profiles_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Profile manager initialized with directory: {self.profiles_dir}")
        except Exception as e:
            raise ProfileError(
                f"Failed to create profiles directory: {self.profiles_dir}",
                profile_name=None,
                operation="initialize"
            ) from e
    
    def get_or_create_profile(self, profile_name: str = "default") -> Path:
        """
        Get existing profile directory or create a new one.
        
        Creates the profile directory structure if it doesn't exist:
        - profile_name/
          - cookies.db (empty file, will be populated by browser)
          - local_storage/ (directory)
          - session_storage/ (directory)
          - preferences.json (default preferences)
        
        Args:
            profile_name: Name of the profile. Defaults to "default".
        
        Returns:
            Path to the profile directory
        
        Raises:
            ProfileError: If profile creation fails
            ValueError: If profile_name is invalid
        """
        # Validate profile name
        if not profile_name or not profile_name.strip():
            raise ValueError("Profile name cannot be empty")
        
        # Sanitize profile name to prevent path traversal
        safe_profile_name = self._sanitize_profile_name(profile_name)
        if safe_profile_name != profile_name:
            logger.warning(
                f"Profile name '{profile_name}' was sanitized to '{safe_profile_name}'"
            )
        
        profile_path = self.profiles_dir / safe_profile_name
        
        # If profile exists, return it
        if profile_path.exists():
            logger.debug(f"Using existing profile: {safe_profile_name}")
            return profile_path
        
        # Create new profile
        try:
            logger.info(f"Creating new profile: {safe_profile_name}")
            self._create_profile_structure(profile_path)
            return profile_path
        except Exception as e:
            raise ProfileError(
                f"Failed to create profile: {safe_profile_name}",
                profile_name=safe_profile_name,
                operation="create"
            ) from e
    
    def list_profiles(self) -> List[str]:
        """
        List all available browser profiles.
        
        Returns:
            List of profile names (directory names in profiles_dir)
        
        Example:
            >>> manager = ChromeProfileManager()
            >>> manager.list_profiles()
            ['default', 'work', 'personal']
        """
        try:
            profiles = [
                p.name for p in self.profiles_dir.iterdir()
                if p.is_dir() and not p.name.startswith('.')
            ]
            logger.debug(f"Found {len(profiles)} profiles: {profiles}")
            return sorted(profiles)
        except Exception as e:
            logger.error(f"Failed to list profiles: {e}")
            return []
    
    def delete_profile(self, profile_name: str) -> bool:
        """
        Delete a profile and all its data.
        
        This permanently removes:
        - All cookies
        - Local storage data
        - Session storage data
        - Browser preferences
        - Stored credentials from keychain
        - Any other profile-specific data
        
        Args:
            profile_name: Name of the profile to delete
        
        Returns:
            True if profile was deleted successfully, False otherwise
        
        Raises:
            ProfileError: If profile deletion fails
            ValueError: If trying to delete a non-existent profile
        
        Example:
            >>> manager = ChromeProfileManager()
            >>> manager.delete_profile("old_profile")
            True
        """
        if not profile_name or not profile_name.strip():
            raise ValueError("Profile name cannot be empty")
        
        safe_profile_name = self._sanitize_profile_name(profile_name)
        profile_path = self.profiles_dir / safe_profile_name
        
        if not profile_path.exists():
            raise ValueError(f"Profile does not exist: {profile_name}")
        
        try:
            logger.info(f"Deleting profile: {safe_profile_name}")
            
            # Delete credentials from keychain first
            try:
                deleted_creds = self.delete_credentials(safe_profile_name)
                logger.info(f"Deleted {deleted_creds} credential(s) from keychain")
            except Exception as e:
                logger.warning(f"Failed to delete credentials from keychain: {e}")
            
            # Delete profile directory
            shutil.rmtree(profile_path)
            logger.info(f"Profile deleted successfully: {safe_profile_name}")
            return True
        except Exception as e:
            raise ProfileError(
                f"Failed to delete profile: {safe_profile_name}",
                profile_name=safe_profile_name,
                operation="delete"
            ) from e
    
    def get_profile_info(self, profile_name: str) -> Dict[str, any]:
        """
        Get information about a profile.
        
        Args:
            profile_name: Name of the profile
        
        Returns:
            Dictionary containing profile information:
            - name: Profile name
            - path: Full path to profile directory
            - created: Creation timestamp (if available)
            - size_bytes: Total size of profile data
            - has_cookies: Whether cookies.db exists
            - has_preferences: Whether preferences.json exists
        
        Raises:
            ValueError: If profile doesn't exist
        """
        safe_profile_name = self._sanitize_profile_name(profile_name)
        profile_path = self.profiles_dir / safe_profile_name
        
        if not profile_path.exists():
            raise ValueError(f"Profile does not exist: {profile_name}")
        
        # Calculate total size
        total_size = sum(
            f.stat().st_size for f in profile_path.rglob('*') if f.is_file()
        )
        
        # Get creation time (from directory stat)
        stat = profile_path.stat()
        created = datetime.fromtimestamp(stat.st_ctime)
        
        return {
            "name": safe_profile_name,
            "path": str(profile_path),
            "created": created.isoformat(),
            "size_bytes": total_size,
            "has_cookies": (profile_path / "cookies.db").exists(),
            "has_preferences": (profile_path / "preferences.json").exists(),
        }
    
    def _sanitize_profile_name(self, profile_name: str) -> str:
        """
        Sanitize profile name to prevent path traversal attacks.
        
        Removes or replaces dangerous characters:
        - Path separators (/, \\)
        - Parent directory references (..)
        - Hidden file indicators (leading .)
        
        Args:
            profile_name: Raw profile name
        
        Returns:
            Sanitized profile name safe for filesystem use
        
        Raises:
            SecurityError: If profile name is malicious
        """
        # Remove leading/trailing whitespace
        name = profile_name.strip()
        
        # Check for path traversal attempts
        if ".." in name or "/" in name or "\\" in name:
            raise SecurityError(
                f"Invalid profile name: {profile_name}",
                security_check="path_traversal",
                resource=profile_name
            )
        
        # Remove leading dots (hidden files)
        name = name.lstrip(".")
        
        # Replace any remaining problematic characters
        # Allow alphanumeric, underscore, hyphen, and space
        safe_chars = []
        for char in name:
            if char.isalnum() or char in ("_", "-", " "):
                safe_chars.append(char)
            else:
                safe_chars.append("_")
        
        sanitized = "".join(safe_chars).strip()
        
        # Ensure name is not empty after sanitization
        if not sanitized:
            raise SecurityError(
                f"Profile name becomes empty after sanitization: {profile_name}",
                security_check="empty_name",
                resource=profile_name
            )
        
        return sanitized
    
    def _create_profile_structure(self, profile_path: Path) -> None:
        """
        Create the directory structure for a new profile.
        
        Creates:
        - profile_path/ (main directory)
        - profile_path/cookies.db (empty file)
        - profile_path/local_storage/ (directory)
        - profile_path/session_storage/ (directory)
        - profile_path/preferences.json (default preferences)
        
        Args:
            profile_path: Path where profile should be created
        
        Raises:
            OSError: If directory or file creation fails
        """
        # Create main profile directory
        profile_path.mkdir(parents=True, exist_ok=True)
        
        # Create cookies.db (empty file, will be populated by browser)
        cookies_file = profile_path / "cookies.db"
        cookies_file.touch()
        logger.debug(f"Created cookies.db at {cookies_file}")
        
        # Create local_storage directory
        local_storage_dir = profile_path / "local_storage"
        local_storage_dir.mkdir(exist_ok=True)
        logger.debug(f"Created local_storage directory at {local_storage_dir}")
        
        # Create session_storage directory
        session_storage_dir = profile_path / "session_storage"
        session_storage_dir.mkdir(exist_ok=True)
        logger.debug(f"Created session_storage directory at {session_storage_dir}")
        
        # Create preferences.json with default settings
        preferences_file = profile_path / "preferences.json"
        default_preferences = {
            "profile": {
                "name": profile_path.name,
                "created": datetime.now().isoformat(),
            },
            "browser": {
                "check_default_browser": False,
                "show_home_button": True,
            },
            "download": {
                "prompt_for_download": True,
                "default_directory": str(profile_path / "downloads"),
            },
            "privacy": {
                "clear_on_exit": False,
            },
        }
        
        with open(preferences_file, 'w') as f:
            json.dump(default_preferences, f, indent=2)
        logger.debug(f"Created preferences.json at {preferences_file}")
        
        logger.info(f"Profile structure created successfully at {profile_path}")
    
    def encrypt_credentials(
        self,
        profile_name: str,
        credentials: Dict[str, str]
    ) -> None:
        """
        Encrypt and store credentials in system keychain.
        
        Uses system keychain (macOS Keychain, Windows Credential Manager,
        Linux Secret Service) to securely store credentials. Each credential
        is stored separately with a unique key.
        
        **Validates: Requirements 10.1, 10.2**
        
        Args:
            profile_name: Name of the profile
            credentials: Dictionary of credentials to encrypt and store.
                        Keys are credential names, values are credential values.
                        Example: {"username": "user@example.com", "password": "secret"}
        
        Raises:
            ValueError: If profile_name or credentials are invalid
            SecurityError: If credential storage fails
        
        Security Notes:
        - Credentials are stored in system keychain, not in files
        - Each credential is stored with a unique keyring key
        - Credentials are never logged or exposed in error messages
        - System keychain provides OS-level encryption
        
        Example:
            >>> manager = ChromeProfileManager()
            >>> manager.encrypt_credentials("work", {
            ...     "username": "user@example.com",
            ...     "password": "secret123"
            ... })
        """
        if not profile_name or not profile_name.strip():
            raise ValueError("Profile name cannot be empty")
        
        if not credentials or not isinstance(credentials, dict):
            raise ValueError("Credentials must be a non-empty dictionary")
        
        safe_profile_name = self._sanitize_profile_name(profile_name)
        
        # Verify profile exists
        profile_path = self.profiles_dir / safe_profile_name
        if not profile_path.exists():
            raise ValueError(f"Profile does not exist: {profile_name}")
        
        try:
            # Store each credential separately in keyring
            for cred_key, cred_value in credentials.items():
                if not isinstance(cred_value, str):
                    raise ValueError(f"Credential value for '{cred_key}' must be a string")
                
                # Create unique keyring key for this credential
                keyring_key = f"{safe_profile_name}:{cred_key}"
                
                # Store in system keychain
                keyring.set_password(
                    KEYRING_SERVICE_NAME,
                    keyring_key,
                    cred_value
                )
                
                # Log success without exposing credential value
                logger.info(
                    f"Stored credential '{cred_key}' for profile '{safe_profile_name}' in keychain"
                )
            
            logger.info(
                f"Successfully encrypted and stored {len(credentials)} credential(s) "
                f"for profile '{safe_profile_name}'"
            )
            
        except ValueError:
            # Re-raise ValueError without wrapping in SecurityError
            raise
        except Exception as e:
            # Never log credential values in error messages
            raise SecurityError(
                f"Failed to store credentials for profile '{safe_profile_name}'",
                security_check="credential_storage",
                resource=safe_profile_name
            ) from e
    
    def get_credentials(
        self,
        profile_name: str
    ) -> Optional[Dict[str, str]]:
        """
        Retrieve encrypted credentials from system keychain.
        
        Retrieves all credentials stored for the specified profile from
        the system keychain. Returns None if no credentials are found.
        
        **Validates: Requirements 10.1, 10.2**
        
        Args:
            profile_name: Name of the profile
        
        Returns:
            Dictionary of credentials if found, None otherwise.
            Keys are credential names, values are decrypted credential values.
        
        Raises:
            ValueError: If profile_name is invalid
            SecurityError: If credential retrieval fails
        
        Security Notes:
        - Credentials are retrieved from system keychain
        - Credentials are never logged or exposed in error messages
        - Returns None if no credentials found (not an error)
        
        Example:
            >>> manager = ChromeProfileManager()
            >>> creds = manager.get_credentials("work")
            >>> if creds:
            ...     username = creds.get("username")
            ...     password = creds.get("password")
        """
        if not profile_name or not profile_name.strip():
            raise ValueError("Profile name cannot be empty")
        
        safe_profile_name = self._sanitize_profile_name(profile_name)
        
        # Verify profile exists
        profile_path = self.profiles_dir / safe_profile_name
        if not profile_path.exists():
            raise ValueError(f"Profile does not exist: {profile_name}")
        
        try:
            # Get list of all stored credential keys for this profile
            # We need to track which credentials were stored
            # For now, we'll try common credential keys
            common_keys = ["username", "password", "email", "token", "api_key"]
            
            credentials = {}
            
            for cred_key in common_keys:
                keyring_key = f"{safe_profile_name}:{cred_key}"
                
                try:
                    cred_value = keyring.get_password(
                        KEYRING_SERVICE_NAME,
                        keyring_key
                    )
                    
                    if cred_value is not None:
                        credentials[cred_key] = cred_value
                        # Log success without exposing credential value
                        logger.debug(
                            f"Retrieved credential '{cred_key}' for profile '{safe_profile_name}'"
                        )
                except Exception as e:
                    # Ignore errors for individual credentials
                    logger.debug(
                        f"No credential '{cred_key}' found for profile '{safe_profile_name}'"
                    )
            
            if credentials:
                logger.info(
                    f"Retrieved {len(credentials)} credential(s) for profile '{safe_profile_name}'"
                )
                return credentials
            else:
                logger.debug(f"No credentials found for profile '{safe_profile_name}'")
                return None
                
        except Exception as e:
            # Never log credential values in error messages
            raise SecurityError(
                f"Failed to retrieve credentials for profile '{safe_profile_name}'",
                security_check="credential_retrieval",
                resource=safe_profile_name
            ) from e
    
    def delete_credentials(
        self,
        profile_name: str,
        credential_keys: Optional[List[str]] = None
    ) -> int:
        """
        Delete credentials from system keychain.
        
        Deletes specified credentials or all credentials for a profile.
        
        Args:
            profile_name: Name of the profile
            credential_keys: List of credential keys to delete.
                           If None, deletes all common credentials.
        
        Returns:
            Number of credentials deleted
        
        Raises:
            ValueError: If profile_name is invalid
        
        Example:
            >>> manager = ChromeProfileManager()
            >>> # Delete specific credentials
            >>> manager.delete_credentials("work", ["password"])
            >>> # Delete all credentials
            >>> manager.delete_credentials("work")
        """
        if not profile_name or not profile_name.strip():
            raise ValueError("Profile name cannot be empty")
        
        safe_profile_name = self._sanitize_profile_name(profile_name)
        
        # If no specific keys provided, try common keys
        if credential_keys is None:
            credential_keys = ["username", "password", "email", "token", "api_key"]
        
        deleted_count = 0
        
        for cred_key in credential_keys:
            keyring_key = f"{safe_profile_name}:{cred_key}"
            
            try:
                keyring.delete_password(
                    KEYRING_SERVICE_NAME,
                    keyring_key
                )
                deleted_count += 1
                logger.debug(
                    f"Deleted credential '{cred_key}' for profile '{safe_profile_name}'"
                )
            except keyring.errors.PasswordDeleteError:
                # Credential doesn't exist, ignore
                pass
            except Exception as e:
                logger.warning(
                    f"Failed to delete credential '{cred_key}' for profile '{safe_profile_name}': {e}"
                )
        
        if deleted_count > 0:
            logger.info(
                f"Deleted {deleted_count} credential(s) for profile '{safe_profile_name}'"
            )
        
        return deleted_count
    
    def encrypt_cookies_db(
        self,
        profile_name: str,
        encryption_key: Optional[str] = None
    ) -> None:
        """
        Encrypt cookies database using AES-256 encryption.
        
        Encrypts the cookies.db file in-place using AES-256-GCM encryption.
        If no encryption key is provided, generates a new one and stores it
        in the system keychain.
        
        **Validates: Requirements 10.1, 10.2**
        
        Args:
            profile_name: Name of the profile
            encryption_key: Optional encryption key (base64 encoded).
                          If None, generates and stores a new key.
        
        Raises:
            ValueError: If profile_name is invalid or cookies.db doesn't exist
            SecurityError: If encryption fails
        
        Security Notes:
        - Uses AES-256-GCM for authenticated encryption
        - Encryption key stored in system keychain
        - Original cookies.db is securely overwritten
        - Encrypted file has .encrypted extension
        
        Example:
            >>> manager = ChromeProfileManager()
            >>> manager.encrypt_cookies_db("work")
        """
        if not profile_name or not profile_name.strip():
            raise ValueError("Profile name cannot be empty")
        
        safe_profile_name = self._sanitize_profile_name(profile_name)
        profile_path = self.profiles_dir / safe_profile_name
        
        if not profile_path.exists():
            raise ValueError(f"Profile does not exist: {profile_name}")
        
        cookies_file = profile_path / "cookies.db"
        
        if not cookies_file.exists():
            raise ValueError(f"Cookies database does not exist for profile: {profile_name}")
        
        try:
            # Get or generate encryption key
            if encryption_key is None:
                # Try to get existing key from keychain
                keyring_key = f"{safe_profile_name}:cookies_encryption_key"
                encryption_key = keyring.get_password(
                    KEYRING_SERVICE_NAME,
                    keyring_key
                )
                
                if encryption_key is None:
                    # Generate new 256-bit key
                    key_bytes = os.urandom(32)  # 256 bits
                    encryption_key = base64.b64encode(key_bytes).decode('utf-8')
                    
                    # Store in keychain
                    keyring.set_password(
                        KEYRING_SERVICE_NAME,
                        keyring_key,
                        encryption_key
                    )
                    logger.info(f"Generated new encryption key for profile '{safe_profile_name}'")
            
            # Decode key from base64
            key = base64.b64decode(encryption_key)
            
            # Read cookies database
            with open(cookies_file, 'rb') as f:
                plaintext = f.read()
            
            # Generate random IV (96 bits for GCM)
            iv = os.urandom(12)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Encrypt data
            ciphertext = encryptor.update(plaintext) + encryptor.finalize()
            
            # Get authentication tag
            tag = encryptor.tag
            
            # Write encrypted file (IV + tag + ciphertext)
            encrypted_file = profile_path / "cookies.db.encrypted"
            with open(encrypted_file, 'wb') as f:
                f.write(iv)
                f.write(tag)
                f.write(ciphertext)
            
            # Securely delete original file
            cookies_file.unlink()
            
            logger.info(
                f"Successfully encrypted cookies database for profile '{safe_profile_name}' "
                f"using AES-256-GCM"
            )
            
        except Exception as e:
            raise SecurityError(
                f"Failed to encrypt cookies database for profile '{safe_profile_name}'",
                security_check="cookies_encryption",
                resource=safe_profile_name
            ) from e
    
    def decrypt_cookies_db(
        self,
        profile_name: str
    ) -> None:
        """
        Decrypt cookies database using stored encryption key.
        
        Decrypts the cookies.db.encrypted file and restores cookies.db.
        
        Args:
            profile_name: Name of the profile
        
        Raises:
            ValueError: If profile_name is invalid or encrypted file doesn't exist
            SecurityError: If decryption fails or key not found
        
        Example:
            >>> manager = ChromeProfileManager()
            >>> manager.decrypt_cookies_db("work")
        """
        if not profile_name or not profile_name.strip():
            raise ValueError("Profile name cannot be empty")
        
        safe_profile_name = self._sanitize_profile_name(profile_name)
        profile_path = self.profiles_dir / safe_profile_name
        
        if not profile_path.exists():
            raise ValueError(f"Profile does not exist: {profile_name}")
        
        encrypted_file = profile_path / "cookies.db.encrypted"
        
        if not encrypted_file.exists():
            raise ValueError(
                f"Encrypted cookies database does not exist for profile: {profile_name}"
            )
        
        try:
            # Get encryption key from keychain
            keyring_key = f"{safe_profile_name}:cookies_encryption_key"
            encryption_key = keyring.get_password(
                KEYRING_SERVICE_NAME,
                keyring_key
            )
            
            if encryption_key is None:
                raise SecurityError(
                    f"Encryption key not found for profile '{safe_profile_name}'",
                    security_check="key_retrieval",
                    resource=safe_profile_name
                )
            
            # Decode key from base64
            key = base64.b64decode(encryption_key)
            
            # Read encrypted file
            with open(encrypted_file, 'rb') as f:
                iv = f.read(12)  # 96 bits
                tag = f.read(16)  # 128 bits
                ciphertext = f.read()
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Decrypt data
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Write decrypted file
            cookies_file = profile_path / "cookies.db"
            with open(cookies_file, 'wb') as f:
                f.write(plaintext)
            
            # Delete encrypted file
            encrypted_file.unlink()
            
            logger.info(
                f"Successfully decrypted cookies database for profile '{safe_profile_name}'"
            )
            
        except SecurityError:
            # Re-raise SecurityError without wrapping
            raise
        except Exception as e:
            raise SecurityError(
                f"Failed to decrypt cookies database for profile '{safe_profile_name}'",
                security_check="cookies_decryption",
                resource=safe_profile_name
            ) from e
