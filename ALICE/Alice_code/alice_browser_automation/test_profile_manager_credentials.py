"""
Unit tests for ChromeProfileManager credential encryption functionality.

Tests credential encryption, retrieval, and deletion using system keychain.

**Validates: Requirements 10.1, 10.2**
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import keyring

from alice_browser_automation.profile_manager import ChromeProfileManager, KEYRING_SERVICE_NAME
from alice_browser_automation.exceptions import SecurityError


class TestCredentialEncryption:
    """Test credential encryption and storage in system keychain."""
    
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
        profile_name = "test_profile"
        manager.get_or_create_profile(profile_name)
        yield profile_name
        # Cleanup: delete all credentials after test
        try:
            manager.delete_credentials(profile_name)
        except:
            pass
    
    def test_encrypt_credentials_success(self, manager, test_profile):
        """Test successful credential encryption and storage."""
        credentials = {
            "username": "test_user@example.com",
            "password": "secure_password_123",
            "api_key": "sk-test-key-12345"
        }
        
        # Encrypt and store credentials
        manager.encrypt_credentials(test_profile, credentials)
        
        # Verify credentials were stored in keychain
        for cred_key, cred_value in credentials.items():
            keyring_key = f"{test_profile}:{cred_key}"
            stored_value = keyring.get_password(
                KEYRING_SERVICE_NAME,
                keyring_key
            )
            assert stored_value == cred_value, f"Credential '{cred_key}' not stored correctly"
    
    def test_encrypt_credentials_empty_profile_name(self, manager):
        """Test that empty profile name raises ValueError."""
        with pytest.raises(ValueError, match="Profile name cannot be empty"):
            manager.encrypt_credentials("", {"username": "test"})
        
        with pytest.raises(ValueError, match="Profile name cannot be empty"):
            manager.encrypt_credentials("   ", {"username": "test"})
    
    def test_encrypt_credentials_invalid_credentials(self, manager, test_profile):
        """Test that invalid credentials raise ValueError."""
        # Empty credentials
        with pytest.raises(ValueError, match="Credentials must be a non-empty dictionary"):
            manager.encrypt_credentials(test_profile, {})
        
        # None credentials
        with pytest.raises(ValueError, match="Credentials must be a non-empty dictionary"):
            manager.encrypt_credentials(test_profile, None)
        
        # Non-dict credentials
        with pytest.raises(ValueError, match="Credentials must be a non-empty dictionary"):
            manager.encrypt_credentials(test_profile, "not a dict")
    
    def test_encrypt_credentials_non_string_value(self, manager, test_profile):
        """Test that non-string credential values raise ValueError."""
        credentials = {
            "username": "test_user",
            "password": 12345  # Invalid: not a string
        }
        
        with pytest.raises(ValueError, match="Credential value for 'password' must be a string"):
            manager.encrypt_credentials(test_profile, credentials)
    
    def test_encrypt_credentials_nonexistent_profile(self, manager):
        """Test that encrypting credentials for non-existent profile raises ValueError."""
        with pytest.raises(ValueError, match="Profile does not exist"):
            manager.encrypt_credentials("nonexistent_profile", {"username": "test"})
    
    def test_encrypt_credentials_no_logging_of_values(self, manager, test_profile, caplog):
        """Test that credential values are never logged."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        credentials = {
            "password": "super_secret_password_123",
            "api_key": "sk-secret-key-xyz"
        }
        
        manager.encrypt_credentials(test_profile, credentials)
        
        # Check that credential values are not in any log messages
        log_text = caplog.text
        assert "super_secret_password_123" not in log_text
        assert "sk-secret-key-xyz" not in log_text
        
        # But credential keys should be mentioned
        assert "password" in log_text
        assert "api_key" in log_text
    
    def test_get_credentials_success(self, manager, test_profile):
        """Test successful credential retrieval."""
        original_credentials = {
            "username": "test_user@example.com",
            "password": "secure_password_123",
            "email": "user@example.com"
        }
        
        # Store credentials
        manager.encrypt_credentials(test_profile, original_credentials)
        
        # Retrieve credentials
        retrieved_credentials = manager.get_credentials(test_profile)
        
        assert retrieved_credentials is not None
        assert retrieved_credentials == original_credentials
    
    def test_get_credentials_no_credentials_stored(self, manager, test_profile):
        """Test that get_credentials returns None when no credentials exist."""
        credentials = manager.get_credentials(test_profile)
        assert credentials is None
    
    def test_get_credentials_partial_credentials(self, manager, test_profile):
        """Test retrieving only some of the common credential keys."""
        # Store only username
        manager.encrypt_credentials(test_profile, {"username": "test_user"})
        
        # Retrieve credentials
        credentials = manager.get_credentials(test_profile)
        
        assert credentials is not None
        assert "username" in credentials
        assert credentials["username"] == "test_user"
        # Other keys should not be present
        assert "password" not in credentials
        assert "email" not in credentials
    
    def test_get_credentials_empty_profile_name(self, manager):
        """Test that empty profile name raises ValueError."""
        with pytest.raises(ValueError, match="Profile name cannot be empty"):
            manager.get_credentials("")
    
    def test_get_credentials_nonexistent_profile(self, manager):
        """Test that getting credentials for non-existent profile raises ValueError."""
        with pytest.raises(ValueError, match="Profile does not exist"):
            manager.get_credentials("nonexistent_profile")
    
    def test_get_credentials_no_logging_of_values(self, manager, test_profile, caplog):
        """Test that retrieved credential values are never logged."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        credentials = {
            "password": "super_secret_password_456",
            "token": "secret_token_xyz"
        }
        
        manager.encrypt_credentials(test_profile, credentials)
        
        # Clear logs
        caplog.clear()
        
        # Retrieve credentials
        retrieved = manager.get_credentials(test_profile)
        
        # Check that credential values are not in any log messages
        log_text = caplog.text
        assert "super_secret_password_456" not in log_text
        assert "secret_token_xyz" not in log_text
    
    def test_delete_credentials_specific_keys(self, manager, test_profile):
        """Test deleting specific credential keys."""
        credentials = {
            "username": "test_user",
            "password": "test_password",
            "email": "test@example.com"
        }
        
        # Store credentials
        manager.encrypt_credentials(test_profile, credentials)
        
        # Delete only password
        deleted_count = manager.delete_credentials(test_profile, ["password"])
        assert deleted_count == 1
        
        # Verify password is deleted but others remain
        retrieved = manager.get_credentials(test_profile)
        assert "username" in retrieved
        assert "email" in retrieved
        assert "password" not in retrieved
    
    def test_delete_credentials_all(self, manager, test_profile):
        """Test deleting all credentials."""
        credentials = {
            "username": "test_user",
            "password": "test_password"
        }
        
        # Store credentials
        manager.encrypt_credentials(test_profile, credentials)
        
        # Delete all credentials (no keys specified)
        deleted_count = manager.delete_credentials(test_profile)
        assert deleted_count >= 2  # At least username and password
        
        # Verify all credentials are deleted
        retrieved = manager.get_credentials(test_profile)
        assert retrieved is None
    
    def test_delete_credentials_nonexistent(self, manager, test_profile):
        """Test deleting non-existent credentials doesn't raise error."""
        # Delete credentials that don't exist
        deleted_count = manager.delete_credentials(test_profile, ["nonexistent_key"])
        assert deleted_count == 0
    
    def test_delete_credentials_empty_profile_name(self, manager):
        """Test that empty profile name raises ValueError."""
        with pytest.raises(ValueError, match="Profile name cannot be empty"):
            manager.delete_credentials("")
    
    def test_credential_isolation_between_profiles(self, manager):
        """Test that credentials are isolated between different profiles."""
        profile1 = "profile1"
        profile2 = "profile2"
        
        # Create both profiles
        manager.get_or_create_profile(profile1)
        manager.get_or_create_profile(profile2)
        
        # Store different credentials for each profile
        manager.encrypt_credentials(profile1, {"username": "user1", "password": "pass1"})
        manager.encrypt_credentials(profile2, {"username": "user2", "password": "pass2"})
        
        # Retrieve and verify isolation
        creds1 = manager.get_credentials(profile1)
        creds2 = manager.get_credentials(profile2)
        
        assert creds1["username"] == "user1"
        assert creds1["password"] == "pass1"
        assert creds2["username"] == "user2"
        assert creds2["password"] == "pass2"
    
    def test_delete_profile_removes_credentials(self, manager, test_profile):
        """Test that deleting a profile also removes its credentials."""
        credentials = {
            "username": "test_user",
            "password": "test_password"
        }
        
        # Store credentials
        manager.encrypt_credentials(test_profile, credentials)
        
        # Verify credentials exist
        assert manager.get_credentials(test_profile) is not None
        
        # Delete profile
        manager.delete_profile(test_profile)
        
        # Verify credentials are deleted from keychain
        # (We can't call get_credentials because profile doesn't exist)
        keyring_key = f"{test_profile}:username"
        stored_value = keyring.get_password(KEYRING_SERVICE_NAME, keyring_key)
        assert stored_value is None


class TestCookiesEncryption:
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
        """Create a test profile with sample cookies data."""
        profile_name = "test_profile"
        profile_path = manager.get_or_create_profile(profile_name)
        
        # Write sample cookies data
        cookies_file = profile_path / "cookies.db"
        sample_data = b"Sample cookies database content with sensitive data"
        with open(cookies_file, 'wb') as f:
            f.write(sample_data)
        
        return profile_name, sample_data
    
    def test_encrypt_cookies_db_success(self, manager, test_profile_with_cookies):
        """Test successful cookies database encryption."""
        profile_name, original_data = test_profile_with_cookies
        profile_path = manager.profiles_dir / profile_name
        
        # Encrypt cookies
        manager.encrypt_cookies_db(profile_name)
        
        # Verify original file is deleted
        assert not (profile_path / "cookies.db").exists()
        
        # Verify encrypted file exists
        assert (profile_path / "cookies.db.encrypted").exists()
        
        # Verify encryption key is stored in keychain
        keyring_key = f"{profile_name}:cookies_encryption_key"
        encryption_key = keyring.get_password(KEYRING_SERVICE_NAME, keyring_key)
        assert encryption_key is not None
    
    def test_encrypt_cookies_db_empty_profile_name(self, manager):
        """Test that empty profile name raises ValueError."""
        with pytest.raises(ValueError, match="Profile name cannot be empty"):
            manager.encrypt_cookies_db("")
    
    def test_encrypt_cookies_db_nonexistent_profile(self, manager):
        """Test that encrypting cookies for non-existent profile raises ValueError."""
        with pytest.raises(ValueError, match="Profile does not exist"):
            manager.encrypt_cookies_db("nonexistent_profile")
    
    def test_encrypt_cookies_db_no_cookies_file(self, manager):
        """Test that encrypting when cookies.db doesn't exist raises ValueError."""
        profile_name = "test_profile"
        profile_path = manager.get_or_create_profile(profile_name)
        
        # Delete cookies.db
        (profile_path / "cookies.db").unlink()
        
        with pytest.raises(ValueError, match="Cookies database does not exist"):
            manager.encrypt_cookies_db(profile_name)
    
    def test_decrypt_cookies_db_success(self, manager, test_profile_with_cookies):
        """Test successful cookies database decryption."""
        profile_name, original_data = test_profile_with_cookies
        profile_path = manager.profiles_dir / profile_name
        
        # Encrypt cookies
        manager.encrypt_cookies_db(profile_name)
        
        # Decrypt cookies
        manager.decrypt_cookies_db(profile_name)
        
        # Verify encrypted file is deleted
        assert not (profile_path / "cookies.db.encrypted").exists()
        
        # Verify decrypted file exists
        assert (profile_path / "cookies.db").exists()
        
        # Verify decrypted content matches original
        with open(profile_path / "cookies.db", 'rb') as f:
            decrypted_data = f.read()
        assert decrypted_data == original_data
    
    def test_decrypt_cookies_db_empty_profile_name(self, manager):
        """Test that empty profile name raises ValueError."""
        with pytest.raises(ValueError, match="Profile name cannot be empty"):
            manager.decrypt_cookies_db("")
    
    def test_decrypt_cookies_db_nonexistent_profile(self, manager):
        """Test that decrypting cookies for non-existent profile raises ValueError."""
        with pytest.raises(ValueError, match="Profile does not exist"):
            manager.decrypt_cookies_db("nonexistent_profile")
    
    def test_decrypt_cookies_db_no_encrypted_file(self, manager):
        """Test that decrypting when encrypted file doesn't exist raises ValueError."""
        profile_name = "test_profile"
        manager.get_or_create_profile(profile_name)
        
        with pytest.raises(ValueError, match="Encrypted cookies database does not exist"):
            manager.decrypt_cookies_db(profile_name)
    
    def test_decrypt_cookies_db_no_encryption_key(self, manager, test_profile_with_cookies):
        """Test that decrypting without encryption key raises SecurityError."""
        profile_name, _ = test_profile_with_cookies
        profile_path = manager.profiles_dir / profile_name
        
        # Encrypt cookies
        manager.encrypt_cookies_db(profile_name)
        
        # Delete encryption key from keychain
        keyring_key = f"{profile_name}:cookies_encryption_key"
        try:
            keyring.delete_password(KEYRING_SERVICE_NAME, keyring_key)
        except:
            pass
        
        # Try to decrypt without key
        with pytest.raises(SecurityError, match="Encryption key not found"):
            manager.decrypt_cookies_db(profile_name)
    
    def test_encrypt_decrypt_roundtrip_preserves_data(self, manager, test_profile_with_cookies):
        """Test that encrypt-decrypt roundtrip preserves original data."""
        profile_name, original_data = test_profile_with_cookies
        profile_path = manager.profiles_dir / profile_name
        
        # Encrypt
        manager.encrypt_cookies_db(profile_name)
        
        # Decrypt
        manager.decrypt_cookies_db(profile_name)
        
        # Verify data is preserved
        with open(profile_path / "cookies.db", 'rb') as f:
            final_data = f.read()
        assert final_data == original_data
    
    def test_encrypt_cookies_db_uses_aes_256(self, manager, test_profile_with_cookies):
        """Test that encryption uses AES-256 (32-byte key)."""
        profile_name, _ = test_profile_with_cookies
        
        # Encrypt cookies
        manager.encrypt_cookies_db(profile_name)
        
        # Get encryption key from keychain
        keyring_key = f"{profile_name}:cookies_encryption_key"
        encryption_key = keyring.get_password(KEYRING_SERVICE_NAME, keyring_key)
        
        # Decode and verify key length
        import base64
        key_bytes = base64.b64decode(encryption_key)
        assert len(key_bytes) == 32, "Encryption key should be 256 bits (32 bytes)"
    
    def test_encrypted_file_format(self, manager, test_profile_with_cookies):
        """Test that encrypted file has correct format (IV + tag + ciphertext)."""
        profile_name, original_data = test_profile_with_cookies
        profile_path = manager.profiles_dir / profile_name
        
        # Encrypt cookies
        manager.encrypt_cookies_db(profile_name)
        
        # Read encrypted file
        encrypted_file = profile_path / "cookies.db.encrypted"
        with open(encrypted_file, 'rb') as f:
            encrypted_data = f.read()
        
        # Verify format: IV (12 bytes) + tag (16 bytes) + ciphertext
        assert len(encrypted_data) >= 28, "Encrypted file should have at least IV + tag"
        
        # IV should be 12 bytes for GCM
        iv = encrypted_data[:12]
        assert len(iv) == 12
        
        # Tag should be 16 bytes
        tag = encrypted_data[12:28]
        assert len(tag) == 16
        
        # Ciphertext should be at least as long as original data
        ciphertext = encrypted_data[28:]
        assert len(ciphertext) >= len(original_data)


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
    
    def test_credentials_never_logged(self, manager, caplog):
        """Test that credential values are never logged (Requirement 10.2)."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        profile_name = "test_profile"
        manager.get_or_create_profile(profile_name)
        
        sensitive_credentials = {
            "password": "super_secret_password_xyz",
            "api_key": "sk-secret-api-key-123",
            "token": "bearer_token_abc"
        }
        
        # Store credentials
        manager.encrypt_credentials(profile_name, sensitive_credentials)
        
        # Retrieve credentials
        manager.get_credentials(profile_name)
        
        # Delete credentials
        manager.delete_credentials(profile_name)
        
        # Check that no sensitive values appear in logs
        log_text = caplog.text
        for value in sensitive_credentials.values():
            assert value not in log_text, f"Sensitive value '{value}' found in logs!"
    
    def test_credentials_stored_in_system_keychain(self, manager):
        """Test that credentials are stored in system keychain (Requirement 10.1)."""
        profile_name = "test_profile"
        manager.get_or_create_profile(profile_name)
        
        credentials = {"username": "test_user", "password": "test_pass"}
        manager.encrypt_credentials(profile_name, credentials)
        
        # Verify credentials are in system keychain (not in files)
        profile_path = manager.profiles_dir / profile_name
        
        # Check that no credential files exist
        for file in profile_path.rglob('*'):
            if file.is_file():
                with open(file, 'rb') as f:
                    content = f.read()
                    # Credentials should not be in any file
                    assert b"test_pass" not in content
    
    def test_encryption_key_stored_in_keychain(self, manager):
        """Test that encryption keys are stored in keychain, not files."""
        profile_name = "test_profile"
        profile_path = manager.get_or_create_profile(profile_name)
        
        # Create sample cookies
        cookies_file = profile_path / "cookies.db"
        with open(cookies_file, 'wb') as f:
            f.write(b"sample cookies")
        
        # Encrypt cookies
        manager.encrypt_cookies_db(profile_name)
        
        # Verify encryption key is in keychain
        keyring_key = f"{profile_name}:cookies_encryption_key"
        encryption_key = keyring.get_password(KEYRING_SERVICE_NAME, keyring_key)
        assert encryption_key is not None
        
        # Verify key is not in any file
        for file in profile_path.rglob('*'):
            if file.is_file():
                with open(file, 'rb') as f:
                    content = f.read()
                    # Encryption key should not be in any file
                    assert encryption_key.encode() not in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
