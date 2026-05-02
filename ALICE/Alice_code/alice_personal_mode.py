"""
Alice Personal Mode Controller
Enables Alice to switch into personal assistant mode with full system control
"""

import os
import subprocess
import psutil
import winreg
import json
from pathlib import Path
from livekit.agents import function_tool
import logging

# Import WhatsApp automation functions
from alice_whatsapp_automation import (
    send_whatsapp_message,
    open_whatsapp_chat, 
    whatsapp_automation_help
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersonalModeController:
    def __init__(self):
        self.is_personal_mode = False
        self.user_permissions = {
            "system_apps": True,
            "file_operations": True,
            "email_access": True,
            "presentations": True,
            "multi_tasking": True,
            "advanced_search": True
        }
    
    def enable_personal_mode(self):
        """Enable Alice's personal mode"""
        self.is_personal_mode = True
        logger.info("Alice Personal Mode Activated")
        return "Personal mode activated! अब मैं आपकी पूरी system को control कर सकती हूँ। 💪"
    
    def disable_personal_mode(self):
        """Disable Alice's personal mode"""
        self.is_personal_mode = False
        logger.info("Alice Personal Mode Deactivated")
        return "Personal mode deactivated. Basic mode में वापस आ गई हूँ। 😊"
    
    def get_installed_applications(self):
        """Get list of all installed applications"""
        apps = []
        try:
            # Check Programs and Features
            uninstall_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, uninstall_key) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            try:
                                app_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                try:
                                    install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                    apps.append({"name": app_name, "path": install_location})
                                except FileNotFoundError:
                                    apps.append({"name": app_name, "path": "Unknown"})
                            except FileNotFoundError:
                                pass
                    except:
                        continue
            
            # Add common Windows applications
            common_apps = [
                {"name": "Notepad", "path": "notepad.exe"},
                {"name": "Calculator", "path": "calc.exe"},
                {"name": "Paint", "path": "mspaint.exe"},
                {"name": "WordPad", "path": "write.exe"},
                {"name": "Command Prompt", "path": "cmd.exe"},
                {"name": "PowerShell", "path": "powershell.exe"},
                {"name": "Task Manager", "path": "taskmgr.exe"},
                {"name": "Control Panel", "path": "control.exe"},
                {"name": "File Explorer", "path": "explorer.exe"}
            ]
            apps.extend(common_apps)
            
        except Exception as e:
            logger.error(f"Error getting applications: {e}")
        
        return apps

# Initialize personal mode controller
personal_controller = PersonalModeController()

@function_tool(
    name="switch_personal_mode",
    description=(
        "Alice को personal mode में switch करने के लिए use करें। "
        "Personal mode में Alice को full system control मिलता है including apps, files, emails, presentations आदि।"
    )
)
async def switch_personal_mode(mode: str = "on") -> str:
    """
    Switch Alice to personal mode for full system control
    
    Args:
        mode: "on" to enable, "off" to disable personal mode
    """
    if mode.lower() in ["on", "enable", "activate", "हाँ", "yes"]:
        result = personal_controller.enable_personal_mode()
        return f"{result}\n\nअब मैं कर सकती हूँ:\n✅ सभी apps open करना\n✅ Files और folders manage करना\n✅ Emails और messages handle करना\n✅ Presentations create करना\n✅ Multi-tasking और automation\n\nबस बताइए Ankush, क्या करना है? 💖🚀"
    
    elif mode.lower() in ["off", "disable", "deactivate", "नहीं", "no"]:
        result = personal_controller.disable_personal_mode()
        return f"{result}\n\nSafety के लिए basic mode में हूँ। Personal mode के लिए फिर से command दें। 😊"
    
    else:
        return "Mode specify करें: 'on' या 'off'. Personal mode चाहिए या basic mode? 🤔"

@function_tool(
    name="get_system_apps",
    description="System में installed सभी applications की list देता है"
)
async def get_system_apps() -> str:
    """Get list of all installed applications on the system"""
    if not personal_controller.is_personal_mode:
        return "Personal mode enable करें पहले! System apps access के लिए personal mode चाहिए। 🔐"
    
    try:
        apps = personal_controller.get_installed_applications()
        
        # Group apps by type for better presentation
        system_apps = []
        user_apps = []
        
        for app in apps[:20]:  # Limit to first 20 for readability
            if any(keyword in app["name"].lower() for keyword in ["microsoft", "windows", "system"]):
                system_apps.append(app["name"])
            else:
                user_apps.append(app["name"])
        
        result = "📱 **Installed Applications:**\n\n"
        
        if system_apps:
            result += "🔧 **System Apps:**\n"
            for app in system_apps[:10]:
                result += f"• {app}\n"
        
        if user_apps:
            result += f"\n💻 **User Apps:**\n"
            for app in user_apps[:10]:
                result += f"• {app}\n"
        
        result += f"\n\nTotal {len(apps)} applications found. कौन सा app खोलना है? 😊"
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting system apps: {e}")
        return f"Apps list लेने में error आया: {str(e)}"

@function_tool(
    name="check_personal_mode_status",
    description="Alice के personal mode की current status check करता है"
)
async def check_personal_mode_status() -> str:
    """Check if Alice is in personal mode"""
    if personal_controller.is_personal_mode:
        return "✅ Personal Mode: **ACTIVE**\n\nमैं आपकी full system को control कर सकती हूँ! बताइए क्या करना है? 💖💪"
    else:
        return "❌ Personal Mode: **INACTIVE**\n\nBasic mode में हूँ। Full control के लिए personal mode enable करें। 🔐"