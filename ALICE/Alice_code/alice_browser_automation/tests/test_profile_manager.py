"""
Unit tests for ChromeProfileManager.

Tests profile creation, listing, deletion, and security features.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime

from alice_browser_automation.profile_manager import ChromeProfileManager
from alice_browser_automation.exceptions import ProfileError, SecurityError


class TestChromeProfileManagerInit:
    """Test ChromeProfileManager initialization"""
    
    def test_init_creates_profiles_directory(self, tmp_path):
        """Test that initialization creates the profiles directory"""
        profiles_dir = tmp_path / "profiles"
        manager = ChromeProfileManager(profiles_dir=str(profiles_dir))
        
        assert profiles_dir.exists()
        assert profiles_dir.is_dir()
        assert manager.profiles_dir == profiles_dir
    
    def test_init_with_existing_directory(self, tmp_path):
        """Test initialization with existing profiles directory"""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        
        manager = ChromeProfileManager(profiles_dir=str(profiles_dir))
        
        assert profiles_dir.exists()
        assert manager.profiles_dir == profiles_dir
    
    def test_init_expands_tilde(self, tmp_path, monkeypatch):
        """Test that ~ is expanded to home directory"""
        # Mock Path.expanduser to return tmp_path
        original_expanduser = Path.expanduser
        
        def mock_expanduser(self):
            if str(self).startswith("~"):
                return tmp_path / str(self)[2:]
            return original_expanduser(self)
        
        monkeypatch.setattr(Path, "expanduser", mock_expanduser)
        
        manager = ChromeProfileManager(profiles_dir="~/test_profiles")
        
        assert manager.profiles_dir == tmp_path / "test_profiles"


class TestGetOrCreateProfile:
    """Test get_or_create_profile method"""
    
    def test_create_new_profile(self, tmp_path):
        """Test creating a new profile"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        profile_path = manager.get_or_create_profile("test_profile")
        
        assert profile_path.exists()
        assert profile_path.is_dir()
        assert profile_path.name == "test_profile"
        
        # Check profile structure
        assert (profile_path / "cookies.db").exists()
        assert (profile_path / "local_storage").exists()
        assert (profile_path / "local_storage").is_dir()
        assert (profile_path / "session_storage").exists()
        assert (profile_path / "session_storage").is_dir()
        assert (profile_path / "preferences.json").exists()
    
    def test_get_existing_profile(self, tmp_path):
        """Test getting an existing profile"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        # Create profile first time
        profile_path1 = manager.get_or_create_profile("existing")
        
        # Get same profile second time
        profile_path2 = manager.get_or_create_profile("existing")
        
        assert profile_path1 == profile_path2
        assert profile_path1.exists()
    
    def test_default_profile_name(self, tmp_path):
        """Test creating profile with default name"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        profile_path = manager.get_or_create_profile()
        
        assert profile_path.name == "default"
        assert profile_path.exists()
    
    def test_preferences_json_content(self, tmp_path):
        """Test that preferences.json has correct structure"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        profile_path = manager.get_or_create_profile("test")
        preferences_file = profile_path / "preferences.json"
        
        with open(preferences_file, 'r') as f:
            prefs = json.load(f)
        
        assert "profile" in prefs
        assert prefs["profile"]["name"] == "test"
        assert "created" in prefs["profile"]
        assert "browser" in prefs
        assert "download" in prefs
        assert "privacy" in prefs
    
    def test_empty_profile_name_raises_error(self, tmp_path):
        """Test that empty profile name raises ValueError"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        with pytest.raises(ValueError, match="Profile name cannot be empty"):
            manager.get_or_create_profile("")
        
        with pytest.raises(ValueError, match="Profile name cannot be empty"):
            manager.get_or_create_profile("   ")
    
    def test_profile_name_sanitization(self, tmp_path):
        """Test that profile names are sanitized"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        # Profile name with special characters should be sanitized
        profile_path = manager.get_or_create_profile("test@profile#123")
        
        # Should replace special chars with underscores
        assert profile_path.name == "test_profile_123"
        assert profile_path.exists()


class TestListProfiles:
    """Test list_profiles method"""
    
    def test_list_empty_profiles(self, tmp_path):
        """Test listing profiles when none exist"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        profiles = manager.list_profiles()
        
        assert profiles == []
    
    def test_list_single_profile(self, tmp_path):
        """Test listing a single profile"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        manager.get_or_create_profile("profile1")
        
        profiles = manager.list_profiles()
        
        assert profiles == ["profile1"]
    
    def test_list_multiple_profiles(self, tmp_path):
        """Test listing multiple profiles"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        manager.get_or_create_profile("profile1")
        manager.get_or_create_profile("profile2")
        manager.get_or_create_profile("profile3")
        
        profiles = manager.list_profiles()
        
        assert sorted(profiles) == ["profile1", "profile2", "profile3"]
    
    def test_list_profiles_sorted(self, tmp_path):
        """Test that profiles are returned in sorted order"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        manager.get_or_create_profile("zebra")
        manager.get_or_create_profile("alpha")
        manager.get_or_create_profile("beta")
        
        profiles = manager.list_profiles()
        
        assert profiles == ["alpha", "beta", "zebra"]
    
    def test_list_profiles_ignores_hidden_dirs(self, tmp_path):
        """Test that hidden directories are ignored"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        manager.get_or_create_profile("visible")
        
        # Create hidden directory
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        
        profiles = manager.list_profiles()
        
        assert profiles == ["visible"]
        assert ".hidden" not in profiles
    
    def test_list_profiles_ignores_files(self, tmp_path):
        """Test that files are ignored, only directories listed"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        manager.get_or_create_profile("profile1")
        
        # Create a file in profiles directory
        (tmp_path / "somefile.txt").touch()
        
        profiles = manager.list_profiles()
        
        assert profiles == ["profile1"]


class TestDeleteProfile:
    """Test delete_profile method"""
    
    def test_delete_existing_profile(self, tmp_path):
        """Test deleting an existing profile"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        profile_path = manager.get_or_create_profile("to_delete")
        
        assert profile_path.exists()
        
        result = manager.delete_profile("to_delete")
        
        assert result is True
        assert not profile_path.exists()
    
    def test_delete_nonexistent_profile_raises_error(self, tmp_path):
        """Test that deleting non-existent profile raises ValueError"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        with pytest.raises(ValueError, match="Profile does not exist"):
            manager.delete_profile("nonexistent")
    
    def test_delete_profile_removes_all_data(self, tmp_path):
        """Test that deletion removes all profile data"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        profile_path = manager.get_or_create_profile("test")
        
        # Add some data to profile
        (profile_path / "local_storage" / "data.txt").write_text("test data")
        (profile_path / "session_storage" / "session.txt").write_text("session data")
        
        manager.delete_profile("test")
        
        assert not profile_path.exists()
        assert not (profile_path / "local_storage" / "data.txt").exists()
    
    def test_delete_empty_profile_name_raises_error(self, tmp_path):
        """Test that empty profile name raises ValueError"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        with pytest.raises(ValueError, match="Profile name cannot be empty"):
            manager.delete_profile("")
    
    def test_delete_profile_not_in_list(self, tmp_path):
        """Test that deleted profile is removed from list"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        manager.get_or_create_profile("profile1")
        manager.get_or_create_profile("profile2")
        
        manager.delete_profile("profile1")
        
        profiles = manager.list_profiles()
        assert "profile1" not in profiles
        assert "profile2" in profiles


class TestGetProfileInfo:
    """Test get_profile_info method"""
    
    def test_get_profile_info(self, tmp_path):
        """Test getting profile information"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        profile_path = manager.get_or_create_profile("test")
        
        info = manager.get_profile_info("test")
        
        assert info["name"] == "test"
        assert info["path"] == str(profile_path)
        assert "created" in info
        assert info["size_bytes"] > 0
        assert info["has_cookies"] is True
        assert info["has_preferences"] is True
    
    def test_get_profile_info_nonexistent_raises_error(self, tmp_path):
        """Test that getting info for non-existent profile raises ValueError"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        with pytest.raises(ValueError, match="Profile does not exist"):
            manager.get_profile_info("nonexistent")
    
    def test_get_profile_info_calculates_size(self, tmp_path):
        """Test that profile size is calculated correctly"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        profile_path = manager.get_or_create_profile("test")
        
        # Add some data
        test_data = "x" * 1000  # 1000 bytes
        (profile_path / "local_storage" / "data.txt").write_text(test_data)
        
        info = manager.get_profile_info("test")
        
        # Size should include the test data
        assert info["size_bytes"] >= 1000


class TestSanitizeProfileName:
    """Test _sanitize_profile_name method"""
    
    def test_sanitize_normal_name(self, tmp_path):
        """Test that normal names pass through unchanged"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        assert manager._sanitize_profile_name("test") == "test"
        assert manager._sanitize_profile_name("test_profile") == "test_profile"
        assert manager._sanitize_profile_name("test-profile") == "test-profile"
        assert manager._sanitize_profile_name("test profile") == "test profile"
    
    def test_sanitize_removes_special_chars(self, tmp_path):
        """Test that special characters are replaced"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        assert manager._sanitize_profile_name("test@profile") == "test_profile"
        assert manager._sanitize_profile_name("test#profile") == "test_profile"
        assert manager._sanitize_profile_name("test$profile") == "test_profile"
    
    def test_sanitize_path_traversal_raises_error(self, tmp_path):
        """Test that path traversal attempts raise SecurityError"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        with pytest.raises(SecurityError, match="Invalid profile name"):
            manager._sanitize_profile_name("../etc/passwd")
        
        with pytest.raises(SecurityError, match="Invalid profile name"):
            manager._sanitize_profile_name("..\\windows\\system32")
        
        with pytest.raises(SecurityError, match="Invalid profile name"):
            manager._sanitize_profile_name("test/../other")
    
    def test_sanitize_removes_leading_dots(self, tmp_path):
        """Test that leading dots are removed"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        assert manager._sanitize_profile_name(".hidden") == "hidden"
        
        # ..hidden contains ".." which is path traversal, should raise error
        with pytest.raises(SecurityError, match="Invalid profile name"):
            manager._sanitize_profile_name("..hidden")
    
    def test_sanitize_empty_after_sanitization_raises_error(self, tmp_path):
        """Test that names that become empty raise SecurityError"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        # "..." contains ".." which is path traversal, raises different error
        with pytest.raises(SecurityError, match="Invalid profile name"):
            manager._sanitize_profile_name("...")
        
        # Pure dots (after stripping leading dots) should raise empty name error
        with pytest.raises(SecurityError, match="becomes empty after sanitization"):
            manager._sanitize_profile_name(".")
    
    def test_sanitize_strips_whitespace(self, tmp_path):
        """Test that leading/trailing whitespace is stripped"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        assert manager._sanitize_profile_name("  test  ") == "test"
        assert manager._sanitize_profile_name("\ttest\n") == "test"


class TestCreateProfileStructure:
    """Test _create_profile_structure method"""
    
    def test_creates_all_directories(self, tmp_path):
        """Test that all required directories are created"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        profile_path = tmp_path / "test_profile"
        
        manager._create_profile_structure(profile_path)
        
        assert profile_path.exists()
        assert (profile_path / "local_storage").exists()
        assert (profile_path / "local_storage").is_dir()
        assert (profile_path / "session_storage").exists()
        assert (profile_path / "session_storage").is_dir()
    
    def test_creates_cookies_file(self, tmp_path):
        """Test that cookies.db file is created"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        profile_path = tmp_path / "test_profile"
        
        manager._create_profile_structure(profile_path)
        
        cookies_file = profile_path / "cookies.db"
        assert cookies_file.exists()
        assert cookies_file.is_file()
    
    def test_creates_preferences_json(self, tmp_path):
        """Test that preferences.json is created with valid JSON"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        profile_path = tmp_path / "test_profile"
        
        manager._create_profile_structure(profile_path)
        
        prefs_file = profile_path / "preferences.json"
        assert prefs_file.exists()
        
        # Verify it's valid JSON
        with open(prefs_file, 'r') as f:
            prefs = json.load(f)
        
        assert isinstance(prefs, dict)
        assert "profile" in prefs
        assert "browser" in prefs
    
    def test_idempotent_creation(self, tmp_path):
        """Test that creating structure twice doesn't fail"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        profile_path = tmp_path / "test_profile"
        
        # Create twice
        manager._create_profile_structure(profile_path)
        manager._create_profile_structure(profile_path)
        
        # Should still exist and be valid
        assert profile_path.exists()
        assert (profile_path / "cookies.db").exists()
        assert (profile_path / "preferences.json").exists()


class TestIntegrationScenarios:
    """Integration tests for common usage scenarios"""
    
    def test_create_multiple_profiles_workflow(self, tmp_path):
        """Test creating and managing multiple profiles"""
        manager = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        # Create profiles
        work_profile = manager.get_or_create_profile("work")
        personal_profile = manager.get_or_create_profile("personal")
        default_profile = manager.get_or_create_profile()
        
        # List profiles
        profiles = manager.list_profiles()
        assert len(profiles) == 3
        assert "work" in profiles
        assert "personal" in profiles
        assert "default" in profiles
        
        # Get info
        work_info = manager.get_profile_info("work")
        assert work_info["name"] == "work"
        
        # Delete one
        manager.delete_profile("personal")
        profiles = manager.list_profiles()
        assert len(profiles) == 2
        assert "personal" not in profiles
    
    def test_profile_persistence_simulation(self, tmp_path):
        """Test that profiles persist across manager instances"""
        # Create profile with first manager instance
        manager1 = ChromeProfileManager(profiles_dir=str(tmp_path))
        profile_path = manager1.get_or_create_profile("persistent")
        
        # Add some data
        (profile_path / "local_storage" / "data.txt").write_text("persistent data")
        
        # Create new manager instance (simulating restart)
        manager2 = ChromeProfileManager(profiles_dir=str(tmp_path))
        
        # Profile should still exist
        profiles = manager2.list_profiles()
        assert "persistent" in profiles
        
        # Data should still be there
        profile_path2 = manager2.get_or_create_profile("persistent")
        data = (profile_path2 / "local_storage" / "data.txt").read_text()
        assert data == "persistent data"
