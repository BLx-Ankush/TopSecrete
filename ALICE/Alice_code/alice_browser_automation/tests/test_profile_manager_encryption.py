"""
Unit tests for ChromeProfileManager credential encryption functionality.

Tests credential encryption, retrieval, and cookies database encryption
using system keychain and AES-256 encryption.

**Validates: Requirements 10.1, 10.2**
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import base64
import os

from alice_browser_automation.profile_manager import ChromeProfileManager
from alice_browser_automation.exceptions import SecurityError, ProfileError


class TestCredentialEncryption:
    """Test credential encryption and retrieval using system keychain."""
    
    @pytest.fixture
    def temp_profiles_dir(self):
        """Create temporary profiles directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def manager(self, temp_profiles_dir):
        """Create ChromeProfileManager instance with temp directory."""
        return ChromeProfileManager(profiles_dir=temp_profiles_dir)
    
    @pytest.fixture
    def test_profile(self, manager):
        """Create a test profile."""
        profile_path = manager.get_or_create_profile("test_profile")
        return "test_profile"
    
    def test_encrypt_credentials_success(self, manager, test_profile):
        """Test successful credential encryption and storage."""
        credentials = {
            "username": "test_user@example.com",
            "password": "secure_password_123"
        }
        
        with patch('keyring.set_password') as mock_set:
            manager.encrypt_credentials(test_profile, credentials)
            
            # Verify keyring.set_password was called for each credential
            assert mock_set.call_count == 2
            
            # Verify correct service name and keys
            calls = mock_set.call_args_list
            assert calls[0][0][0] == "alice_browser_automation"
            assert calls[0][0][1] == "test_profile:username"
            assert calls[0][0][2] == "test_user@example.com"
            
            assert calls[1][0][0] == "alice_browser_automation"
            assert calls[1][0][1] == "test_profile:password"
            assert calls[1][0][2] == "secure_password_123"
    
    def test_encrypt_credentials_empty_profile_name(self, manager):
        """Test that empty profile name raises ValueError."""
        with pytest.raises(ValueError, match="Profile name cannot be empty"):
            manager.encrypt_credentials("", {"username": "test"})
    
    def test_encrypt_credentials_invalid_credentials(self, manager, test_profile):
        """Test that invalid credentials raise ValueError."""
        # Empty credentials
        with pytest.raises(ValueError, match="Credentials must be a non-empty dictionary"):
            manager.encrypt_credentials(test_profile, {})
        
        # Non-dict credentials
        with pytest.raises(ValueError, match="Credentials must be a non-empty dictionary"):
            manager.encrypt_credentials(test_profile, None)
    
    def test_encrypt_credentials_non_string_value(self, manager, test_profile):
        """Test that non-string credential values raise ValueError."""
        credentials = {
            "username": "test_user",
            "age": 25  # Invalid: not a string
        }
        
        with patch('keyring.set_password'):
            with pytest.raises(ValueError, match="Credential value for 'age' must be a string"):
                manager.encrypt_credentials(test_profile, credentials)
    
    def test_encrypt_credentials_nonexistent_profile(self, manager):
        """Test that encrypting credentials for non-existent profile raises ValueError."""
        with pytest.raises(ValueError, match="Profile does not exist"):
            manager.encrypt_credentials("nonexistent_profile", {"username": "test"})
    
    def test_encrypt_credentials_keyring_failure(self, manager, test_profile):
        """Test that keyring failure raises SecurityError."""
        credentials = {"username": "test_user"}
        
        with patch('keyring.set_password', side_effect=Exception("Keyring error")):
            with pytest.raises(SecurityError, match="Failed to store credentials"):
                manager.encrypt_credentials(test_profile, credentials)
    
    def test_get_credentials_success(self, manager, test_profile):
        """Test successful credential retrieval."""
        # Mock keyring to return stored credentials
        def mock_get_password(service, key):
            if key == "test_profile:username":
                return "test_user@example.com"
            elif key == "test_profile:password":
                return "secure_password_123"
            return None
        
        with patch('keyring.get_password', side_effect=mock_get_password):
            credentials = manager.get_credentials(test_profile)
            
            assert credentials is not None
            assert credentials["username"] == "test_user@example.com"
            assert credentials["password"] == "secure_password_123"
    
    def test_get_credentials_no_credentials_found(self, manager, test_profile):
        """Test that get_credentials returns None when no credentials found."""
        with patch('keyring.get_password', return_value=None):
            credentials = manager.get_credentials(test_profile)
            assert credentials is None
    
    def test_get_credentials_empty_profile_name(self, manager):
        """Test that empty profile name raises ValueError."""
        with pytest.raises(ValueError, match="Profile name cannot be empty"):
            manager.get_credentials("")
    
    def test_get_credentials_nonexistent_profile(self, manager):
        """Test that getting credentials for non-existent profile raises ValueError."""
        with pytest.raises(ValueError, match="Profile does not exist"):
            manager.get_credentials("nonexistent_profile")
    
    def test_get_credentials_partial_retrieval(self, manager, test_profile):
        """Test that partial credential retrieval works correctly."""
        # Mock keyring to return only some credentials
        def mock_get_password(service, key):
            if key == "test_profile:username":
                return "test_user@example.com"
            # Other credentials return None
            return None
        
        with patch('keyring.get_password', side_effect=mock_get_password):
            credentials = manager.get_credentials(test_profile)
            
            assert credentials is not None
            assert "username" in credentials
            assert credentials["username"] == "test_user@example.com"
            assert "password" not in credentials
    
    def test_delete_credentials_success(self, manager, test_profile):
        """Test successful credential deletion."""
        with patch('keyring.delete_password') as mock_delete:
            deleted_count = manager.delete_credentials(test_profile, ["username", "password"])
            
            assert deleted_count == 2
            assert mock_delete.call_count == 2
    
    def test_delete_credentials_all(self, manager, test_profile):
        """Test deleting all credentials when no keys specified."""
        with patch('keyring.delete_password') as mock_delete:
            deleted_count = manager.delete_credentials(test_profile)
            
            # Should try to delete all common keys
            assert mock_delete.call_count == 5  # username, password, email, token, api_key
    
    def test_delete_credentials_nonexistent(self, manager, test_profile):
        """Test that deleting non-existent credentials doesn't raise error."""
        import keyring.errors
        
        with patch('keyring.delete_password', side_effect=keyring.errors.PasswordDeleteError()):
            # Should not raise error, just return 0
            deleted_count = manager.delete_credentials(test_profile, ["nonexistent"])
            assert deleted_count == 0
    
    def test_credentials_not_logged(self, manager, test_profile, caplog):
        """Test that credential values are never logged."""
        import logging
        caplog.set_level(logging.INFO)
        
        credentials = {
            "username": "secret_user",
            "password": "super_secret_password"
        }
        
        with patch('keyring.set_password'):
            manager.encrypt_credentials(test_profile, credentials)
        
        # Check that credential values don't appear in logs
        log_text = caplog.text
        assert "secret_user" not in log_text
        assert "super_secret_password" not in log_text
        
        # But credential keys should be logged
        assert "username" in log_text
        assert "password" in log_text


class TestCookiesDatabaseEncryption:
    """Test cookies database encryption using AES-256."""
    
    @pytest.fixture
    def temp_profiles_dir(self):
        """Create temporary profiles directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def manager(self, temp_profiles_dir):
        """Create ChromeProfileManager instance with temp directory."""
        return ChromeProfileManager(profiles_dir=temp_profiles_dir)
    
    @pytest.fixture
    def test_profile_with_cookies(self, manager):
        """Create a test profile with cookies database."""
        profile_path = manager.get_or_create_profile("test_profile")
        
        # Write some test data to cookies.db
        cookies_file = profile_path / "cookies.db"
        test_data = b"This is test cookie data that should be encrypted"
        with open(cookies_file, 'wb') as f:
            f.write(test_data)
        
        return "test_profile", test_data
    
    def test_encrypt_cookies_db_success(self, manager, test_profile_with_cookies):
        """Test successful cookies database encryption."""
        profile_name, original_data = test_profile_with_cookies
        
        # Generate a test encryption key
        test_key = base64.b64encode(os.urandom(32)).decode('utf-8')
        
        with patch('keyring.set_password') as mock_set, \
             patch('keyring.get_password', return_value=None):
            
            manager.encrypt_cookies_db(profile_name, encryption_key=test_key)
            
            # Verify original cookies.db is deleted
            profile_path = manager.profiles_dir / profile_name
            assert not (profile_path / "cookies.db").exists()
            
            # Verify encrypted file exists
            assert (profile_path / "cookies.db.encrypted").exists()
            
            # Verify encrypted file is different from original
            with open(profile_path / "cookies.db.encrypted", 'rb') as f:
                encrypted_data = f.read()
            
            assert encrypted_data != original_data
            assert len(encrypted_data) > len(original_data)  # IV + tag + ciphertext
    
    def test_encrypt_cookies_db_generates_key(self, manager, test_profile_with_cookies):
        """Test that encryption generates and stores key if not provided."""
        profile_name, _ = test_profile_with_cookies
        
        with patch('keyring.set_password') as mock_set, \
             patch('keyring.get_password', return_value=None):
            
            manager.encrypt_cookies_db(profile_name)
            
            # Verify key was stored in keychain
            mock_set.assert_called_once()
            call_args = mock_set.call_args[0]
            assert call_args[0] == "alice_browser_automation"
            assert call_args[1] == "test_profile:cookies_encryption_key"
            # Verify key is base64 encoded
            assert isinstance(call_args[2], str)
            base64.b64decode(call_args[2])  # Should not raise
    
    def test_encrypt_cookies_db_nonexistent_profile(self, manager):
        """Test that encrypting cookies for non-existent profile raises ValueError."""
        with pytest.raises(ValueError, match="Profile does not exist"):
            manager.encrypt_cookies_db("nonexistent_profile")
    
    def test_encrypt_cookies_db_no_cookies_file(self, manager):
        """Test that encrypting non-existent cookies.db raises ValueError."""
        profile_path = manager.get_or_create_profile("test_profile")
        
        # Delete cookies.db
        (profile_path / "cookies.db").unlink()
        
        with pytest.raises(ValueError, match="Cookies database does not exist"):
            manager.encrypt_cookies_db("test_profile")
    
    def test_decrypt_cookies_db_success(self, manager, test_profile_with_cookies):
        """Test successful cookies database decryption."""
        profile_name, original_data = test_profile_with_cookies
        
        # First encrypt
        test_key = base64.b64encode(os.urandom(32)).decode('utf-8')
        
        with patch('keyring.set_password'), \
             patch('keyring.get_password', return_value=None):
            manager.encrypt_cookies_db(profile_name, encryption_key=test_key)
        
        # Then decrypt
        with patch('keyring.get_password', return_value=test_key):
            manager.decrypt_cookies_db(profile_name)
        
        # Verify original cookies.db is restored
        profile_path = manager.profiles_dir / profile_name
        assert (profile_path / "cookies.db").exists()
        assert not (profile_path / "cookies.db.encrypted").exists()
        
        # Verify decrypted data matches original
        with open(profile_path / "cookies.db", 'rb') as f:
            decrypted_data = f.read()
        
        assert decrypted_data == original_data
    
    def test_decrypt_cookies_db_no_key(self, manager, test_profile_with_cookies):
        """Test that decryption without key raises SecurityError."""
        profile_name, _ = test_profile_with_cookies
        
        # First encrypt
        test_key = base64.b64encode(os.urandom(32)).decode('utf-8')
        
        with patch('keyring.set_password'), \
             patch('keyring.get_password', return_value=None):
            manager.encrypt_cookies_db(profile_name, encryption_key=test_key)
        
        # Try to decrypt without key
        with patch('keyring.get_password', return_value=None):
            with pytest.raises(SecurityError, match="Encryption key not found"):
                manager.decrypt_cookies_db(profile_name)
    
    def test_decrypt_cookies_db_wrong_key(self, manager, test_profile_with_cookies):
        """Test that decryption with wrong key raises SecurityError."""
        profile_name, _ = test_profile_with_cookies
        
        # Encrypt with one key
        test_key1 = base64.b64encode(os.urandom(32)).decode('utf-8')
        
        with patch('keyring.set_password'), \
             patch('keyring.get_password', return_value=None):
            manager.encrypt_cookies_db(profile_name, encryption_key=test_key1)
        
        # Try to decrypt with different key
        test_key2 = base64.b64encode(os.urandom(32)).decode('utf-8')
        
        with patch('keyring.get_password', return_value=test_key2):
            with pytest.raises(SecurityError, match="Failed to decrypt cookies database"):
                manager.decrypt_cookies_db(profile_name)
    
    def test_decrypt_cookies_db_nonexistent_encrypted_file(self, manager):
        """Test that decrypting non-existent encrypted file raises ValueError."""
        profile_path = manager.get_or_create_profile("test_profile")
        
        with pytest.raises(ValueError, match="Encrypted cookies database does not exist"):
            manager.decrypt_cookies_db("test_profile")


class TestProfileDeletionWithCredentials:
    """Test that profile deletion also deletes credentials."""
    
    @pytest.fixture
    def temp_profiles_dir(self):
        """Create temporary profiles directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def manager(self, temp_profiles_dir):
        """Create ChromeProfileManager instance with temp directory."""
        return ChromeProfileManager(profiles_dir=temp_profiles_dir)
    
    def test_delete_profile_deletes_credentials(self, manager):
        """Test that deleting profile also deletes credentials from keychain."""
        # Create profile
        profile_path = manager.get_or_create_profile("test_profile")
        
        with patch('keyring.delete_password') as mock_delete:
            manager.delete_profile("test_profile")
            
            # Verify credentials were deleted
            assert mock_delete.call_count >= 1
    
    def test_delete_profile_continues_on_credential_error(self, manager, caplog):
        """Test that profile deletion continues even if credential deletion fails."""
        import logging
        caplog.set_level(logging.WARNING)
        
        # Create profile
        profile_path = manager.get_or_create_profile("test_profile")
        
        with patch('keyring.delete_password', side_effect=Exception("Keyring error")):
            # Should not raise, just log warning
            result = manager.delete_profile("test_profile")
            
            assert result is True
            assert "Failed to delete credential" in caplog.text


class TestSecurityRequirements:
    """Test that security requirements are met."""
    
    @pytest.fixture
    def temp_profiles_dir(self):
        """Create temporary profiles directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def manager(self, temp_profiles_dir):
        """Create ChromeProfileManager instance with temp directory."""
        return ChromeProfileManager(profiles_dir=temp_profiles_dir)
    
    def test_credentials_never_in_error_messages(self, manager):
        """Test that credentials never appear in error messages."""
        profile_path = manager.get_or_create_profile("test_profile")
        
        credentials = {
            "password": "super_secret_password_12345"
        }
        
        with patch('keyring.set_password', side_effect=Exception("Storage failed")):
            try:
                manager.encrypt_credentials("test_profile", credentials)
            except SecurityError as e:
                # Verify password doesn't appear in error message
                assert "super_secret_password_12345" not in str(e)
                assert "password" not in str(e)  # Even key shouldn't be in error
    
    def test_aes_256_encryption_used(self, manager):
        """Test that AES-256 encryption is used for cookies database."""
        profile_path = manager.get_or_create_profile("test_profile")
        
        # Create cookies.db
        cookies_file = profile_path / "cookies.db"
        with open(cookies_file, 'wb') as f:
            f.write(b"test data")
        
        # Encrypt with known key
        test_key = base64.b64encode(os.urandom(32)).decode('utf-8')  # 256 bits
        
        with patch('keyring.set_password'), \
             patch('keyring.get_password', return_value=None):
            manager.encrypt_cookies_db("test_profile", encryption_key=test_key)
        
        # Verify key is 256 bits (32 bytes)
        key_bytes = base64.b64decode(test_key)
        assert len(key_bytes) == 32  # 256 bits / 8 = 32 bytes
    
    def test_system_keychain_used(self, manager):
        """Test that system keychain is used for credential storage."""
        profile_path = manager.get_or_create_profile("test_profile")
        
        credentials = {"username": "test"}
        
        with patch('keyring.set_password') as mock_set:
            manager.encrypt_credentials("test_profile", credentials)
            
            # Verify keyring module was used
            mock_set.assert_called()
            
            # Verify correct service name
            call_args = mock_set.call_args[0]
            assert call_args[0] == "alice_browser_automation"
