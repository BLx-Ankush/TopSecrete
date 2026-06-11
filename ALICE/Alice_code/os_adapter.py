"""
OS Platform Adapter — Domain 4B (Phase 4)
==========================================
Abstracts ALICE's Windows-specific system tools behind a platform-neutral
interface. When ALICE's core agent calls system operations, it goes through
get_os_adapter() which returns the correct platform implementation.

This means the LLM prompts and tool-calling logic in agent.py never need
to change when running on macOS or Linux — only the adapter changes.

Architecture (Strategy Pattern):
    BaseOSAdapter (abstract interface)
        ├── WindowsAdapter   ← current primary implementation
        ├── MacOSAdapter     ← stub (ready for implementation)
        └── LinuxAdapter     ← stub (ready for implementation)

Usage:
    from os_adapter import get_os_adapter

    adapter = get_os_adapter()
    adapter.set_brightness(70)
    adapter.launch_app("notepad")
    adapter.close_window("Notepad")
    info = adapter.get_system_info()
"""

import logging
import platform
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Base Interface
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BaseOSAdapter(ABC):
    """Abstract interface all platform adapters must implement."""

    @property
    @abstractmethod
    def platform_name(self) -> str: ...

    @abstractmethod
    def set_brightness(self, level: int) -> bool:
        """Set display brightness (0–100)."""
        ...

    @abstractmethod
    def set_volume(self, level: int) -> bool:
        """Set system volume (0–100)."""
        ...

    @abstractmethod
    def launch_app(self, app_name: str) -> bool:
        """Launch an application by its common name."""
        ...

    @abstractmethod
    def close_window(self, window_title: str) -> bool:
        """Close a window by its title (fuzzy match)."""
        ...

    @abstractmethod
    def focus_window(self, window_title: str) -> bool:
        """Bring a window to the foreground."""
        ...

    @abstractmethod
    def get_system_info(self) -> Dict:
        """Return OS, CPU, RAM, battery info as a dict."""
        ...

    @abstractmethod
    def list_running_apps(self) -> List[str]:
        """Return a list of currently running application window titles."""
        ...

    @abstractmethod
    def lock_screen(self) -> bool: ...

    @abstractmethod
    def shutdown(self, delay_seconds: int = 0) -> bool: ...

    @abstractmethod
    def restart(self, delay_seconds: int = 0) -> bool: ...


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Windows Adapter (delegates to existing alice_personal_safe.py tools)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class WindowsAdapter(BaseOSAdapter):

    @property
    def platform_name(self) -> str:
        return "windows"

    def set_brightness(self, level: int) -> bool:
        try:
            level = max(0, min(100, level))
            subprocess.run(
                ["powershell", "-Command",
                 f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                 f".WmiSetBrightness(1,{level})"],
                capture_output=True, timeout=5
            )
            logger.info(f"[WindowsAdapter] Brightness set to {level}%")
            return True
        except Exception as e:
            logger.error(f"[WindowsAdapter] set_brightness failed: {e}")
            return False

    def set_volume(self, level: int) -> bool:
        try:
            level = max(0, min(100, level))
            # Uses nircmd if available, else PowerShell Audio API
            result = subprocess.run(
                ["powershell", "-Command",
                 f"$wsh = New-Object -ComObject WScript.Shell; "
                 f"for($i=0;$i -lt 50;$i++){{$wsh.SendKeys([char]174)}}; "
                 f"$vol = [Math]::Round({level}/2); "
                 f"for($i=0;$i -lt $vol;$i++){{$wsh.SendKeys([char]175)}}"],
                capture_output=True, timeout=5
            )
            logger.info(f"[WindowsAdapter] Volume set to ~{level}%")
            return True
        except Exception as e:
            logger.error(f"[WindowsAdapter] set_volume failed: {e}")
            return False

    def launch_app(self, app_name: str) -> bool:
        try:
            # Delegate to Alice_window_CTRL's open_app where possible
            from Alice_window_CTRL import open_app as _open_app
            import asyncio
            asyncio.get_event_loop().run_until_complete(_open_app.acall({"app_name": app_name}))
            return True
        except Exception:
            # Fallback: start directly
            try:
                subprocess.Popen(["start", app_name], shell=True)
                return True
            except Exception as e:
                logger.error(f"[WindowsAdapter] launch_app failed: {e}")
                return False

    def close_window(self, window_title: str) -> bool:
        try:
            import pygetwindow as gw
            wins = gw.getWindowsWithTitle(window_title)
            if wins:
                wins[0].close()
                logger.info(f"[WindowsAdapter] Closed window: {window_title}")
                return True
            logger.warning(f"[WindowsAdapter] No window found: {window_title}")
            return False
        except Exception as e:
            logger.error(f"[WindowsAdapter] close_window failed: {e}")
            return False

    def focus_window(self, window_title: str) -> bool:
        try:
            import pygetwindow as gw
            wins = gw.getWindowsWithTitle(window_title)
            if wins:
                wins[0].activate()
                return True
            return False
        except Exception as e:
            logger.error(f"[WindowsAdapter] focus_window failed: {e}")
            return False

    def get_system_info(self) -> Dict:
        import platform, psutil
        info = {
            "platform": "Windows",
            "version": platform.version(),
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "ram_total_gb": round(psutil.virtual_memory().total / 1e9, 1),
            "ram_used_percent": psutil.virtual_memory().percent,
        }
        battery = psutil.sensors_battery()
        if battery:
            info["battery_percent"] = battery.percent
            info["plugged_in"] = battery.power_plugged
        return info

    def list_running_apps(self) -> List[str]:
        try:
            import pygetwindow as gw
            return [w.title for w in gw.getAllWindows() if w.title.strip()]
        except Exception:
            return []

    def lock_screen(self) -> bool:
        try:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
            return True
        except Exception as e:
            logger.error(f"[WindowsAdapter] lock_screen failed: {e}")
            return False

    def shutdown(self, delay_seconds: int = 0) -> bool:
        try:
            subprocess.run(["shutdown", "/s", f"/t {delay_seconds}"])
            return True
        except Exception as e:
            logger.error(f"[WindowsAdapter] shutdown failed: {e}")
            return False

    def restart(self, delay_seconds: int = 0) -> bool:
        try:
            subprocess.run(["shutdown", "/r", f"/t {delay_seconds}"])
            return True
        except Exception as e:
            logger.error(f"[WindowsAdapter] restart failed: {e}")
            return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# macOS Adapter (stub — ready for implementation)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MacOSAdapter(BaseOSAdapter):

    @property
    def platform_name(self) -> str:
        return "macos"

    def set_brightness(self, level: int) -> bool:
        try:
            frac = level / 100.0
            subprocess.run(["osascript", "-e", f"tell application \"System Events\" to set brightness of current user to {frac}"])
            return True
        except Exception as e:
            logger.error(f"[MacOSAdapter] set_brightness: {e}"); return False

    def set_volume(self, level: int) -> bool:
        try:
            subprocess.run(["osascript", "-e", f"set volume output volume {level}"])
            return True
        except Exception as e:
            logger.error(f"[MacOSAdapter] set_volume: {e}"); return False

    def launch_app(self, app_name: str) -> bool:
        try:
            subprocess.Popen(["open", "-a", app_name]); return True
        except Exception as e:
            logger.error(f"[MacOSAdapter] launch_app: {e}"); return False

    def close_window(self, window_title: str) -> bool:
        logger.warning("[MacOSAdapter] close_window not yet implemented"); return False

    def focus_window(self, window_title: str) -> bool:
        try:
            subprocess.run(["osascript", "-e", f'tell application "{window_title}" to activate'])
            return True
        except Exception as e:
            logger.error(f"[MacOSAdapter] focus_window: {e}"); return False

    def get_system_info(self) -> Dict:
        import platform, psutil
        return {"platform": "macOS", "version": platform.mac_ver()[0],
                "cpu_percent": psutil.cpu_percent(0.5), "ram_used_percent": psutil.virtual_memory().percent}

    def list_running_apps(self) -> List[str]:
        r = subprocess.run(["osascript", "-e", 'tell application "System Events" to get name of every process whose background only is false'], capture_output=True, text=True)
        return r.stdout.strip().split(", ") if r.returncode == 0 else []

    def lock_screen(self) -> bool:
        subprocess.run(["pmset", "displaysleepnow"]); return True

    def shutdown(self, delay_seconds: int = 0) -> bool:
        subprocess.run(["sudo", "shutdown", "-h", f"+{delay_seconds//60}"]); return True

    def restart(self, delay_seconds: int = 0) -> bool:
        subprocess.run(["sudo", "shutdown", "-r", f"+{delay_seconds//60}"]); return True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Linux Adapter (stub — ready for implementation)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LinuxAdapter(BaseOSAdapter):

    @property
    def platform_name(self) -> str:
        return "linux"

    def set_brightness(self, level: int) -> bool:
        try:
            subprocess.run(["brightnessctl", "set", f"{level}%"]); return True
        except Exception as e:
            logger.error(f"[LinuxAdapter] set_brightness: {e}"); return False

    def set_volume(self, level: int) -> bool:
        try:
            subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{level}%"]); return True
        except Exception as e:
            logger.error(f"[LinuxAdapter] set_volume: {e}"); return False

    def launch_app(self, app_name: str) -> bool:
        try:
            subprocess.Popen([app_name]); return True
        except Exception as e:
            logger.error(f"[LinuxAdapter] launch_app: {e}"); return False

    def close_window(self, window_title: str) -> bool:
        subprocess.run(["wmctrl", "-c", window_title]); return True

    def focus_window(self, window_title: str) -> bool:
        subprocess.run(["wmctrl", "-a", window_title]); return True

    def get_system_info(self) -> Dict:
        import psutil
        return {"platform": "Linux", "cpu_percent": psutil.cpu_percent(0.5),
                "ram_used_percent": psutil.virtual_memory().percent}

    def list_running_apps(self) -> List[str]:
        r = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
        return [l.split(None, 3)[-1] for l in r.stdout.strip().splitlines()] if r.returncode == 0 else []

    def lock_screen(self) -> bool:
        subprocess.run(["gnome-screensaver-command", "-l"]); return True

    def shutdown(self, delay_seconds: int = 0) -> bool:
        subprocess.run(["sudo", "shutdown", "-h", f"+{delay_seconds//60}"]); return True

    def restart(self, delay_seconds: int = 0) -> bool:
        subprocess.run(["sudo", "shutdown", "-r", f"+{delay_seconds//60}"]); return True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Factory — auto-detects OS and returns correct adapter
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_adapter: Optional[BaseOSAdapter] = None


def get_os_adapter() -> BaseOSAdapter:
    """
    Returns the correct platform adapter for the current OS.
    Singleton — only constructed once per process.
    """
    global _adapter
    if _adapter is not None:
        return _adapter

    system = platform.system().lower()
    if system == "windows":
        _adapter = WindowsAdapter()
    elif system == "darwin":
        _adapter = MacOSAdapter()
    elif system == "linux":
        _adapter = LinuxAdapter()
    else:
        logger.warning(f"[OSAdapter] Unknown platform '{system}' — defaulting to Windows adapter")
        _adapter = WindowsAdapter()

    logger.info(f"[OSAdapter] Loaded {_adapter.platform_name.upper()} adapter")
    return _adapter
