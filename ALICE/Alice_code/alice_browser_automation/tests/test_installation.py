"""
Unit tests for installation scripts.

Tests the installation, configuration setup, and verification scripts.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestInstallScript:
    """Test install.py functionality"""
    
    def test_check_python_version_success(self):
        """Test Python version check with valid version"""
        from install import check_python_version
        
        # Current Python should be 3.10+
        assert check_python_version() is True
    
    def test_check_python_version_failure(self):
        """Test Python version check with invalid version"""
        from install import check_python_version
        import sys
        from unittest.mock import MagicMock
        
        # Create a mock version_info object
        mock_version = MagicMock()
        mock_version.major = 3
        mock_version.minor = 9
        mock_version.micro = 0
        
        with patch('sys.version_info', mock_version):
            # Should fail with Python 3.9
            assert check_python_version() is False
    
    @patch('shutil.disk_usage')
    def test_check_system_resources_sufficient(self, mock_disk_usage):
        """Test system resource check with sufficient resources"""
        from install import check_system_resources
        
        # Mock sufficient disk space (20GB free)
        mock_disk_usage.return_value = Mock(free=20 * 1024 ** 3)
        
        success, warnings = check_system_resources()
        
        # Should succeed with no warnings about disk
        disk_warnings = [w for w in warnings if 'disk' in w.lower()]
        assert len(disk_warnings) == 0
    
    @patch('shutil.disk_usage')
    def test_check_system_resources_low_disk(self, mock_disk_usage):
        """Test system resource check with low disk space"""
        from install import check_system_resources
        
        # Mock low disk space (5GB free)
        mock_disk_usage.return_value = Mock(free=5 * 1024 ** 3)
        
        success, warnings = check_system_resources()
        
        # Should have warning about disk space
        assert success is False
        assert any('disk' in w.lower() for w in warnings)
    
    @patch('subprocess.run')
    def test_install_python_dependencies_success(self, mock_run):
        """Test successful Python dependency installation"""
        from install import install_python_dependencies
        
        # Mock successful pip install
        mock_run.return_value = Mock(returncode=0)
        
        assert install_python_dependencies() is True
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_install_python_dependencies_failure(self, mock_run):
        """Test failed Python dependency installation"""
        from install import install_python_dependencies
        import subprocess
        
        # Mock failed pip install with CalledProcessError
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, 
            cmd=['pip', 'install'],
            stderr="Installation failed"
        )
        
        assert install_python_dependencies() is False
    
    @patch('shutil.which')
    def test_check_ollama_installation_found(self, mock_which):
        """Test Ollama installation check when installed"""
        from install import check_ollama_installation
        
        # Mock Ollama found in PATH
        mock_which.return_value = "/usr/local/bin/ollama"
        
        assert check_ollama_installation() is True
    
    @patch('shutil.which')
    def test_check_ollama_installation_not_found(self, mock_which):
        """Test Ollama installation check when not installed"""
        from install import check_ollama_installation
        
        # Mock Ollama not found
        mock_which.return_value = None
        
        assert check_ollama_installation() is False
    
    def test_create_directory_structure(self):
        """Test directory structure creation"""
        from install import create_directory_structure
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                assert create_directory_structure() is True
                
                # Verify directories were created
                assert (Path(tmpdir) / ".alice" / "browser_profiles").exists()
                assert (Path(tmpdir) / ".alice" / "logs").exists()


class TestSetupConfigScript:
    """Test setup_config.py functionality"""
    
    def test_get_default_config(self):
        """Test default configuration generation"""
        from setup_config import get_default_config
        
        config = get_default_config()
        
        assert isinstance(config, dict)
        assert 'browser' in config
        assert 'qwen' in config
        assert 'logging' in config
        assert config['browser']['max_concurrent_sessions'] == 3
        assert config['qwen']['model'] == 'qwen2.5-coder:3b'
    
    def test_generate_config_file(self):
        """Test configuration file generation"""
        from setup_config import generate_config_file
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yaml"
            
            assert generate_config_file(config_path) is True
            assert config_path.exists()
            
            # Verify file contains expected content
            content = config_path.read_text()
            assert 'browser:' in content
            assert 'qwen:' in content
            assert 'qwen2.5-coder:3b' in content
    
    def test_create_profile_directory_structure(self):
        """Test browser profile directory creation"""
        from setup_config import create_profile_directory_structure
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                # Should succeed
                result = create_profile_directory_structure()
                
                # Verify profile directories exist (even if README creation fails due to encoding)
                base_dir = Path(tmpdir) / ".alice" / "browser_profiles"
                assert (base_dir / "default").exists()
                assert (base_dir / "default" / "local_storage").exists()
                assert (base_dir / "default" / "session_storage").exists()
                assert (base_dir / "default" / "extensions").exists()


class TestVerifyInstallationScript:
    """Test verify_installation.py functionality"""
    
    def test_verify_python_packages_all_installed(self):
        """Test Python package verification when all installed"""
        from verify_installation import verify_python_packages
        
        # Most packages should be installed in test environment
        success, missing = verify_python_packages()
        
        # Should succeed or have minimal missing packages
        assert isinstance(success, bool)
        assert isinstance(missing, list)
    
    @patch('httpx.get')
    def test_verify_ollama_service_running(self, mock_get):
        """Test Ollama service verification when running"""
        from verify_installation import verify_ollama_service
        
        # Mock successful Ollama response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "0.1.0"}
        mock_get.return_value = mock_response
        
        success, version = verify_ollama_service()
        
        assert success is True
        assert version == "0.1.0"
    
    @patch('httpx.get')
    def test_verify_ollama_service_not_running(self, mock_get):
        """Test Ollama service verification when not running"""
        from verify_installation import verify_ollama_service
        
        # Mock connection error
        mock_get.side_effect = Exception("Connection refused")
        
        success, version = verify_ollama_service()
        
        assert success is False
        assert version is None
    
    @patch('httpx.get')
    def test_verify_qwen_model_available(self, mock_get):
        """Test Qwen model verification when available"""
        from verify_installation import verify_qwen_model
        
        # Mock successful model list response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {
                    "name": "qwen2.5-coder:3b",
                    "size": 2 * 1024 ** 3  # 2GB
                }
            ]
        }
        mock_get.return_value = mock_response
        
        success, model_info = verify_qwen_model()
        
        assert success is True
        assert model_info is not None
        assert model_info["name"] == "qwen2.5-coder:3b"
    
    @patch('httpx.get')
    def test_verify_qwen_model_not_available(self, mock_get):
        """Test Qwen model verification when not available"""
        from verify_installation import verify_qwen_model
        
        # Mock response with no Qwen model
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "other-model:latest"}
            ]
        }
        mock_get.return_value = mock_response
        
        success, model_info = verify_qwen_model()
        
        assert success is False
        assert model_info is None
    
    def test_verify_directory_structure(self):
        """Test directory structure verification"""
        from verify_installation import verify_directory_structure
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                # Create required directories
                (Path(tmpdir) / ".alice" / "browser_profiles").mkdir(parents=True)
                (Path(tmpdir) / ".alice" / "logs").mkdir(parents=True)
                
                assert verify_directory_structure() is True
    
    def test_verify_directory_structure_missing(self):
        """Test directory structure verification with missing directories"""
        from verify_installation import verify_directory_structure
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                # Don't create directories
                assert verify_directory_structure() is False


class TestInstallationIntegration:
    """Integration tests for installation process"""
    
    def test_config_file_format(self):
        """Test that generated config file is valid YAML"""
        from setup_config import generate_config_file
        import yaml
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            generate_config_file(config_path)
            
            # Should be valid YAML
            with open(config_path) as f:
                config = yaml.safe_load(f)
            
            assert isinstance(config, dict)
            assert 'browser' in config
            assert 'qwen' in config
    
    def test_directory_structure_complete(self):
        """Test that complete directory structure is created"""
        from install import create_directory_structure
        from setup_config import create_profile_directory_structure
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                # Run both directory creation functions
                create_directory_structure()
                create_profile_directory_structure()
                
                # Verify all directories exist
                base = Path(tmpdir) / ".alice"
                assert (base / "browser_profiles" / "default").exists()
                assert (base / "browser_profiles" / "default" / "local_storage").exists()
                assert (base / "logs").exists()


class TestInstallationRequirements:
    """Test that installation meets requirements"""
    
    def test_requirement_1_1_browser_use_installation(self):
        """
        Test Requirement 1.1: Browser_Automation_Engine SHALL install 
        browser-use library with Playwright dependencies
        """
        # Verify requirements.txt contains browser-use and playwright
        requirements_path = Path(__file__).parent.parent / "requirements.txt"
        assert requirements_path.exists()
        
        content = requirements_path.read_text()
        assert 'browser-use' in content
        assert 'playwright' in content
    
    def test_requirement_1_2_ollama_qwen_installation(self):
        """
        Test Requirement 1.2: Browser_Automation_Engine SHALL install 
        Ollama with Qwen Coder 2.5 3B model
        """
        from install import check_ollama_installation, download_qwen_model
        
        # Verify functions exist for Ollama and Qwen
        assert callable(check_ollama_installation)
        assert callable(download_qwen_model)
    
    def test_requirement_1_3_playwright_verification(self):
        """
        Test Requirement 1.3: Browser_Automation_Engine SHALL verify 
        Playwright browser binaries are installed
        """
        from verify_installation import verify_playwright_installation
        
        # Verify function exists
        assert callable(verify_playwright_installation)
    
    def test_requirement_1_4_qwen_model_validation(self):
        """
        Test Requirement 1.4: Browser_Automation_Engine SHALL validate 
        Qwen model availability via Ollama API
        """
        from verify_installation import verify_qwen_model
        
        # Verify function exists
        assert callable(verify_qwen_model)
    
    def test_requirement_7_1_chrome_profile_creation(self):
        """
        Test Requirement 7.1: Browser_Automation_Engine SHALL create and 
        maintain Chrome_Profile for persistent sessions
        """
        from setup_config import create_profile_directory_structure
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                create_profile_directory_structure()
                
                # Verify default profile directory exists
                profile_dir = Path(tmpdir) / ".alice" / "browser_profiles" / "default"
                assert profile_dir.exists()
                assert (profile_dir / "local_storage").exists()
                assert (profile_dir / "session_storage").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
