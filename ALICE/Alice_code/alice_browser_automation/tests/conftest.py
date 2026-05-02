"""
Pytest configuration and fixtures for Alice Browser Automation tests.
"""

import pytest
import asyncio
from pathlib import Path
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config_path(tmp_path: Path) -> Path:
    """
    Create a temporary configuration file for testing.
    
    Args:
        tmp_path: Pytest temporary directory fixture
        
    Returns:
        Path to temporary config file
    """
    config_content = """
browser:
  headless_default: true
  max_concurrent_sessions: 2
  idle_timeout_seconds: 60
  profiles_dir: "{profiles_dir}"
  default_profile: "test"

qwen:
  host: "http://localhost:11434"
  model: "qwen2.5-coder:3b"
  timeout_seconds: 10
  max_retries: 2

dom_parser:
  cache_duration_seconds: 1.0
  max_elements: 100
  filter_decorative: true

performance:
  dom_parse_timeout: 1.0
  action_generation_timeout: 3.0
  simple_action_timeout: 0.5

security:
  require_payment_confirmation: true
  block_banking_sites: false
  validate_ssl: true
  clear_sensitive_data: true

logging:
  level: "DEBUG"
  log_file: "{log_file}"
  log_sensitive_data: false
"""
    
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    
    log_file = tmp_path / "test.log"
    
    # Convert paths to use forward slashes (works on all platforms including Windows)
    # This avoids YAML escaping issues with backslashes
    profiles_dir_str = str(profiles_dir).replace('\\', '/')
    log_file_str = str(log_file).replace('\\', '/')
    
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text(
        config_content.format(
            profiles_dir=profiles_dir_str,
            log_file=log_file_str
        )
    )
    
    return config_path


@pytest.fixture
def mock_playwright_page():
    """
    Create a mock Playwright page for testing.
    
    Returns:
        Mock page object
    """
    from unittest.mock import MagicMock, AsyncMock
    
    page = MagicMock()
    page.url = "https://example.com"
    page.title = AsyncMock(return_value="Example Domain")
    page.content = AsyncMock(return_value="<html><body><h1>Example</h1></body></html>")
    page.evaluate = AsyncMock()
    page.accessibility = MagicMock()
    page.accessibility.snapshot = AsyncMock()
    
    return page


@pytest.fixture
def sample_dom_html() -> str:
    """
    Provide sample HTML for DOM parsing tests.
    
    Returns:
        HTML string with various interactive elements
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
    </head>
    <body>
        <form id="login-form">
            <input type="email" id="email" aria-label="Email" placeholder="Enter email">
            <input type="password" id="password" aria-label="Password" placeholder="Enter password">
            <button type="submit" id="login-btn">Login</button>
        </form>
        
        <div class="content">
            <img src="logo.png" alt="">  <!-- Decorative -->
            <img src="profile.png" alt="User profile">  <!-- Not decorative -->
            <a href="/dashboard" id="dashboard-link">Dashboard</a>
            <button id="settings-btn" aria-label="Settings">⚙️</button>
        </div>
        
        <div class="spacer"></div>  <!-- Decorative -->
    </body>
    </html>
    """


@pytest.fixture
def sample_accessibility_tree() -> dict:
    """
    Provide sample accessibility tree for testing.
    
    Returns:
        Dictionary representing accessibility tree structure
    """
    return {
        "role": "WebArea",
        "name": "Test Page",
        "children": [
            {
                "role": "form",
                "name": "login-form",
                "children": [
                    {
                        "role": "textbox",
                        "name": "Email",
                        "children": []
                    },
                    {
                        "role": "textbox",
                        "name": "Password",
                        "children": []
                    },
                    {
                        "role": "button",
                        "name": "Login",
                        "children": []
                    }
                ]
            },
            {
                "role": "link",
                "name": "Dashboard",
                "children": []
            },
            {
                "role": "button",
                "name": "Settings",
                "children": []
            }
        ]
    }
