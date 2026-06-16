"""
Alice Security Trigger - Hashed Code Authentication
Secure launcher that requires a code before starting Alice.

SECURITY: the launch code is NOT stored in source. It is provided as a
SHA-256 hash via the ALICE_LAUNCH_CODE_HASH environment variable (or a local
.alice_launch.hash file). On first run, if neither is set, the user is guided
to create one. Comparison is constant-time.
"""

import os
import sys
import subprocess
import getpass
import hashlib
import hmac
from pathlib import Path
from datetime import datetime

# Where a locally-set code hash is stored if the user doesn't use the env var.
_HASH_FILE = Path(__file__).resolve().parent / ".alice_launch.hash"


def _hash_code(code: str) -> str:
    """SHA-256 hex digest of the code (with a fixed app salt)."""
    return hashlib.sha256(("alice-launch:" + code).encode("utf-8")).hexdigest()


def _get_expected_hash() -> str | None:
    """Return the configured launch-code hash, or None if not set up yet."""
    env = os.getenv("ALICE_LAUNCH_CODE_HASH")
    if env:
        return env.strip()
    try:
        if _HASH_FILE.exists():
            return _HASH_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return None


def _first_run_setup() -> str | None:
    """Guide the user to create a launch code on first run; returns its hash."""
    print("🔐 No launch code configured yet. Let's set one up (stored hashed).")
    try:
        code1 = getpass.getpass("🔑 Choose a launch code (min 4 chars): ").strip()
        if len(code1) < 4:
            print("❌ Code too short. Aborting setup.")
            return None
        code2 = getpass.getpass("🔁 Re-enter to confirm: ").strip()
        if code1 != code2:
            print("❌ Codes did not match. Aborting setup.")
            return None
        h = _hash_code(code1)
        try:
            _HASH_FILE.write_text(h, encoding="utf-8")
            try:
                os.chmod(_HASH_FILE, 0o600)
            except Exception:
                pass
            print(f"✅ Launch code saved (hash only) to {_HASH_FILE.name}")
        except Exception as e:
            print(f"⚠️ Could not persist hash ({e}). Set ALICE_LAUNCH_CODE_HASH instead:")
            print(f"   {h}")
        return h
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled.")
        return None

def clear_screen():
    """Clear the terminal screen"""
    # SECURITY: fixed arguments, shell-free.
    subprocess.run(["cls" if os.name == "nt" else "clear"], shell=False, check=False)

def print_alice_banner():
    """Display Alice startup banner"""
    print("=" * 60)
    print("🤖 ALICE AI ASSISTANT - SECURITY LAUNCHER 🔒")
    print("=" * 60)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🔐 Security Authentication Required")
    print("=" * 60)
    print("✨ NEW: Alice now has VISION & OCR capabilities! 👁️")
    print("📖 Can read text from images and screen content")
    print("🎤 Try: 'Alice, read the text on my screen'")
    print("=" * 60)

def get_secure_code():
    """Get the launch code from user with hidden input"""
    try:
        # Use getpass for hidden input (like password entry)
        code = getpass.getpass("🔑 Enter launch code: ")
        return code.strip()
    except KeyboardInterrupt:
        print("\n❌ Authentication cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Input error: {e}")
        return None

def validate_code(entered_code, expected_hash):
    """Validate the entered code against the configured hash (constant-time)."""
    if not entered_code:
        return False, "Code cannot be empty"

    if hmac.compare_digest(_hash_code(entered_code), expected_hash):
        return True, "Code validated successfully"
    return False, "Invalid security code"

def resolve_python_exe():
    """Find the best Python executable to run Alice agent"""
    alice_path = os.path.join(os.path.dirname(__file__), "Alice_code")
    _venv_candidates = [
        os.path.join(alice_path, "venv", "Scripts", "python.exe"),          # venv inside Alice_code (NEW!)
        os.path.join(alice_path, "venv_new", "Scripts", "python.exe"),      # legacy name
        r"D:\ProjectAlice\venv\Scripts\python.exe",                         # shared ProjectAlice venv (fallback)
        os.path.join(os.path.dirname(alice_path), "venv", "Scripts", "python.exe"),  # sibling venv
    ]
    found_python = next((p for p in _venv_candidates if os.path.exists(p)), sys.executable)
    print(f"🐍 Using Python: {found_python}")
    return found_python

def check_alice_vision_system():
    """Quick check to ensure vision/OCR capabilities are available"""
    try:
        python_exe = resolve_python_exe()
        alice_path = os.path.join(os.path.dirname(__file__), "Alice_code")
        
        # Run import and length check in a subprocess using correct python_exe
        check_code = (
            "import sys; "
            f"sys.path.insert(0, r'{alice_path}'); "
            "from alice_vision_tools import ALICE_VISION_TOOLS; "
            "print(len(ALICE_VISION_TOOLS))"
        )
        res = subprocess.run(
            [python_exe, "-c", check_code],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
        # Get only the last line that should be the count
        output_lines = res.stdout.strip().split('\n')
        vision_count = int(output_lines[-1])
        if vision_count >= 11:  # Should have 11 tools including OCR
            print(f"✅ Vision System: {vision_count} tools ready (including OCR)")
            return True
        else:
            print(f"⚠️ Vision System: Only {vision_count} tools found")
            return False
            
    except Exception as e:
        print(f"⚠️ Vision System: {str(e)[:100]}")
        return False

def start_alice():
    """Start Alice AI assistant with web interface"""
    alice_path = os.path.join(os.path.dirname(__file__), "Alice_code")
    react_path = os.path.join(os.path.dirname(__file__), "agent-starter-react")
    agent_file = os.path.join(alice_path, "agent.py")
    
    if not os.path.exists(agent_file):
        print(f"❌ Alice agent file not found at: {agent_file}")
        print("Please ensure Alice is properly installed.")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    if not os.path.exists(react_path):
        print(f"❌ Alice web interface not found at: {react_path}")
        print("Please ensure the agent-starter-react folder exists.")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    print("\n🚀 Starting Alice AI Assistant with Web Interface...")
    print("=" * 65)
    print("🔗 Alice will start both backend and web interface...")
    print("📱 Web Interface will be available at: http://localhost:3000")
    print("🤖 Backend will start on LiveKit WebSocket connection")
    print("👁️ Vision & OCR System: ENABLED (11 vision tools available)")
    print("📖 Alice can now read text from images and screen!")
    print("=" * 65)
    
    try:
        # Change to React app directory and start full Alice system
        os.chdir(react_path)
        
        print("\n⚡ Initializing Alice Full System...")
        print("🌐 Starting Backend Agent + Web Interface...")
        print("-" * 50)
        
        # Try different npm/pnpm commands to handle PATH issues
        # pnpm is the primary package manager (pnpm-lock.yaml present)
        npm_commands = ["pnpm", "pnpm.cmd", "npm", "npm.cmd"]
        npm_found = None
        
        for npm_cmd in npm_commands:
            try:
                # Test if command exists
                subprocess.run([npm_cmd, "--version"], capture_output=True, check=True, timeout=5)
                npm_found = npm_cmd
                break
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        if not npm_found:
            print("❌ npm/pnpm not found. Trying alternative startup method...")
            print("🔄 Starting Alice backend only...")
            
            # Fallback: Start only the backend
            os.chdir(alice_path)
            python_exe = resolve_python_exe()
            print(f"🐍 Using Python: {python_exe}")
            
            
            process = subprocess.Popen(
            
                [python_exe, "agent.py", "dev"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                universal_newlines=True
            )
        else:
            print(f"✅ Found package manager: {npm_found}")
            # Use the dev script which starts both backend and frontend
            process = subprocess.Popen(
                [npm_found, "run", "dev"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                universal_newlines=True
            )
        
        print("📡 Alice System Status:")
        print("-" * 40)
        
        # Read output line by line and display
        try:
            for line in process.stdout:
                line = line.strip()
                if line:
                    # Highlight important URLs and connection info
                    if any(keyword in line.lower() for keyword in ['http://localhost', 'local:', 'ready', 'compiled']):
                        print(f"🔗 {line}")
                    elif any(keyword in line.lower() for keyword in ['error', 'failed', 'exception']):
                        print(f"❌ {line}")
                    elif any(keyword in line.lower() for keyword in ['info', 'starting', 'listening', 'success']):
                        print(f"✅ {line}")
                    else:
                        print(f"   {line}")
                        
                    # Show access instructions when ready
                    if "ready" in line.lower() and "localhost" in line.lower():
                        print(f"\n{'='*50}")
                        print(f"🎉 ALICE IS READY!")
                        print(f"🌐 Web Interface: http://localhost:3000")
                        print(f"🤖 Open the link above to interact with Alice!")
                        print(f"{'='*50}\n")
                    elif "localhost" in line.lower() and any(port in line for port in ["3000", "8000", "5000"]):
                        print(f"\n{'='*50}")
                        print(f"🎉 ALICE BACKEND IS READY!")
                        print(f"🤖 Backend running - check output for connection details")
                        print(f"{'='*50}\n")
                        
        except KeyboardInterrupt:
            print("\n👋 Alice shutdown requested by user")
            process.terminate()
        
        # Wait for process to complete
        process.wait()
        
    except KeyboardInterrupt:
        print("\n👋 Alice shutdown requested by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting Alice: {e}")
        input("\nPress Enter to exit...")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        input("\nPress Enter to exit...")

def main():
    """Main security launcher function"""
    max_attempts = 3
    attempts = 0

    clear_screen()

    # SECURITY: load the configured launch-code hash; guide first-run setup.
    expected_hash = _get_expected_hash()
    if not expected_hash:
        print_alice_banner()
        expected_hash = _first_run_setup()
        if not expected_hash:
            print("❌ No launch code configured. Exiting.")
            sys.exit(1)
        clear_screen()

    while attempts < max_attempts:
        print_alice_banner()

        if attempts > 0:
            remaining = max_attempts - attempts
            print(f"⚠️  Attempts remaining: {remaining}")
            print()

        # Get security code from user
        entered_code = get_secure_code()

        if entered_code is None:
            attempts += 1
            clear_screen()
            continue

        # Validate the code
        is_valid, message = validate_code(entered_code, expected_hash)
        
        if is_valid:
            print(f"\n✅ {message}")
            print("🔓 Access granted! Initializing Alice...")
            print()
            
            # Check vision system
            print("🔍 Checking Alice Vision & OCR System...")
            vision_ready = check_alice_vision_system()
            
            if vision_ready:
                print("🎉 All systems ready!")
            else:
                print("⚠️ Vision system may have issues, but Alice will still start")
            
            # Wait a moment for effect
            import time
            time.sleep(2)
            
            # Start Alice
            start_alice()
            break
        else:
            attempts += 1
            clear_screen()
            print("❌ AUTHENTICATION FAILED")
            print(f"Reason: {message}")
            print()
            
            if attempts >= max_attempts:
                print("🚨 Maximum attempts exceeded!")
                print("Access denied. Exiting for security.")
                input("\nPress Enter to exit...")
                sys.exit(1)
            else:
                input("Press Enter to try again...")
                clear_screen()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! Alice trigger cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        input("Press Enter to exit...")
        sys.exit(1)