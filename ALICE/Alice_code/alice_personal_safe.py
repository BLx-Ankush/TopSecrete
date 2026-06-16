"""
Alice Personal Mode - Safe Integration Version
Comprehensive app discovery and mapping for opening any app on the system
"""

import subprocess
import os
import winreg
import json
import sys
from pathlib import Path
from datetime import datetime
from livekit.agents import function_tool
import logging

# Set UTF-8 encoding for Windows console to handle emojis
if os.name == 'nt':
    try:
        # SECURITY: fixed arguments, shell-free (replaces os.system('chcp ...')).
        subprocess.run(["chcp", "65001"], shell=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except Exception:
        pass

# Configure logging with UTF-8 encoding support
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ── Hardened safe-execution layer (Phase 1/2 security hardening) ──────────────
# All OS launches/file-opens/searches that previously used shell=True with
# interpolated user input are routed through alice_security, which validates
# input and executes with shell=False / OS APIs (no shell command line).
from alice_security import (
    SecurityValidationError,
    launch_app as _safe_launch_app,
    launch_executable as _safe_launch_executable,
    open_path_with as _safe_open_path_with,
    open_url as _safe_open_url,
    launch_protocol as _safe_launch_protocol,
    search_files as _safe_search_files,
)

# Global variables
PERSONAL_MODE_ENABLED = True  # Enable by default for better user experience
APP_DATABASE = {}
DATABASE_FILE = Path("alice_app_database.json")

class AppDiscovery:
    def __init__(self):
        self.apps = {}
        
    def scan_registry_apps(self):
        """Scan Windows Registry for installed applications"""
        registry_paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        ]
        
        for reg_path in registry_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    app_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                    try:
                                        install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                        if install_location and os.path.exists(install_location):
                                            # Find executables in install location
                                            self.find_executables_in_directory(install_location, app_name)
                                    except FileNotFoundError:
                                        pass
                                    
                                    # Try to get direct executable path
                                    try:
                                        display_icon = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                                        if display_icon.endswith('.exe') and os.path.exists(display_icon):
                                            self.apps[app_name.lower()] = display_icon
                                    except:
                                        pass
                                        
                                except FileNotFoundError:
                                    pass
                        except Exception as e:
                            continue
            except Exception as e:
                logger.error(f"Registry scan error: {e}")
                continue
    
    def find_executables_in_directory(self, directory, app_name):
        """Find executable files in a given directory"""
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.exe'):
                        full_path = os.path.join(root, file)
                        # Create multiple name variations
                        exe_name = file.replace('.exe', '').lower()
                        self.apps[exe_name] = full_path
                        self.apps[app_name.lower()] = full_path
                        
                        # Add common variations
                        if ' ' in app_name:
                            self.apps[app_name.replace(' ', '').lower()] = full_path
                        
                # Limit search depth for performance
                if root.count(os.sep) - directory.count(os.sep) > 3:
                    dirs[:] = []
        except Exception as e:
            pass
    
    def scan_common_directories(self):
        """Scan common installation directories"""
        common_dirs = [
            "C:\\Program Files",
            "C:\\Program Files (x86)",
            os.path.expanduser("~\\AppData\\Local"),
            os.path.expanduser("~\\AppData\\Roaming"),
            "C:\\Users\\Public\\Desktop",
            os.path.expanduser("~\\Desktop"),
            "C:\\Windows\\System32"
        ]
        
        for base_dir in common_dirs:
            if os.path.exists(base_dir):
                try:
                    for item in os.listdir(base_dir):
                        item_path = os.path.join(base_dir, item)
                        if os.path.isdir(item_path) and not item.startswith('.'):
                            self.find_executables_in_directory(item_path, item)
                except Exception:
                    continue
    
    def add_essential_system_apps(self):
        """Add essential system applications with known paths"""
        essential_apps = {
            # Browsers with multiple name variations
            "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "google chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "google": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",  # NEW: Google alias for Chrome
            "googlechrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            
            "firefox": "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
            "mozilla firefox": "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
            
            "edge": "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
            "microsoft edge": "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
            "msedge": "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
            
            # Development Tools
            "vscode": "C:\\Program Files\\Microsoft VS Code\\Code.exe",
            "vs code": "C:\\Program Files\\Microsoft VS Code\\Code.exe",
            "visual studio code": "C:\\Program Files\\Microsoft VS Code\\Code.exe",
            "code": "C:\\Program Files\\Microsoft VS Code\\Code.exe",
            
            # Communication Apps
            "discord": "C:\\Users\\%USERNAME%\\AppData\\Local\\Discord\\app-1.0.9156\\Discord.exe",
            "zoom": "C:\\Program Files\\Zoom\\bin\\Zoom.exe",
            
            # Perplexity/Comet (appears to be installed based on database)
            "comet": "C:\\Users\\%USERNAME%\\AppData\\Local\\Perplexity\\Comet\\Application\\comet.exe",
            "perplexity": "C:\\Users\\%USERNAME%\\AppData\\Local\\Perplexity\\Comet\\Application\\comet.exe",
            
            # Video Editing
            "capcut": "C:\\Program Files\\CapCut\\CapCut.exe",
            "cap cut": "C:\\Program Files\\CapCut\\CapCut.exe",
            
            # System Tools
            "notepad": "C:\\Windows\\System32\\notepad.exe",
            "calculator": "C:\\Windows\\System32\\calc.exe",
            "paint": "C:\\Windows\\System32\\mspaint.exe",
            "wordpad": "C:\\Program Files\\Windows NT\\Accessories\\wordpad.exe",
            "cmd": "C:\\Windows\\System32\\cmd.exe",
            "command prompt": "C:\\Windows\\System32\\cmd.exe",
            "powershell": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
            "control panel": "C:\\Windows\\System32\\control.exe",
            "task manager": "C:\\Windows\\System32\\taskmgr.exe",
            "registry editor": "C:\\Windows\\regedit.exe",
            "device manager": "C:\\Windows\\System32\\devmgmt.msc",
            "services": "C:\\Windows\\System32\\services.msc",
            
            # Microsoft Office (common locations)
            "word": "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
            "excel": "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
            "powerpoint": "C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE",
            "outlook": "C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE",
            
            # Alternative Office locations
            "microsoft word": "C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
            "microsoft excel": "C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
            "microsoft powerpoint": "C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\POWERPNT.EXE",
        }
        
        # Expand environment variables and check if apps exist
        for app_name, app_path in essential_apps.items():
            expanded_path = os.path.expandvars(app_path)
            
            # For apps that might not exist, add common alternative locations
            paths_to_try = [expanded_path]
            
            # Add alternative Discord locations
            if "discord" in app_name:
                paths_to_try.extend([
                    "C:\\Users\\%USERNAME%\\AppData\\Local\\Discord\\Update.exe",
                    "C:\\Users\\%USERNAME%\\AppData\\Roaming\\Discord\\Discord.exe",
                    "C:\\Users\\%USERNAME%\\AppData\\Local\\Discord\\app-1.0.9155\\Discord.exe",
                    "C:\\Users\\%USERNAME%\\AppData\\Local\\Discord\\app-1.0.9157\\Discord.exe",
                ])
            
            # Add alternative VS Code locations with priority for actual executable
            elif "vscode" in app_name or "vs code" in app_name or app_name == "code":
                paths_to_try = [  # Override with correct priority
                    "C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
                    "C:\\Program Files\\Microsoft VS Code\\Code.exe",
                    "C:\\Program Files (x86)\\Microsoft VS Code\\Code.exe"
                ]
            
            # Add alternative Firefox locations  
            elif "firefox" in app_name or "mozilla firefox" in app_name:
                paths_to_try.extend([
                    "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe"
                ])
            
            # Add alternative Zoom locations
            elif "zoom" in app_name:
                paths_to_try.extend([
                    "C:\\Program Files (x86)\\Zoom\\bin\\Zoom.exe",
                    "C:\\Users\\%USERNAME%\\AppData\\Roaming\\Zoom\\bin\\Zoom.exe"
                ])
            
            # CapCut - only use start command since it may not be installed
            elif "capcut" in app_name or "cap cut" in app_name:
                paths_to_try = [f'start "" "{app_name}"']  # Direct start command
            
            # Try each path until one exists
            for path_to_try in paths_to_try:
                expanded_try_path = os.path.expandvars(path_to_try)
                if os.path.exists(expanded_try_path):
                    self.apps[app_name] = expanded_try_path
                    # Add variations without spaces
                    if ' ' in app_name:
                        self.apps[app_name.replace(' ', '')] = expanded_try_path
                    break
            else:
                # If no path exists, still add it for fallback Windows start command
                self.apps[app_name] = f'start "" "{app_name}"'
    
    def scan_start_menu(self):
        """Scan Windows Start Menu shortcuts"""
        start_menu_paths = [
            "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
            os.path.expanduser("~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs")
        ]
        
        for start_path in start_menu_paths:
            if os.path.exists(start_path):
                try:
                    for root, dirs, files in os.walk(start_path):
                        for file in files:
                            if file.endswith('.lnk'):
                                shortcut_name = file.replace('.lnk', '').lower()
                                # Try to resolve shortcut to actual executable
                                try:
                                    # Simple approach - store shortcut name for start command
                                    self.apps[shortcut_name] = f'start "" "{file.replace(".lnk", "")}"'
                                except:
                                    pass
                except Exception:
                    continue
    
    def add_system_apps(self):
        """Add common Windows system applications"""
        system_apps = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "wordpad": "write.exe",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "powershell": "powershell.exe",
            "terminal": "wt.exe",
            "windows terminal": "wt.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "control panel": "control.exe",
            "task manager": "taskmgr.exe",
            "registry editor": "regedit.exe",
            "device manager": "devmgmt.msc",
            "services": "services.msc",
            "event viewer": "eventvwr.exe",
            "disk management": "diskmgmt.msc",
            "character map": "charmap.exe",
            "snipping tool": "SnippingTool.exe",
            "magnifier": "magnify.exe",
            "narrator": "narrator.exe",
            "on-screen keyboard": "osk.exe"
        }
        
        for app_name, exe_path in system_apps.items():
            self.apps[app_name] = exe_path
    
    def discover_all_apps(self):
        """Complete app discovery process"""
        logger.info("[*] Starting comprehensive app discovery...")
        
        # Add system apps first
        self.add_system_apps()
        logger.info(f"[+] Added {len(self.apps)} system apps")
        
        # Add essential system apps (Chrome, Office, etc.)
        initial_count = len(self.apps)
        self.add_essential_system_apps()
        logger.info(f"[+] Added {len(self.apps) - initial_count} essential system apps")
        
        # Scan registry
        initial_count = len(self.apps)
        self.scan_registry_apps()
        logger.info(f"[+] Registry scan added {len(self.apps) - initial_count} apps")
        
        # Scan common directories
        initial_count = len(self.apps)
        self.scan_common_directories()
        logger.info(f"[+] Directory scan added {len(self.apps) - initial_count} apps")
        
        # Scan start menu
        initial_count = len(self.apps)
        self.scan_start_menu()
        logger.info(f"[+] Start menu scan added {len(self.apps) - initial_count} apps")
        
        logger.info(f"[*] Total apps discovered: {len(self.apps)}")
        return self.apps

def load_app_database():
    """Load app database from file or create new one"""
    global APP_DATABASE
    
    if DATABASE_FILE.exists():
        try:
            with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                APP_DATABASE = json.load(f)
            logger.info(f"📂 Loaded {len(APP_DATABASE)} apps from database")
            return True
        except Exception as e:
            logger.error(f"Database load error: {e}")
    
    return False

def save_app_database():
    """Save app database to file"""
    try:
        with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
            json.dump(APP_DATABASE, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Saved {len(APP_DATABASE)} apps to database")
    except Exception as e:
        logger.error(f"Database save error: {e}")

def refresh_app_database():
    """Refresh the app database by scanning the system"""
    global APP_DATABASE
    
    discovery = AppDiscovery()
    APP_DATABASE = discovery.discover_all_apps()
    save_app_database()
    
    return len(APP_DATABASE)

@function_tool(
    name="enable_personal_mode",
    description="Alice को personal mode enable करने के लिए - full system access मिलेगा"
)
async def enable_personal_mode() -> str:
    """Enable Alice's personal mode for full system control"""
    global PERSONAL_MODE_ENABLED, APP_DATABASE
    PERSONAL_MODE_ENABLED = True
    
    # Load or refresh app database
    if not load_app_database():
        app_count = refresh_app_database()
        logger.info("Alice Personal Mode Activated with fresh app scan")
        return f"""✅ **Personal Mode Activated!**

🔍 System scan complete - {app_count} apps discovered और mapped!

अब मैं आपकी system के हर app को open कर सकती हूँ:
🚀 Any app: "chrome open karo", "word open karo", "spotify open karo" 
📱 System apps: "notepad", "calculator", "task manager"
🎮 Games: "steam open karo" (if installed)
💻 Dev tools: "vscode open karo", "git bash open karo"

बस app का नाम बता दीजिए! मैं तुरंत खोल दूंगी 💕😊"""
    else:
        logger.info("Alice Personal Mode Activated with existing database")
        return f"""✅ **Personal Mode Activated!**

📂 {len(APP_DATABASE)} apps loaded from database!

Ready to open any application! Commands:
- "app का नाम open karo"  
- "refresh app database" (नए apps के लिए)
- "show available apps" (list देखने के लिए)

कौन सा app खोलना है? मैं खुशी से help करूंगी! 💖🚀"""

@function_tool(
    name="refresh_app_database",
    description="System को rescan करके नए apps find करने के लिए"
)
async def refresh_app_database_tool() -> str:
    """Refresh the application database by scanning the system"""
    if not PERSONAL_MODE_ENABLED:
        return "🔐 Personal mode enable करें पहले!"
    
    try:
        app_count = refresh_app_database()
        return f"""🔄 **Database Refreshed!**

✅ {app_count} total apps discovered और mapped
🔍 Registry, Program Files, Start Menu सभी scan किए गए
💾 Database updated और saved

अब कोई भी नया installed app open कर सकते हैं! 🎯"""
    
    except Exception as e:
        logger.error(f"Database refresh error: {e}")
        return f"Database refresh में error: {str(e)} 😔"

@function_tool(
    name="show_available_apps",
    description="Available apps की list show करने के लिए"
)
async def show_available_apps(search_term: str = "") -> str:
    """Show list of available applications"""
    if not PERSONAL_MODE_ENABLED:
        return "🔐 Personal mode enable करें पहले!"
    
    if not APP_DATABASE:
        return "❌ App database empty! 'refresh app database' करें।"
    
    try:
        if search_term:
            # Filter apps by search term
            filtered_apps = {k: v for k, v in APP_DATABASE.items() if search_term.lower() in k.lower()}
            if not filtered_apps:
                return f"'{search_term}' के लिए कोई app नहीं मिला। Different keyword try करें।"
            
            result = f"🔍 **Apps matching '{search_term}':**\n\n"
            for i, app_name in enumerate(list(filtered_apps.keys())[:15], 1):
                result += f"{i}. {app_name.title()}\n"
            
            if len(filtered_apps) > 15:
                result += f"\n... and {len(filtered_apps) - 15} more apps"
                
            return result + f"\n\nबस 'app_name open karo' कह दीजिए! मैं तुरंत खोल दूंगी 💕😊"
        
        else:
            # Show random sample of apps
            import random
            sample_apps = random.sample(list(APP_DATABASE.keys()), min(20, len(APP_DATABASE)))
            
            result = f"📱 **Available Apps (Sample from {len(APP_DATABASE)} total):**\n\n"
            for i, app_name in enumerate(sample_apps, 1):
                result += f"{i}. {app_name.title()}\n"
            
            result += f"\n🔍 Specific search: 'show apps chrome' या 'show apps office'\n"
            result += f"📂 Total apps: {len(APP_DATABASE)}\n"
            result += f"💡 Usage: 'app_name open karo'"
            
            return result
            
    except Exception as e:
        logger.error(f"Show apps error: {e}")
        return f"Apps list में error: {str(e)} 😔"

@function_tool(
    name="disable_personal_mode", 
    description="Alice को basic mode में वापस करने के लिए"
)
async def disable_personal_mode() -> str:
    """Disable Alice's personal mode"""
    global PERSONAL_MODE_ENABLED
    PERSONAL_MODE_ENABLED = False
    logger.info("Alice Personal Mode Deactivated")
    return "❌ Personal mode disabled. Basic mode में वापस आ गई हूँ। Safe mode! 🔐"

@function_tool(
    name="open_application",
    description="कोई भी application open करने के लिए - system में कोई भी app (chrome, word, spotify, games आदि)"
)
async def open_application(app_name: str) -> str:
    """Open any application on the system using comprehensive app database"""
    
    # Allow certain common apps without personal mode
    allowed_without_personal_mode = ['whatsapp', 'whatsapp desktop']
    
    if not PERSONAL_MODE_ENABLED and app_name.lower() not in allowed_without_personal_mode:
        return "🔐 Personal mode enable करें पहले! 'enable personal mode' कहें।"
    
    if not APP_DATABASE:
        # Try to load database, if fails then scan
        if not load_app_database():
            app_count = refresh_app_database()
            logger.info(f"Created fresh database with {app_count} apps")
    
    try:
        app_lower = app_name.lower().strip()
        exe_path = None
        matched_name = None
        
        # Priority overrides for specific apps to ensure correct matching
        priority_overrides = {
            "google": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "google chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", 
            "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "vs code": "C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
            "vscode": "C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
            "code": "C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
            "discord": "C:\\Users\\%USERNAME%\\AppData\\Local\\Discord\\Update.exe",
            "firefox": "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
            "mozilla firefox": "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
            "whatsapp": "C:\\Users\\%USERNAME%\\AppData\\Local\\WhatsApp\\WhatsApp.exe",
            "whatsapp desktop": "C:\\Users\\%USERNAME%\\AppData\\Local\\WhatsApp\\WhatsApp.exe"
        }
        
        # Method 0: Check priority overrides first
        if app_lower in priority_overrides:
            test_path = os.path.expandvars(priority_overrides[app_lower])
            if os.path.exists(test_path):
                exe_path = test_path
                matched_name = app_lower
        
        # Special handling for WhatsApp with multiple possible paths
        if not exe_path and app_lower in ["whatsapp", "whatsapp desktop"]:
            whatsapp_paths = [
                os.path.expandvars("C:\\Users\\%USERNAME%\\AppData\\Local\\WhatsApp\\WhatsApp.exe"),
                "C:\\Program Files\\WhatsApp\\WhatsApp.exe",
                "C:\\Program Files (x86)\\WhatsApp\\WhatsApp.exe"
            ]
            
            # Check for Windows Store WhatsApp installation
            try:
                import subprocess
                # SECURITY: static command, shell=False arg-list (no shell).
                result = subprocess.run(
                    ['powershell.exe', '-Command', 'Get-AppxPackage *WhatsApp*'],
                    shell=False, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=5
                )
                if "5319275A.WhatsAppDesktop" in result.stdout:
                    logger.info("Found WhatsApp Store app installed")
                    # Use store app if desktop version not found
            except Exception as e:
                logger.debug(f"WhatsApp store check failed: {e}")
            
            for path in whatsapp_paths:
                if os.path.exists(path):
                    exe_path = path
                    matched_name = "whatsapp"
                    break
        
        # Method 1: Exact match (if no override found)
        if not exe_path and app_lower in APP_DATABASE:
            exe_path = APP_DATABASE[app_lower]
            matched_name = app_lower
        
        # Method 2: Partial match - find best match with proper prioritization
        if not exe_path:
            best_matches = []
            exact_matches = []
            partial_matches = []
            
            # Exclude web apps when looking for desktop apps
            excluded_web_terms = ['web', 'online', 'browser', 'chrome app']
            
            for app_key in APP_DATABASE.keys():
                # Skip web versions if looking for desktop app
                if app_lower == "whatsapp" and any(term in app_key.lower() for term in excluded_web_terms):
                    continue
                    
                if app_lower == app_key:  # Exact match
                    exact_matches.append((app_key, APP_DATABASE[app_key]))
                elif app_lower in app_key or app_key in app_lower:
                    # Prioritize non-web apps
                    priority_score = 0
                    if not any(term in app_key.lower() for term in excluded_web_terms):
                        priority_score += 10
                    if app_key.startswith(app_lower):
                        priority_score += 5
                    partial_matches.append((priority_score, app_key, APP_DATABASE[app_key]))
            
            # Use exact matches first, then best partial matches
            if exact_matches:
                best_matches = exact_matches
            elif partial_matches:
                partial_matches.sort(key=lambda x: x[0], reverse=True)
                best_matches = [(x[1], x[2]) for x in partial_matches[:3]]
            
            if best_matches:
                # Sort by length to get best match (shortest usually better)
                best_matches.sort(key=lambda x: len(x[0]))
                matched_name, exe_path = best_matches[0]
        
        # Special handling for WhatsApp to ensure proper opening
        if app_lower in ["whatsapp", "whatsapp desktop"] and (not exe_path or "web" in matched_name.lower() if matched_name else False):
            # Force use of working WhatsApp protocol instead of problematic paths
            try:
                import webbrowser
                webbrowser.open('whatsapp:')
                return f"✅ WhatsApp opened successfully! 🚀\n\n🎯 Using WhatsApp protocol\n🚀 Desktop app launched\n\nऔर कुछ help चाहिए? मैं यहाँ हूँ! 💕😊"
            except Exception as e:
                logger.debug(f"WhatsApp protocol failed: {e}")
        
        # Method 3: If we have a path, try to launch it
        if exe_path and matched_name:
            try:
                # SECURITY: launch the resolved executable via the hardened
                # safe-execution layer (shell=False / ShellExecute). No user
                # string is ever interpolated into a shell command line.
                success = False
                try:
                    _safe_launch_executable(exe_path)
                    success = True
                except SecurityValidationError as sec_err:
                    logger.warning(f"Blocked unsafe launch of '{exe_path}': {sec_err}")
                    success = False

                if success:
                    return f"""✅ **{app_name.title()} Successfully Opened!**

🎯 Matched: {matched_name}
🚀 Path: {exe_path[:50]}{'...' if len(exe_path) > 50 else ''}

और कुछ help चाहिए? मैं यहाँ हूँ! 💕😊"""
                else:
                    raise Exception("All launch methods failed")
            
            except subprocess.TimeoutExpired:
                return f"⏰ {app_name} opening... (timeout हुआ लेकिन process start हो गया होगा)"
            except Exception as launch_error:
                logger.error(f"Launch error for {app_name}: {launch_error}")
                # SECURITY: shell-free fallback. os.startfile/association resolves
                # the name the same way `start "<name>"` did, with no shell.
                try:
                    _safe_launch_app(app_name, app_database=APP_DATABASE)
                    return f"✅ {app_name} opened via Windows fallback! 🎯"
                except SecurityValidationError as sec_err:
                    logger.warning(f"Blocked unsafe app launch '{app_name}': {sec_err}")
                    return f"❌ '{app_name}' contains unsupported characters."
                except Exception:
                    return f"❌ {app_name} launch failed: {str(launch_error)}"

        # Method 4: Enhanced fallback — shell-free bare-name / protocol launch.
        # SECURITY: replaces the previous list of interpolated PowerShell/cmd/
        # start command strings. A single validated os.startfile call covers all
        # of them (Windows resolves the name via app associations) with no shell.

        # Special WhatsApp store app fallback (protocol launch, no shell)
        if app_lower in ["whatsapp", "whatsapp desktop"]:
            try:
                _safe_launch_protocol('whatsapp:')
                return f"✅ WhatsApp opened successfully! 🚀"
            except Exception as e:
                logger.debug(f"WhatsApp protocol failed: {e}")
            try:
                _safe_launch_protocol('ms-windows-store://pdp/?ProductId=9NKSQGP7F2NH')
                return f"✅ WhatsApp opened via Store! 🚀"
            except Exception as e:
                logger.debug(f"WhatsApp store launch failed: {e}")

        # Generic shell-free bare-name launch
        try:
            _safe_launch_app(app_name, app_database=APP_DATABASE)
            return f"✅ {app_name} opened via Windows search! ✨"
        except SecurityValidationError as sec_err:
            logger.warning(f"Blocked unsafe app launch '{app_name}': {sec_err}")
            return f"❌ '{app_name}' contains unsupported characters and was not launched."
        except Exception as e:
            logger.debug(f"Bare-name launch failed for {app_name}: {e}")
        
        # Method 5: Try to search for the app in registry and common locations
        try:
            potential_paths = [
                f"C:\\Program Files\\{app_name}\\{app_name}.exe",
                f"C:\\Program Files (x86)\\{app_name}\\{app_name}.exe",
                f"C:\\Program Files\\{app_name.title()}\\{app_name.lower()}.exe",
                f"C:\\Program Files (x86)\\{app_name.title()}\\{app_name.lower()}.exe",
            ]
            
            for path in potential_paths:
                if os.path.exists(path):
                    try:
                        import subprocess
                        subprocess.Popen([path], shell=False)
                        return f"✅ {app_name} opened from discovered path: {path}! 🔍"
                    except:
                        continue
        except:
            pass
        
        # If nothing worked, provide helpful suggestions
        suggestions = []
        for app_key in list(APP_DATABASE.keys())[:10]:
            if any(word in app_key for word in app_lower.split()):
                suggestions.append(app_key.title())
        
        result = f"❌ Sorry! '{app_name}' नहीं मिला।\n\n"
        
        if suggestions:
            result += f"🤔 Did you mean:\n"
            for i, suggestion in enumerate(suggestions[:5], 1):
                result += f"{i}. {suggestion}\n"
        
        result += f"\n💡 Try:\n"
        result += f"• 'show available apps' - full list देखने के लिए\n"
        result += f"• 'show apps {app_name}' - search करने के लिए\n"
        result += f"• 'refresh app database' - नए apps scan करने के लिए"
        
        return result
        
    except Exception as e:
        logger.error(f"Error opening app {app_name}: {e}")
        return f"App opening में error आया। Error: {str(e)}\n\nTry 'refresh app database' या different app name। 😔"

@function_tool(
    name="perform_multi_app_task",
    description="Multiple apps को एक साथ open करके different tasks perform करने के लिए"
)
async def perform_multi_app_task(task_description: str) -> str:
    """
    Perform complex tasks involving multiple applications
    
    Args:
        task_description: Description of the multi-app task to perform
    """
    if not PERSONAL_MODE_ENABLED:
        return "🔐 Personal mode enable करें पहले! Multi-app tasks के लिए जरूरी है।"
    
    try:
        results = []
        
        # Parse task description and perform appropriate actions
        task_lower = task_description.lower()
        
        if "research" in task_lower and "notepad" in task_lower:
            # Research task with notepad
            results.append("🔍 Starting research and documentation task...")
            
            # Open Chrome for research
            chrome_result = await open_application("chrome")
            results.append(f"Browser: {chrome_result}")
            
            # Open Notepad for notes
            notepad_result = await open_application("notepad")
            results.append(f"Notepad: {notepad_result}")
            
            results.append("✅ Research setup complete! Chrome + Notepad ready for research work.")
            
        elif "presentation" in task_lower:
            # Presentation creation task
            results.append("🎯 Starting presentation creation task...")
            
            # Open PowerPoint
            ppt_result = await open_application("powerpoint")
            results.append(f"PowerPoint: {ppt_result}")
            
            # Open Chrome for research
            chrome_result = await open_application("chrome")
            results.append(f"Chrome: {chrome_result}")
            
            results.append("✅ Presentation setup complete! PowerPoint + Chrome ready.")
            
        elif "development" in task_lower or "coding" in task_lower:
            # Development environment setup
            results.append("💻 Setting up development environment...")
            
            # Try to open VS Code
            vscode_result = await open_application("vscode")
            results.append(f"VS Code: {vscode_result}")
            
            # Open terminal/cmd
            cmd_result = await open_application("cmd")
            results.append(f"Terminal: {cmd_result}")
            
            # Open browser for documentation
            chrome_result = await open_application("chrome")
            results.append(f"Browser: {chrome_result}")
            
            results.append("✅ Development environment ready!")
            
        elif "office work" in task_lower:
            # Office productivity setup
            results.append("📊 Setting up office productivity suite...")
            
            apps_to_open = ["word", "excel", "outlook"]
            for app in apps_to_open:
                app_result = await open_application(app)
                results.append(f"{app.title()}: {app_result}")
            
            results.append("✅ Office suite ready for productivity!")
            
        else:
            # Generic multi-app opening based on keywords
            results.append("🚀 Opening multiple apps based on task description...")
            
            # Extract app names from task description
            app_keywords = {
                "notepad": "notepad", "calculator": "calculator", "paint": "paint",
                "chrome": "chrome", "browser": "chrome", "word": "word", 
                "excel": "excel", "powerpoint": "powerpoint", "explorer": "explorer"
            }
            
            opened_count = 0
            for keyword, app_name in app_keywords.items():
                if keyword in task_lower:
                    app_result = await open_application(app_name)
                    results.append(f"{app_name.title()}: {app_result}")
                    opened_count += 1
            
            if opened_count == 0:
                # Default: open basic productivity apps
                default_apps = ["notepad", "calculator", "explorer"]
                for app in default_apps:
                    app_result = await open_application(app)
                    results.append(f"{app.title()}: {app_result}")
            
            results.append(f"✅ Multi-app task setup complete!")
        
        return "\n\n".join(results) + "\n\nसारे apps ready हैं! अब क्या करना है? मैं help करूंगी 💕😊"
        
    except Exception as e:
        logger.error(f"Error in multi-app task: {e}")
        return f"Multi-app task में error आया: {str(e)}"

@function_tool(
    name="create_file_and_open",
    description="File create करके automatically app में open करने के लिए"
)
async def create_file_and_open(filename: str, content: str = "", app: str = "notepad") -> str:
    """
    Create a file with content and open it in specified application
    
    Args:
        filename: Name of file to create
        content: Content to write in file
        app: Application to open file with (default: notepad)
    """
    if not PERSONAL_MODE_ENABLED:
        return "🔐 Personal mode enable करें पहले!"
    
    try:
        import subprocess
        from pathlib import Path
        
        # Create file with content
        file_path = Path(filename)
        if not content:
            content = f"File created by Alice on {datetime.now()}\nFilename: {filename}"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Open file with specified app — SECURITY: shell-free, validated path.
        # The opener is a fixed program name; the path is passed as a separate
        # argv entry (open_path_with) or via ShellExecute (launch default).
        try:
            if app.lower() == "notepad":
                _safe_open_path_with("notepad.exe", str(file_path))
            elif app.lower() == "word":
                _safe_open_path_with("winword.exe", str(file_path))
            elif app.lower() == "excel":
                _safe_open_path_with("excel.exe", str(file_path))
            else:
                # Default association open (equivalent to `start "" "<file>"`)
                _safe_launch_executable(str(file_path))
        except SecurityValidationError as sec_err:
            logger.warning(f"Blocked unsafe file open '{file_path}': {sec_err}")
            return f"✅ File created at {filename}, but could not be opened (invalid path)."
        
        return f"✅ **File Created & Opened!**\n\n📁 File: {filename}\n💾 Size: {len(content)} characters\n🚀 Opened in: {app.title()}\n\nFile ready for editing! ✏️"
        
    except Exception as e:
        logger.error(f"Error creating and opening file: {e}")
        return f"File create करने में error: {str(e)}"

@function_tool(
    name="open_vscode_new_window",
    description="VS Code का new window open करने के लिए"
)
async def open_vscode_new_window(folder_path: str = "") -> str:
    """Open VS Code in a new window, optionally with a specific folder"""
    
    if not PERSONAL_MODE_ENABLED:
        return "🔐 Personal mode enable करें पहले!"
    
    try:
        import subprocess
        import os
        
        # VS Code command variations to try (program + args as LISTS, never
        # interpolated shell strings). SECURITY: shell=False everywhere.
        vscode_commands = [
            ["code", "--new-window"],
            ["Code.exe", "--new-window"],
            ["C:\\Program Files\\Microsoft VS Code\\Code.exe", "--new-window"],
            [os.path.expandvars("C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe"), "--new-window"],
        ]

        # If a folder path is provided, validate it and append as a separate arg.
        safe_folder = None
        if folder_path:
            try:
                from alice_security import validate_path as _vp
                safe_folder = _vp(folder_path, must_exist=True)
            except SecurityValidationError as sec_err:
                logger.warning(f"Ignoring unsafe VS Code folder path: {sec_err}")
                safe_folder = None
        if safe_folder:
            vscode_commands = [cmd + [safe_folder] for cmd in vscode_commands]

        success = False
        for cmd in vscode_commands:
            try:
                subprocess.Popen(cmd, shell=False)
                success = True
                break
            except Exception:
                continue

        if success:
            folder_info = f" with folder: {safe_folder}" if safe_folder else ""
            return f"✅ VS Code new window opened{folder_info}! 💻\n\nReady for coding! 🚀"
        else:
            return "❌ VS Code नहीं मिला। Install करें या path check करें। 🤔"
            
    except Exception as e:
        logger.error(f"Error opening VS Code: {e}")
        return f"VS Code opening में error: {str(e)} 😔"

@function_tool(
    name="open_browser",
    description="Firefox, Edge, या कोई भी browser open करने के लिए"
)
async def open_browser(browser: str, url: str = "") -> str:
    """Open specified browser with optional URL"""
    
    if not PERSONAL_MODE_ENABLED:
        return "🔐 Personal mode enable करें पहले!"
    
    try:
        import subprocess
        import os
        
        browser_commands = {
            "firefox": [
                "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
                "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe",
                "firefox.exe"
            ],
            "edge": [
                "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
                "msedge.exe"
            ],
            "chrome": [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
                "chrome.exe"
            ],
            "brave": [
                "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
                "brave.exe"
            ]
        }
        
        browser_lower = browser.lower()
        commands = browser_commands.get(browser_lower, [browser + ".exe"])

        # SECURITY: validate the URL once up front. Rejects javascript:/file:/
        # data: schemes and any shell metacharacters before it reaches a launch.
        safe_url = ""
        if url:
            try:
                from alice_security import validate_url as _vu
                safe_url = _vu(url)
            except SecurityValidationError as sec_err:
                logger.warning(f"Blocked unsafe browser URL: {sec_err}")
                return f"❌ The URL was rejected for security reasons."

        success = False
        used_command = ""

        # Try each command path until one works (all shell=False arg-lists)
        for cmd_path in commands:
            try:
                if os.path.exists(cmd_path):
                    if safe_url:
                        result = subprocess.Popen([cmd_path, safe_url], shell=False)
                    else:
                        result = subprocess.Popen([cmd_path], shell=False)
                    success = True
                    used_command = cmd_path
                    break
                else:
                    # Path not found at this location: try launching the browser
                    # by bare name via the safe layer (shell-free association),
                    # then hand off the URL to the default handler if needed.
                    try:
                        _safe_launch_app(browser_lower, app_database=APP_DATABASE)
                        if safe_url:
                            _safe_open_url(safe_url)
                        success = True
                        used_command = cmd_path
                        break
                    except Exception as e:
                        logger.debug(f"Safe launch of {browser_lower} failed: {e}")
                        continue
            except Exception as e:
                logger.debug(f"Failed to open {cmd_path}: {e}")
                continue

        if success:
            url_info = f" with URL: {safe_url}" if safe_url else ""
            return f"✅ {browser.title()} opened{url_info}! 🌐\n\nBrowsing ready! 📱\n\nUsed: {used_command}"
        else:
            return f"❌ {browser.title()} browser नहीं मिला। Install check करें। 🤔\n\nTried paths: {', '.join(commands[:2])}"
            
    except Exception as e:
        logger.error(f"Error opening browser {browser}: {e}")
        return f"Browser opening में error: {str(e)} 😔"

@function_tool(
    name="capture_screenshot",
    description="Screenshot capture करने के लिए - screen का photo लेता है"
)
async def capture_screenshot(filename: str = "") -> str:
    """Capture screenshot of the screen"""
    
    if not PERSONAL_MODE_ENABLED:
        return "🔐 Personal mode enable करें पहले!"
    
    try:
        import subprocess
        import os
        from datetime import datetime
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"alice_screenshot_{timestamp}.png"
        
        # Ensure .png extension
        if not filename.lower().endswith('.png'):
            filename += '.png'
        
        # Use PowerShell to capture screenshot
        powershell_cmd = f'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp = New-Object Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [Drawing.Graphics]::FromImage($bmp)
$graphics.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $bounds.Size)
$bmp.Save("{filename}")
$graphics.Dispose()
$bmp.Dispose()
'''
        
        # Execute PowerShell command
        result = subprocess.run(
            ['powershell', '-Command', powershell_cmd],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and os.path.exists(filename):
            file_size = os.path.getsize(filename)
            return f"✅ **Screenshot Captured!** 📸\n\n📁 File: {filename}\n💾 Size: {file_size // 1024} KB\n🖼️ Resolution: Full screen\n\nScreenshot saved successfully! 🎯"
        else:
            # Fallback: Use Windows Snipping Tool
            import subprocess
            subprocess.Popen(["snippingtool.exe"], shell=False)
            return "✅ Snipping Tool opened for manual screenshot! ✂️\n\nCapture your screenshot manually. 📷"
            
    except Exception as e:
        logger.error(f"Error capturing screenshot: {e}")
        # Another fallback: Print Screen key simulation
        try:
            import subprocess
            subprocess.Popen(["snippingtool.exe"], shell=False)
            return f"⚠️ Auto-screenshot failed, but Snipping Tool opened!\n\nError: {str(e)}\nUse Snipping Tool manually. ✂️"
        except:
            return f"❌ Screenshot capture में error: {str(e)} 😔"

@function_tool(
    name="adjust_brightness",
    description="Screen brightness increase या decrease करने के लिए"
)
async def adjust_brightness(action: str, value: int = 10) -> str:
    """Adjust screen brightness up or down"""
    
    if not PERSONAL_MODE_ENABLED:
        return "🔐 Personal mode enable करें पहले!"
    
    try:
        import subprocess
        
        action_lower = action.lower()
        
        if action_lower in ["increase", "up", "बढ़ाओ", "ऊपर"]:
            # Increase brightness using PowerShell
            powershell_cmd = f'''
(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, 100)
'''
            operation = "increased"
            icon = "☀️"
            
        elif action_lower in ["decrease", "down", "कम करो", "नीचे"]:
            # Decrease brightness
            powershell_cmd = f'''
(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, 30)
'''
            operation = "decreased"
            icon = "🌙"
            
        else:
            return "❌ Action specify करें: 'increase' या 'decrease'\n\nExample: 'brightness increase karo' 💡"
        
        # Execute brightness command
        try:
            result = subprocess.run(
                ['powershell', '-Command', powershell_cmd],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return f"✅ Screen brightness {operation}! {icon}\n\nBrightness adjustment successful! 🖥️"
            else:
                # Fallback: Open Windows Settings
                import subprocess
                _safe_launch_protocol("ms-settings:display")
                return f"⚠️ Direct brightness control failed.\n\nDisplay settings opened - adjust manually! ⚙️"
                
        except subprocess.TimeoutExpired:
            # Fallback: Use Windows key shortcuts simulation or settings
            import subprocess
            _safe_launch_protocol("ms-settings:display")
            return f"⚠️ Brightness command timeout.\n\nDisplay settings opened for manual adjustment! ⚙️"
            
    except Exception as e:
        logger.error(f"Error adjusting brightness: {e}")
        try:
            import subprocess
            _safe_launch_protocol("ms-settings:display")
            return f"❌ Brightness adjustment में error: {str(e)}\n\nDisplay settings opened as fallback! ⚙️"
        except:
            return f"❌ Brightness control error: {str(e)} 😔"

@function_tool(
    name="search_files_system",
    description="System में files को search करने के लिए - name या extension के आधार पर"
)
async def search_files_system(query: str, location: str = "", file_type: str = "") -> str:
    """Search for files in the system"""
    
    if not PERSONAL_MODE_ENABLED:
        return "🔐 Personal mode enable करें पहले!"
    
    try:
        import os

        # Default search location
        if not location:
            location = "C:\\"

        # SECURITY: search is performed in pure Python (os.walk) via the safe
        # layer — NOT a `dir "<loc>" /s /b | findstr "<query>"` shell pipeline.
        # This structurally eliminates the command injection that existed here.
        if file_type:
            search_term = f".{file_type.replace('.', '')}"  # e.g. ".pdf"
        else:
            search_term = query

        try:
            matches = _safe_search_files(search_term, location, max_results=500)
        except SecurityValidationError as sec_err:
            logger.warning(f"Blocked unsafe file search: {sec_err}")
            return f"❌ Search input was rejected for security reasons."

        try:
            if matches:
                files = matches
                # Limit results to first 15 to avoid overwhelming
                limited_files = files[:15]

                search_results = f"🔍 **Search Results for '{query}':**\n\n"
                search_results += f"📍 Location: {location}\n"
                search_results += f"📁 Found: {len(files)} files\n\n"

                if file_type:
                    search_results += f"🎯 File type: .{file_type}\n\n"

                search_results += "📄 **Files Found:**\n"
                for i, file_path in enumerate(limited_files, 1):
                    filename = os.path.basename(file_path)
                    search_results += f"{i}. {filename}\n   📂 {file_path}\n"

                if len(files) > 15:
                    search_results += f"\n... और {len(files) - 15} files मिली।"

                search_results += f"\n\n💡 Koi specific file open करनी है? File path बताएं!"
                return search_results

            else:
                # Fallback: open Windows File Explorer at the location (shell-free)
                try:
                    _safe_open_path_with("explorer.exe", location)
                except Exception:
                    pass
                return f"❌ '{query}' files नहीं मिलीं।\n\nFile Explorer opened at {location}\nManual search करें! 📂"

        except Exception as inner_e:
            logger.error(f"Error formatting search results: {inner_e}")
            return f"❌ File search में error: {str(inner_e)}"
            
    except Exception as e:
        logger.error(f"Error searching files: {e}")
        try:
            import subprocess
            subprocess.Popen(["explorer.exe"], shell=False)
            return f"❌ File search में error: {str(e)}\n\nFile Explorer opened as fallback! 📂"
        except:
            return f"❌ File search error: {str(e)} 😔"

@function_tool(
    name="advanced_system_operations",
    description="Advanced system operations जैसे multiple browsers, development setup, screenshot + file operations आदि"
)
async def advanced_system_operations(operation: str, parameters: str = "") -> str:
    """Perform advanced system operations with multiple apps"""
    
    if not PERSONAL_MODE_ENABLED:
        return "🔐 Personal mode enable करें पहले!"
    
    try:
        operation_lower = operation.lower()
        results = []
        
        if "development setup" in operation_lower:
            results.append("💻 **Development Environment Setup...**")
            
            # Open VS Code new window
            vscode_result = await open_vscode_new_window(parameters if parameters else "")
            results.append(f"🔧 VS Code: {vscode_result}")
            
            # Open browsers for documentation
            firefox_result = await open_browser("firefox", "https://developer.mozilla.org")
            results.append(f"📚 Firefox: {firefox_result}")
            
            edge_result = await open_browser("edge", "https://docs.microsoft.com")
            results.append(f"📖 Edge: {edge_result}")
            
            results.append("✅ Development environment ready!")
            
        elif "browser testing" in operation_lower:
            results.append("🌐 **Cross-Browser Testing Setup...**")
            
            browsers = ["chrome", "firefox", "edge"]
            test_url = parameters if parameters else "https://www.google.com"
            
            for browser in browsers:
                browser_result = await open_browser(browser, test_url)
                results.append(f"{browser.title()}: {browser_result}")
            
            results.append("✅ All browsers opened for testing!")
            
        elif "screenshot workflow" in operation_lower:
            results.append("📸 **Screenshot Documentation Workflow...**")
            
            # Capture screenshot first
            screenshot_result = await capture_screenshot()
            results.append(f"📷 Screenshot: {screenshot_result}")
            
            # Open image editing tools if available
            paint_result = await open_application("paint")
            results.append(f"🎨 Paint: {paint_result}")
            
            results.append("✅ Screenshot workflow ready!")
            
        elif "file management" in operation_lower:
            results.append("📁 **File Management Setup...**")
            
            # Open file explorer
            explorer_result = await open_application("explorer")
            results.append(f"📂 Explorer: {explorer_result}")
            
            # Search for files if parameters provided
            if parameters:
                search_result = await search_files_system(parameters)
                results.append(f"🔍 Search: {search_result}")
            
            results.append("✅ File management ready!")
            
        else:
            return f"❌ Unknown operation: '{operation}'\n\nAvailable: development setup, browser testing, screenshot workflow, file management"
        
        return "\n\n".join(results)
        
    except Exception as e:
        logger.error(f"Error in advanced operations: {e}")
        return f"Advanced operations में error: {str(e)} 😔"

@function_tool(
    name="check_personal_mode",
    description="Personal mode की current status check करने के लिए"
)
async def check_personal_mode() -> str:
    """Check if Alice is in personal mode"""
    if PERSONAL_MODE_ENABLED:
        return f"""✅ **Personal Mode: ACTIVE** 💪

📊 Status: Full system control available
📱 Apps in database: {len(APP_DATABASE)}
🚀 Ready for commands!

Available commands:
• "app_name open karo"
• "show available apps"  
• "refresh app database"
• "disable personal mode"

क्या करना है? 😊"""
    else:
        return """❌ **Personal Mode: INACTIVE** 🔐

Basic mode में हूँ। Advanced features के लिए personal mode enable करें।

Enable करने के लिए: "enable personal mode" कहें। 🛡️"""

# ========================
# WHATSAPP AUTOMATION INTEGRATION
# ========================

@function_tool(
    name="send_whatsapp_message_alice",
    description="WhatsApp पर किसी को भी message भेजने के लिए - Alice के through"
)
async def send_whatsapp_message_alice(contact_name: str, message: str) -> str:
    """
    Send WhatsApp message through Alice's automation system
    
    Args:
        contact_name: Name of the contact (as saved in phone)
        message: Message content to send
    """
    if not PERSONAL_MODE_ENABLED:
        # Allow WhatsApp without personal mode for common contacts
        common_contacts = ['mom', 'dad', 'family', 'home']
        if not any(term in contact_name.lower() for term in common_contacts):
            return "🔐 WhatsApp messaging के लिए personal mode enable करें! 'enable personal mode' कहें।"
    
    try:
        # Import and use WhatsApp automation
        from alice_whatsapp_automation import send_whatsapp_message
        result = await send_whatsapp_message(contact_name, message)
        return result
        
    except ImportError:
        return "❌ WhatsApp automation module available नहीं है। Setup check करें। 🔧"
    except Exception as e:
        logger.error(f"WhatsApp message error: {e}")
        return f"❌ WhatsApp message send करने में error: {str(e)}\n\n💡 Solutions:\n• WhatsApp Desktop running है?\n• Contact name correct है?\n• Internet connected है?"

@function_tool(
    name="open_whatsapp_chat_alice", 
    description="WhatsApp में किसी specific person का chat खोलने के लिए"
)
async def open_whatsapp_chat_alice(contact_name: str) -> str:
    """
    Open WhatsApp chat with specific contact through Alice
    
    Args:
        contact_name: Name of the contact to open chat with
    """
    try:
        # Import and use WhatsApp automation  
        from alice_whatsapp_automation import open_whatsapp_chat
        result = await open_whatsapp_chat(contact_name)
        return result
        
    except ImportError:
        return "❌ WhatsApp automation module available नहीं है। Setup check करें। 🔧"
    except Exception as e:
        logger.error(f"WhatsApp chat error: {e}")
        return f"❌ WhatsApp chat open करने में error: {str(e)}\n\n💡 Try: WhatsApp Desktop manually open करके try करें।"

@function_tool(
    name="whatsapp_help_alice",
    description="WhatsApp automation के बारे में help और instructions"
)
async def whatsapp_help_alice() -> str:
    """Get help about Alice's WhatsApp automation capabilities"""
    return """📱 **Alice WhatsApp Automation Help**

🚀 **Available Commands**:

1. **Send Message**:
   - "WhatsApp पर [Name] को message भेजो '[Message]'"
   - Example: "WhatsApp पर Mom को message भेजो 'Dinner ready है'"

2. **Open Chat**:
   - "WhatsApp पर [Name] का chat खोलो"
   - Example: "WhatsApp पर Dad का chat खोलो"

📋 **Requirements**:
- ✅ WhatsApp Desktop installed और logged in
- ✅ Contact names exactly as saved in phone
- ✅ Internet connection active
- ✅ Personal mode enabled (for unknown contacts)

💡 **Smart Tips**:
- Contact names should match exactly (case insensitive)
- Common family contacts work without personal mode
- Alice uses advanced UI automation for reliability
- Works with both regular and business WhatsApp

🎯 **How Alice Works**:
1. Opens WhatsApp Desktop automatically
2. Uses smart search to find contact
3. Navigates to chat using multiple strategies  
4. Types and sends message with verification

⚠️ **Troubleshooting**:
- Ensure WhatsApp Desktop is installed
- Check contact name spelling
- Make sure you're logged into WhatsApp
- Try: "refresh app database" if WhatsApp doesn't open

🔥 **Example Commands**:
- "Alice, WhatsApp पर Rahul को message भेजो 'Meeting tomorrow at 5 PM'"
- "Alice, WhatsApp पर Priya का chat खोलो"
- "WhatsApp मैं Ankush को बोलो 'Happy Birthday!'"

Ready to connect! 💬✨"""

@function_tool(
    name="test_whatsapp_setup",
    description="WhatsApp automation setup test करने के लिए"
)
async def test_whatsapp_setup() -> str:
    """Test if WhatsApp automation is properly set up"""
    try:
        # Test WhatsApp opening
        whatsapp_open_result = await open_application("whatsapp")
        
        if "✅" in whatsapp_open_result:
            # Test automation module import
            try:
                from alice_whatsapp_automation import whatsapp_automation_help
                return f"""✅ **WhatsApp Automation: READY!**

📱 **WhatsApp App**: Working ✅
🤖 **Automation Module**: Loaded ✅
🚀 **Ready for**: Messaging & Chat opening

💡 **Test Commands**:
• "WhatsApp पर [contact] को message भेजो 'test'"
• "WhatsApp पर [contact] का chat खोलो"

{whatsapp_open_result}

सब कुछ ready है! 🎉"""

            except ImportError as import_err:
                return f"""⚠️ **WhatsApp Setup: Partial**

📱 **WhatsApp App**: Working ✅  
🤖 **Automation Module**: Error ❌

Error: {import_err}

💡 Fix: alice_whatsapp_automation.py file check करें।"""
                
        else:
            return f"""❌ **WhatsApp Setup: Failed**

📱 **WhatsApp App**: Not working ❌

Error: {whatsapp_open_result}

💡 Solutions:
• WhatsApp Desktop install करें
• "refresh app database" try करें
• Manually WhatsApp open करके check करें"""
            
    except Exception as e:
        logger.error(f"WhatsApp setup test error: {e}")
        return f"❌ WhatsApp setup test failed: {str(e)}"