#!/usr/bin/env python3
"""
Configuration setup script for Alice Browser Automation.

This script generates default configuration files and validates settings.
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, Any


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


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


def print_header(message: str) -> None:
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def get_default_config() -> Dict[str, Any]:
    """
    Get default configuration dictionary.
    
    Returns:
        Default configuration as dictionary
    """
    return {
        'browser': {
            'headless_default': True,
            'max_concurrent_sessions': 3,
            'idle_timeout_seconds': 300,
            'profiles_dir': '~/.alice/browser_profiles',
            'default_profile': 'default',
        },
        'qwen': {
            'host': 'http://localhost:11434',
            'model': 'qwen2.5-coder:3b',
            'timeout_seconds': 30,
            'max_retries': 3,
        },
        'dom_parser': {
            'cache_duration_seconds': 2.0,
            'max_elements': 1000,
            'filter_decorative': True,
        },
        'performance': {
            'dom_parse_timeout': 2.0,
            'action_generation_timeout': 5.0,
            'simple_action_timeout': 1.0,
        },
        'security': {
            'require_payment_confirmation': True,
            'block_banking_sites': False,
            'validate_ssl': True,
            'clear_sensitive_data': True,
        },
        'logging': {
            'level': 'INFO',
            'log_file': '~/.alice/logs/browser_automation.log',
            'log_sensitive_data': False,
        },
    }


def generate_config_file(output_path: Path) -> bool:
    """
    Generate default configuration YAML file.
    
    Args:
        output_path: Path where config file should be created
        
    Returns:
        True if file created successfully
    """
    print_info(f"Generating configuration file: {output_path}")
    
    try:
        config = get_default_config()
        
        # Add comments to the YAML file
        yaml_content = """# Alice Browser Automation Configuration
# This file contains default settings for the browser automation engine

# Browser Configuration
browser:
  # Run browser in headless mode by default (no visible window)
  headless_default: true
  
  # Maximum number of concurrent browser sessions
  max_concurrent_sessions: 3
  
  # Idle timeout in seconds before closing inactive sessions
  idle_timeout_seconds: 300
  
  # Directory for storing browser profiles
  profiles_dir: ~/.alice/browser_profiles
  
  # Default profile name
  default_profile: default

# Qwen Model Configuration
qwen:
  # Ollama API host
  host: http://localhost:11434
  
  # Qwen model name
  model: qwen2.5-coder:3b
  
  # Request timeout in seconds
  timeout_seconds: 30
  
  # Maximum retry attempts for failed requests
  max_retries: 3

# DOM Parser Configuration
dom_parser:
  # Cache duration for parsed DOM in seconds
  cache_duration_seconds: 2.0
  
  # Maximum number of elements to extract
  max_elements: 1000
  
  # Filter out decorative elements (images without alt, spacers, etc.)
  filter_decorative: true

# Performance Configuration
performance:
  # Timeout for DOM parsing in seconds
  dom_parse_timeout: 2.0
  
  # Timeout for action generation in seconds
  action_generation_timeout: 5.0
  
  # Timeout for simple actions (click, type) in seconds
  simple_action_timeout: 1.0

# Security Configuration
security:
  # Require explicit user confirmation for payment actions
  require_payment_confirmation: true
  
  # Block automation on banking websites
  block_banking_sites: false
  
  # Validate SSL certificates for HTTPS connections
  validate_ssl: true
  
  # Clear sensitive data from memory after task completion
  clear_sensitive_data: true

# Logging Configuration
logging:
  # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
  level: INFO
  
  # Log file path
  log_file: ~/.alice/logs/browser_automation.log
  
  # Log sensitive data (passwords, OTPs, etc.) - NOT RECOMMENDED
  log_sensitive_data: false
"""
        
        with open(output_path, 'w') as f:
            f.write(yaml_content)
        
        print_success(f"Configuration file created: {output_path}")
        return True
    except Exception as e:
        print_error(f"Failed to create configuration file: {e}")
        return False


def update_env_example() -> bool:
    """
    Ensure .env.example is up to date.
    
    Returns:
        True if file is up to date
    """
    print_info("Checking .env.example file...")
    
    env_example_path = Path(__file__).parent / ".env.example"
    
    if env_example_path.exists():
        print_success(".env.example already exists")
        return True
    
    # If it doesn't exist, create it
    print_warning(".env.example not found, creating it...")
    
    env_content = """# Alice Browser Automation Environment Variables
# Copy this file to .env and fill in your values

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
QWEN_MODEL=qwen2.5-coder:3b

# Browser Configuration
BROWSER_PROFILES_DIR=~/.alice/browser_profiles

# LiveKit Configuration (if not already set in main Alice .env)
# LIVEKIT_URL=wss://your-livekit-server.com
# LIVEKIT_API_KEY=your-api-key
# LIVEKIT_API_SECRET=your-api-secret

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=~/.alice/logs/browser_automation.log

# Security Configuration
REQUIRE_PAYMENT_CONFIRMATION=true
BLOCK_BANKING_SITES=false
VALIDATE_SSL=true

# Performance Configuration
MAX_CONCURRENT_SESSIONS=3
IDLE_TIMEOUT_SECONDS=300

# Feature Flags
ENABLE_OTP_VERIFICATION=true
ENABLE_PROBLEM_SOLVING=true
ENABLE_WEB_BOOKINGS=true
ENABLE_APP_ACCESS=true
"""
    
    try:
        with open(env_example_path, 'w') as f:
            f.write(env_content)
        print_success(".env.example created")
        return True
    except Exception as e:
        print_error(f"Failed to create .env.example: {e}")
        return False


def create_profile_directory_structure() -> bool:
    """
    Create default browser profile directory structure.
    
    Returns:
        True if directories created successfully
    """
    print_info("Creating browser profile directory structure...")
    
    base_dir = Path.home() / ".alice" / "browser_profiles"
    
    directories = [
        base_dir / "default",
        base_dir / "default" / "local_storage",
        base_dir / "default" / "session_storage",
        base_dir / "default" / "extensions",
    ]
    
    try:
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Create a README in the profiles directory
        readme_path = base_dir / "README.md"
        readme_content = """# Alice Browser Profiles

This directory contains browser profiles for persistent sessions.

## Structure

Each profile has the following structure:

```
profile_name/
├── cookies.db          # Encrypted cookies
├── local_storage/      # Local storage data
├── session_storage/    # Session storage data
├── preferences.json    # Browser preferences
└── extensions/         # Browser extensions
```

## Default Profile

The `default` profile is used when no specific profile is requested.

## Creating New Profiles

New profiles are created automatically when requested by the automation engine.
You can also create them manually by copying the default profile structure.

## Security

- Cookies are encrypted using system keychain
- Sensitive data is never logged
- Profiles are stored locally and never transmitted

## Maintenance

- Old profiles can be deleted manually
- Clear profile data if you want to reset login sessions
"""
        
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        print_success("Browser profile directory structure created")
        return True
    except Exception as e:
        print_error(f"Failed to create profile directories: {e}")
        return False


def validate_configuration() -> bool:
    """
    Validate configuration on startup.
    
    Returns:
        True if configuration is valid
    """
    print_info("Validating configuration...")
    
    try:
        # Try to import and validate config
        from config import Config
        
        # Try loading config
        config = Config.load()
        
        # Validate
        config.validate()
        
        print_success("Configuration is valid")
        return True
    except ImportError:
        print_warning("Could not import config module (this is OK during initial setup)")
        return True
    except Exception as e:
        print_error(f"Configuration validation failed: {e}")
        return False


def main() -> int:
    """
    Main setup function.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print_header("Alice Browser Automation Configuration Setup")
    
    all_success = True
    
    # Step 1: Generate default config file
    config_path = Path(__file__).parent / "alice_browser_automation_config.yaml"
    
    if config_path.exists():
        print_warning(f"Configuration file already exists: {config_path}")
        response = input("Overwrite? (y/N): ").strip().lower()
        if response == 'y':
            if not generate_config_file(config_path):
                all_success = False
        else:
            print_info("Keeping existing configuration file")
    else:
        if not generate_config_file(config_path):
            all_success = False
    
    # Step 2: Update .env.example
    if not update_env_example():
        all_success = False
    
    # Step 3: Create profile directory structure
    if not create_profile_directory_structure():
        all_success = False
    
    # Step 4: Validate configuration
    if not validate_configuration():
        all_success = False
    
    # Print summary
    print_header("Configuration Setup Summary")
    
    if all_success:
        print_success("Configuration setup completed successfully!")
        print()
        print_info("Next steps:")
        print("  1. Review alice_browser_automation_config.yaml and adjust settings if needed")
        print("  2. Copy .env.example to .env and configure environment variables")
        print("  3. Run the verification script: python verify_installation.py")
        return 0
    else:
        print_warning("Configuration setup completed with warnings or errors")
        print()
        print_info("Please address the issues above and re-run the setup")
        return 1


if __name__ == "__main__":
    sys.exit(main())
