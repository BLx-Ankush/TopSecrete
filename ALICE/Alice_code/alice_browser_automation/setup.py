#!/usr/bin/env python3
"""
Master setup script for Alice Browser Automation.

This script runs the complete installation and setup process:
1. Installation (install.py)
2. Configuration setup (setup_config.py)
3. Verification (verify_installation.py)
"""

import sys
import subprocess
from pathlib import Path


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


def print_error(message: str) -> None:
    """Print an error message"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message: str) -> None:
    """Print an info message"""
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")


def run_script(script_name: str, description: str) -> bool:
    """
    Run a setup script.
    
    Args:
        script_name: Name of the script to run
        description: Description of what the script does
        
    Returns:
        True if script succeeded
    """
    print_header(description)
    
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        print_error(f"Script not found: {script_path}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=False,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            print_success(f"{description} completed successfully")
            return True
        else:
            print_error(f"{description} failed with exit code {result.returncode}")
            return False
    except Exception as e:
        print_error(f"Failed to run {script_name}: {e}")
        return False


def main() -> int:
    """
    Main setup function.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print_header("Alice Browser Automation - Complete Setup")
    
    print_info("This script will:")
    print("  1. Install all dependencies")
    print("  2. Set up configuration files")
    print("  3. Verify the installation")
    print()
    
    response = input("Continue? (Y/n): ").strip().lower()
    if response == 'n':
        print_info("Setup cancelled")
        return 0
    
    # Step 1: Installation
    if not run_script("install.py", "Step 1: Installation"):
        print_error("Installation failed. Please fix the issues and try again.")
        return 1
    
    # Step 2: Configuration setup
    if not run_script("setup_config.py", "Step 2: Configuration Setup"):
        print_error("Configuration setup failed. Please fix the issues and try again.")
        return 1
    
    # Step 3: Verification
    if not run_script("verify_installation.py", "Step 3: Installation Verification"):
        print_error("Verification failed. Please fix the issues and try again.")
        return 1
    
    # All steps completed
    print_header("Setup Complete!")
    
    print_success("Alice Browser Automation is ready to use!")
    print()
    print_info("Next steps:")
    print("  1. Review and customize alice_browser_automation_config.yaml if needed")
    print("  2. Copy .env.example to .env and configure environment variables")
    print("  3. Start using Alice with browser automation capabilities")
    print()
    print_info("Documentation:")
    print("  - README.md: Overview and usage guide")
    print("  - alice_browser_automation_config.yaml: Configuration reference")
    print("  - .env.example: Environment variables reference")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
