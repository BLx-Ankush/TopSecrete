"""
Comprehensive App Mapping System for Alice
Scans entire Windows system to map all installed applications
"""

import os
import winreg
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensiveAppMapper:
    def __init__(self):
        self.apps_database = {}
        self.scan_locations = [
            "C:\\Program Files",
            "C:\\Program Files (x86)",
            "C:\\Windows\\System32",
            "C:\\Windows\\SysWOW64",
            os.path.expanduser("~\\AppData\\Local"),
            os.path.expanduser("~\\AppData\\Roaming"),
        ]
        
    def scan_registry_apps(self) -> Dict:
        """Scan Windows Registry for installed applications"""
        registry_apps = {}
        
        # Registry locations to scan
        registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
        ]
        
        for root_key, subkey_path in registry_keys:
            try:
                with winreg.OpenKey(root_key, subkey_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    app_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                    
                                    # Get installation location
                                    install_location = ""
                                    display_icon = ""
                                    
                                    try:
                                        install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                    except FileNotFoundError:
                                        pass
                                    
                                    try:
                                        display_icon = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                                    except FileNotFoundError:
                                        pass
                                    
                                    if app_name and (install_location or display_icon):
                                        registry_apps[app_name.lower()] = {
                                            "name": app_name,
                                            "install_location": install_location,
                                            "icon_path": display_icon,
                                            "source": "registry"
                                        }
                                except FileNotFoundError:
                                    continue
                        except Exception:
                            continue
            except Exception as e:
                logger.warning(f"Could not scan registry key {subkey_path}: {e}")
        
        return registry_apps
    
    def scan_start_menu(self) -> Dict:
        """Scan Windows Start Menu for applications"""
        start_menu_apps = {}
        
        start_menu_paths = [
            "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
            os.path.expanduser("~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs")
        ]
        
        for start_path in start_menu_paths:
            if os.path.exists(start_path):
                for root, dirs, files in os.walk(start_path):
                    for file in files:
                        if file.endswith('.lnk'):
                            app_name = file[:-4].lower()  # Remove .lnk extension
                            lnk_path = os.path.join(root, file)
                            
                            # Try to resolve shortcut target
                            try:
                                result = subprocess.run([
                                    'powershell', '-Command', 
                                    f'$shell = New-Object -ComObject WScript.Shell; $shortcut = $shell.CreateShortcut("{lnk_path}"); $shortcut.TargetPath'
                                ], capture_output=True, text=True, timeout=5)
                                
                                if result.returncode == 0 and result.stdout.strip():
                                    target_path = result.stdout.strip()
                                    if os.path.exists(target_path):
                                        start_menu_apps[app_name] = {
                                            "name": file[:-4],
                                            "target_path": target_path,
                                            "shortcut_path": lnk_path,
                                            "source": "start_menu"
                                        }
                            except Exception:
                                continue
        
        return start_menu_apps
    
    def scan_directories(self) -> Dict:
        """Scan common installation directories for executables"""
        directory_apps = {}
        
        for location in self.scan_locations:
            if os.path.exists(location):
                try:
                    # Limit depth to avoid performance issues
                    for root, dirs, files in os.walk(location):
                        # Skip deep nested directories
                        depth = root.replace(location, '').count(os.sep)
                        if depth > 3:
                            dirs[:] = []  # Don't go deeper
                            continue
                        
                        for file in files:
                            if file.endswith('.exe') and not file.startswith('unins'):
                                app_name = file[:-4].lower()
                                full_path = os.path.join(root, file)
                                
                                # Skip system files and uninstallers
                                if any(skip in app_name for skip in ['uninstall', 'setup', 'installer', 'update']):
                                    continue
                                
                                directory_apps[app_name] = {
                                    "name": file[:-4],
                                    "exe_path": full_path,
                                    "directory": root,
                                    "source": "directory_scan"
                                }
                except Exception as e:
                    logger.warning(f"Could not scan directory {location}: {e}")
        
        return directory_apps
    
    def get_windows_apps(self) -> Dict:
        """Get Windows Store and built-in apps"""
        windows_apps = {}
        
        # Built-in Windows apps
        builtin_apps = {
            "notepad": {"path": "notepad.exe", "name": "Notepad"},
            "calculator": {"path": "calc.exe", "name": "Calculator"},
            "paint": {"path": "mspaint.exe", "name": "Paint"},
            "wordpad": {"path": "write.exe", "name": "WordPad"},
            "cmd": {"path": "cmd.exe", "name": "Command Prompt"},
            "powershell": {"path": "powershell.exe", "name": "PowerShell"},
            "terminal": {"path": "wt.exe", "name": "Windows Terminal"},
            "explorer": {"path": "explorer.exe", "name": "File Explorer"},
            "control": {"path": "control.exe", "name": "Control Panel"},
            "taskmgr": {"path": "taskmgr.exe", "name": "Task Manager"},
            "regedit": {"path": "regedit.exe", "name": "Registry Editor"},
            "msconfig": {"path": "msconfig.exe", "name": "System Configuration"},
            "services": {"path": "services.msc", "name": "Services"}
        }
        
        for key, info in builtin_apps.items():
            windows_apps[key] = {
                "name": info["name"],
                "exe_path": info["path"],
                "source": "windows_builtin"
            }
        
        return windows_apps
    
    def build_comprehensive_database(self) -> Dict:
        """Build comprehensive database of all applications"""
        logger.info("🔍 Scanning system for all applications...")
        
        # Get apps from different sources
        registry_apps = self.scan_registry_apps()
        logger.info(f"Found {len(registry_apps)} registry apps")
        
        start_menu_apps = self.scan_start_menu()
        logger.info(f"Found {len(start_menu_apps)} start menu apps")
        
        directory_apps = self.scan_directories()
        logger.info(f"Found {len(directory_apps)} directory apps")
        
        windows_apps = self.get_windows_apps()
        logger.info(f"Found {len(windows_apps)} Windows apps")
        
        # Combine all sources with priority: Windows built-in > Registry > Start Menu > Directory
        combined_apps = {}
        combined_apps.update(directory_apps)
        combined_apps.update(start_menu_apps)
        combined_apps.update(registry_apps)
        combined_apps.update(windows_apps)
        
        # Create searchable aliases
        searchable_database = {}
        for key, app_info in combined_apps.items():
            app_name = app_info["name"]
            
            # Add original key
            searchable_database[key] = app_info
            
            # Add full name variations
            searchable_database[app_name.lower()] = app_info
            searchable_database[app_name.lower().replace(" ", "")] = app_info
            
            # Add common abbreviations
            if "microsoft" in app_name.lower():
                searchable_database[app_name.lower().replace("microsoft ", "")] = app_info
            
            # Add executable name without extension
            if "exe_path" in app_info:
                exe_name = os.path.basename(app_info["exe_path"])[:-4].lower()
                searchable_database[exe_name] = app_info
            elif "target_path" in app_info:
                exe_name = os.path.basename(app_info["target_path"])[:-4].lower()
                searchable_database[exe_name] = app_info
        
        logger.info(f"✅ Built database with {len(searchable_database)} searchable entries")
        return searchable_database
    
    def save_database(self, database: Dict, filename: str = "apps_database.json"):
        """Save the database to a JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(database, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Database saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving database: {e}")
    
    def load_database(self, filename: str = "apps_database.json") -> Dict:
        """Load the database from a JSON file"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    database = json.load(f)
                logger.info(f"📂 Database loaded from {filename}")
                return database
            else:
                logger.info(f"No existing database found at {filename}")
                return {}
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            return {}

if __name__ == "__main__":
    # Test the comprehensive app mapping system
    print("🚀 Starting Comprehensive App Mapping System...")
    
    mapper = ComprehensiveAppMapper()
    
    # Build the database
    database = mapper.build_comprehensive_database()
    
    # Save the database
    mapper.save_database(database)
    
    # Show some sample results
    print(f"\n📊 Total applications found: {len(database)}")
    
    print("\n🎯 Sample applications found:")
    count = 0
    for key, app_info in database.items():
        if count < 10:
            print(f"  '{key}' -> {app_info['name']}")
            count += 1
        else:
            break
    
    print(f"\n✅ App mapping complete! Database contains {len(database)} entries.")