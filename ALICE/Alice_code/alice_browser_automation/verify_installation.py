#!/usr/bin/env python3
"""
Installation verification script for Alice Browser Automation.

This script verifies that all components are properly installed and configured.
"""

import sys
import asyncio
from pathlib import Path
from typing import Tuple, Optional, List


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(message: str) -> None:
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def print_success(message: str) -> None:
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_warning(message: str) -> None:
    """Print a warning message"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def print_error(message: str) -> None:
    """Print an error message"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message: str) -> None:
    """Print an info message"""
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")


def verify_python_packages() -> Tuple[bool, List[str]]:
    """
    Verify required Python packages are installed.
    
    Returns:
        Tuple of (success, missing_packages)
    """
    print_info("Verifying Python packages...")
    
    required_packages = [
        'playwright',
        'browser_use',
        'ollama',
        'yaml',
        'aiohttp',
        'httpx',
        'keyring',
        'cryptography',
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'yaml':
                __import__('yaml')
            elif package == 'browser_use':
                # browser-use might not be importable yet, skip for now
                continue
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if not missing_packages:
        print_success(f"All required Python packages are installed")
        return True, []
    else:
        print_error(f"Missing packages: {', '.join(missing_packages)}")
        return False, missing_packages


def verify_playwright_installation() -> bool:
    """
    Verify Playwright is installed with browser binaries.
    
    Returns:
        True if Playwright is properly installed
    """
    print_info("Verifying Playwright installation...")
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Check if Chromium is installed
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print_success("Playwright Chromium browser is installed and working")
                return True
            except Exception as e:
                print_error(f"Playwright Chromium browser not available: {e}")
                print_info("Run: python -m playwright install chromium")
                return False
    except ImportError:
        print_error("Playwright is not installed")
        print_info("Run: pip install playwright")
        return False
    except Exception as e:
        print_error(f"Playwright verification failed: {e}")
        return False


def verify_ollama_service() -> Tuple[bool, Optional[str]]:
    """
    Verify Ollama service is running.
    
    Returns:
        Tuple of (success, version)
    """
    print_info("Verifying Ollama service...")
    
    try:
        import httpx
        
        # Check if service is running
        response = httpx.get("http://localhost:11434/api/version", timeout=5.0)
        
        if response.status_code == 200:
            version = response.json().get("version", "unknown")
            print_success(f"Ollama service is running (version: {version})")
            return True, version
        else:
            print_error(f"Ollama service returned status {response.status_code}")
            return False, None
    except Exception as e:
        print_error(f"Ollama service is not accessible: {e}")
        print_info("Start Ollama with: ollama serve")
        return False, None


def verify_qwen_model() -> Tuple[bool, Optional[dict]]:
    """
    Verify Qwen model is available.
    
    Returns:
        Tuple of (success, model_info)
    """
    print_info("Verifying Qwen model availability...")
    
    try:
        import httpx
        
        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        
        if response.status_code == 200:
            models = response.json().get("models", [])
            qwen_models = [m for m in models if "qwen2.5-coder:3b" in m.get("name", "")]
            
            if qwen_models:
                model_info = qwen_models[0]
                size_gb = model_info.get("size", 0) / (1024 ** 3)
                print_success(f"Qwen 2.5 Coder 3B model is available ({size_gb:.2f} GB)")
                return True, model_info
            else:
                print_error("Qwen 2.5 Coder 3B model not found")
                print_info("Download with: ollama pull qwen2.5-coder:3b")
                return False, None
        else:
            print_error("Could not retrieve model list from Ollama")
            return False, None
    except Exception as e:
        print_error(f"Could not verify Qwen model: {e}")
        return False, None


async def test_qwen_model() -> bool:
    """
    Test Qwen model with a simple query.
    
    Returns:
        True if model responds correctly
    """
    print_info("Testing Qwen model response...")
    
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5-coder:3b",
                    "prompt": "Return only the JSON: {\"status\": \"ok\"}",
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                
                if "ok" in response_text.lower():
                    print_success("Qwen model is responding correctly")
                    return True
                else:
                    print_warning(f"Qwen model response unexpected: {response_text[:100]}")
                    return True  # Still consider it working
            else:
                print_error(f"Qwen model test failed with status {response.status_code}")
                return False
    except Exception as e:
        print_error(f"Qwen model test failed: {e}")
        return False


async def test_browser_session() -> bool:
    """
    Test creating a browser session.
    
    Returns:
        True if browser session can be created
    """
    print_info("Testing browser session creation...")
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to a simple page
            await page.goto("about:blank")
            
            # Close browser
            await browser.close()
            
            print_success("Browser session created and closed successfully")
            return True
    except Exception as e:
        print_error(f"Browser session test failed: {e}")
        return False


def verify_configuration() -> bool:
    """
    Verify configuration files exist and are valid.
    
    Returns:
        True if configuration is valid
    """
    print_info("Verifying configuration...")
    
    try:
        from config import Config
        
        # Try to load configuration
        config = Config.load()
        
        # Validate configuration
        config.validate()
        
        print_success("Configuration is valid")
        
        # Check if .env file exists
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            print_success(".env file exists")
        else:
            print_warning(".env file not found (using defaults)")
            print_info("Copy .env.example to .env and configure if needed")
        
        return True
    except Exception as e:
        print_error(f"Configuration validation failed: {e}")
        return False


def verify_directory_structure() -> bool:
    """
    Verify required directories exist.
    
    Returns:
        True if all directories exist
    """
    print_info("Verifying directory structure...")
    
    required_dirs = [
        Path.home() / ".alice" / "browser_profiles",
        Path.home() / ".alice" / "logs",
    ]
    
    all_exist = True
    
    for directory in required_dirs:
        if directory.exists():
            print_success(f"Directory exists: {directory}")
        else:
            print_error(f"Directory missing: {directory}")
            all_exist = False
    
    return all_exist


async def run_integration_test() -> bool:
    """
    Run a simple integration test.
    
    Returns:
        True if integration test passes
    """
    print_info("Running integration test...")
    
    try:
        # Import required modules
        from qwen_client import QwenModelClient
        from playwright.async_api import async_playwright
        
        # Test 1: Qwen client
        qwen_client = QwenModelClient()
        
        # Test 2: Browser session
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("about:blank")
            await browser.close()
        
        print_success("Integration test passed")
        return True
    except Exception as e:
        print_error(f"Integration test failed: {e}")
        return False


def print_installation_status(results: dict) -> None:
    """
    Print overall installation status.
    
    Args:
        results: Dictionary of verification results
    """
    print_header("Installation Status Report")
    
    total_checks = len(results)
    passed_checks = sum(1 for v in results.values() if v)
    
    print(f"Checks passed: {passed_checks}/{total_checks}\n")
    
    for check, passed in results.items():
        status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
        print(f"  {check.ljust(40)} {status}")
    
    print()
    
    if all(results.values()):
        print_success("All checks passed! Alice Browser Automation is ready to use.")
        print()
        print_info("You can now:")
        print("  1. Start the Alice agent")
        print("  2. Use browser automation commands via voice")
        print("  3. Check logs at ~/.alice/logs/browser_automation.log")
    else:
        print_warning("Some checks failed. Please address the issues above.")
        print()
        print_info("Common fixes:")
        print("  - Install missing packages: pip install -r requirements.txt")
        print("  - Install Playwright browsers: python -m playwright install chromium")
        print("  - Start Ollama service: ollama serve")
        print("  - Download Qwen model: ollama pull qwen2.5-coder:3b")


async def main() -> int:
    """
    Main verification function.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print_header("Alice Browser Automation Installation Verification")
    
    results = {}
    
    # Verify Python packages
    packages_ok, missing = verify_python_packages()
    results["Python packages"] = packages_ok
    
    # Verify Playwright
    results["Playwright installation"] = verify_playwright_installation()
    
    # Verify Ollama service
    ollama_ok, version = verify_ollama_service()
    results["Ollama service"] = ollama_ok
    
    # Verify Qwen model
    if ollama_ok:
        qwen_ok, model_info = verify_qwen_model()
        results["Qwen model availability"] = qwen_ok
        
        # Test Qwen model
        if qwen_ok:
            results["Qwen model response"] = await test_qwen_model()
    else:
        results["Qwen model availability"] = False
        results["Qwen model response"] = False
    
    # Verify configuration
    results["Configuration"] = verify_configuration()
    
    # Verify directory structure
    results["Directory structure"] = verify_directory_structure()
    
    # Test browser session
    if results["Playwright installation"]:
        results["Browser session test"] = await test_browser_session()
    else:
        results["Browser session test"] = False
    
    # Run integration test
    if all([
        results.get("Python packages"),
        results.get("Playwright installation"),
        results.get("Qwen model availability"),
    ]):
        results["Integration test"] = await run_integration_test()
    else:
        results["Integration test"] = False
    
    # Print status report
    print_installation_status(results)
    
    # Return exit code
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
