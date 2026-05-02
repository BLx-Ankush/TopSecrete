#!/usr/bin/env python3
"""
Installation script for Alice Browser Automation.

This script installs all required dependencies and verifies system requirements.
"""

import sys
import subprocess
import platform
import shutil
import os
from pathlib import Path
from typing import Tuple, Optional


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


def check_python_version() -> bool:
    """
    Verify Python version is 3.10 or higher.
    
    Returns:
        True if Python version is sufficient
    """
    print_info("Checking Python version...")
    version = sys.version_info
    
    if version.major >= 3 and version.minor >= 10:
        print_success(f"Python {version.major}.{version.minor}.{version.micro} detected")
        return True
    else:
        print_error(f"Python 3.10+ required, found {version.major}.{version.minor}.{version.micro}")
        return False


def check_system_resources() -> Tuple[bool, list]:
    """
    Verify system has sufficient resources.
    
    Returns:
        Tuple of (success, warnings)
    """
    print_info("Checking system resources...")
    warnings = []
    
    # Check available RAM (approximate)
    try:
        if platform.system() == "Linux":
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                mem_total = int([line for line in meminfo.split('\n') if 'MemTotal' in line][0].split()[1]) // 1024
        elif platform.system() == "Darwin":  # macOS
            result = subprocess.run(['sysctl', 'hw.memsize'], capture_output=True, text=True, encoding='utf-8', errors='ignore')
            mem_total = int(result.stdout.split()[1]) // (1024 * 1024)
        elif platform.system() == "Windows":
            result = subprocess.run(['wmic', 'computersystem', 'get', 'totalphysicalmemory'], 
                                  capture_output=True, text=True, encoding='utf-8', errors='ignore')
            mem_total = int(result.stdout.split('\n')[1].strip()) // (1024 * 1024)
        else:
            mem_total = 8192  # Assume sufficient if we can't detect
        
        if mem_total < 8192:
            warnings.append(f"Low RAM detected: {mem_total}MB (8GB recommended)")
        else:
            print_success(f"RAM: {mem_total}MB available")
    except Exception as e:
        warnings.append(f"Could not verify RAM: {e}")
    
    # Check available disk space
    try:
        stat = shutil.disk_usage(Path.home())
        free_gb = stat.free // (1024 ** 3)
        
        if free_gb < 10:
            warnings.append(f"Low disk space: {free_gb}GB free (10GB recommended)")
        else:
            print_success(f"Disk space: {free_gb}GB available")
    except Exception as e:
        warnings.append(f"Could not verify disk space: {e}")
    
    return len(warnings) == 0, warnings


def install_python_dependencies() -> bool:
    """
    Install Python dependencies from requirements.txt.
    
    Returns:
        True if installation successful
    """
    print_info("Installing Python dependencies...")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print_error(f"requirements.txt not found at {requirements_file}")
        return False
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        print_success("Python dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install Python dependencies: {e.stderr}")
        return False


def install_playwright_browsers() -> bool:
    """
    Install Playwright browser binaries (Chromium).
    
    Returns:
        True if installation successful
    """
    print_info("Installing Playwright Chromium browser...")
    
    try:
        # Install Chromium browser
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        print_success("Playwright Chromium browser installed successfully")
        
        # Install system dependencies (Linux only)
        if platform.system() == "Linux":
            print_info("Installing Playwright system dependencies...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "playwright", "install-deps", "chromium"],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore'
                )
                print_success("Playwright system dependencies installed")
            except subprocess.CalledProcessError as e:
                print_warning(f"Could not install system dependencies: {e.stderr}")
                print_warning("You may need to run this with sudo or install manually")
        
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install Playwright browsers: {e.stderr}")
        return False


def check_ollama_installation() -> bool:
    """
    Check if Ollama is installed.
    
    Returns:
        True if Ollama is installed
    """
    print_info("Checking Ollama installation...")
    
    if shutil.which("ollama") is not None:
        print_success("Ollama is installed")
        return True
    else:
        print_warning("Ollama is not installed")
        return False


def provide_ollama_instructions() -> None:
    """Provide instructions for installing Ollama"""
    print_info("Ollama installation instructions:")
    print()
    
    system = platform.system()
    
    if system == "Linux":
        print("  Run the following command:")
        print(f"  {Colors.BOLD}curl -fsSL https://ollama.com/install.sh | sh{Colors.END}")
    elif system == "Darwin":  # macOS
        print("  Option 1: Download from https://ollama.com/download")
        print("  Option 2: Install via Homebrew:")
        print(f"  {Colors.BOLD}brew install ollama{Colors.END}")
    elif system == "Windows":
        print("  Download the installer from: https://ollama.com/download")
    else:
        print("  Visit https://ollama.com/download for installation instructions")
    
    print()
    print("  After installation, start Ollama:")
    print(f"  {Colors.BOLD}ollama serve{Colors.END}")
    print()


def check_ollama_service() -> bool:
    """
    Check if Ollama service is running.
    
    Returns:
        True if Ollama service is accessible
    """
    print_info("Checking Ollama service...")
    
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        
        if response.status_code == 200:
            print_success("Ollama service is running")
            return True
        else:
            print_warning(f"Ollama service returned status {response.status_code}")
            return False
    except Exception as e:
        print_warning(f"Ollama service is not accessible: {e}")
        print_info("Start Ollama with: ollama serve")
        return False


def download_qwen_model() -> bool:
    """
    Download Qwen 2.5 Coder 3B model via Ollama.
    
    Returns:
        True if model download successful
    """
    print_info("Downloading Qwen 2.5 Coder 3B model (this may take several minutes)...")
    
    try:
        process = subprocess.Popen(
            ["ollama", "pull", "qwen2.5-coder:3b"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='ignore',
            bufsize=1
        )
        
        # Stream output to show progress
        for line in process.stdout:
            print(f"  {line.rstrip()}")
        
        process.wait()
        
        if process.returncode == 0:
            print_success("Qwen 2.5 Coder 3B model downloaded successfully")
            return True
        else:
            print_error("Failed to download Qwen model")
            return False
    except FileNotFoundError:
        print_error("Ollama command not found. Please install Ollama first.")
        return False
    except Exception as e:
        print_error(f"Failed to download Qwen model: {e}")
        return False


def verify_qwen_model() -> bool:
    """
    Verify Qwen model is available.
    
    Returns:
        True if model is available
    """
    print_info("Verifying Qwen model availability...")
    
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        
        if response.status_code == 200:
            models = response.json().get("models", [])
            qwen_models = [m for m in models if "qwen2.5-coder:3b" in m.get("name", "")]
            
            if qwen_models:
                print_success("Qwen 2.5 Coder 3B model is available")
                return True
            else:
                print_warning("Qwen 2.5 Coder 3B model not found")
                return False
        else:
            print_warning("Could not verify model availability")
            return False
    except Exception as e:
        print_warning(f"Could not verify model: {e}")
        return False


def create_directory_structure() -> bool:
    """
    Create necessary directory structure.
    
    Returns:
        True if directories created successfully
    """
    print_info("Creating directory structure...")
    
    directories = [
        Path.home() / ".alice" / "browser_profiles",
        Path.home() / ".alice" / "logs",
    ]
    
    try:
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        print_success("Directory structure created")
        return True
    except Exception as e:
        print_error(f"Failed to create directories: {e}")
        return False


def main() -> int:
    """
    Main installation function.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print_header("Alice Browser Automation Installation")
    
    # Track installation status
    all_success = True
    warnings = []
    
    # Step 1: Verify Python version
    if not check_python_version():
        print_error("Installation cannot continue with unsupported Python version")
        return 1
    
    # Step 2: Check system resources
    resources_ok, resource_warnings = check_system_resources()
    if not resources_ok:
        warnings.extend(resource_warnings)
        for warning in resource_warnings:
            print_warning(warning)
    
    # Step 3: Install Python dependencies
    if not install_python_dependencies():
        print_error("Failed to install Python dependencies")
        all_success = False
    
    # Step 4: Install Playwright browsers
    if not install_playwright_browsers():
        print_error("Failed to install Playwright browsers")
        all_success = False
    
    # Step 5: Check Ollama installation
    ollama_installed = check_ollama_installation()
    if not ollama_installed:
        provide_ollama_instructions()
        all_success = False
    else:
        # Step 6: Check Ollama service
        ollama_running = check_ollama_service()
        
        if ollama_running:
            # Step 7: Download Qwen model
            if not download_qwen_model():
                all_success = False
            else:
                # Step 8: Verify Qwen model
                if not verify_qwen_model():
                    all_success = False
        else:
            print_warning("Ollama service is not running. Start it with: ollama serve")
            print_warning("Then run: ollama pull qwen2.5-coder:3b")
            all_success = False
    
    # Step 9: Create directory structure
    if not create_directory_structure():
        all_success = False
    
    # Print summary
    print_header("Installation Summary")
    
    if all_success:
        print_success("Installation completed successfully!")
        print()
        print_info("Next steps:")
        print("  1. Copy .env.example to .env and configure settings")
        print("  2. Run the verification script: python verify_installation.py")
        print("  3. Start using Alice Browser Automation!")
        return 0
    else:
        print_warning("Installation completed with warnings or errors")
        print()
        print_info("Please address the issues above and re-run the installation")
        
        if not ollama_installed:
            print()
            print_info("To complete Ollama setup:")
            provide_ollama_instructions()
            print("  Then run: ollama pull qwen2.5-coder:3b")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
