"""
Alice Advanced System Controller
Advanced system operations for Alice's personal mode including:
- App management
- File operations
- Email handling  
- Presentation creation
- Multi-tasking automation
"""

import os
import subprocess
import shutil
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from livekit.agents import function_tool
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedSystemController:
    def __init__(self):
        self.temp_dir = Path.cwd() / "temp_alice_files"
        self.temp_dir.mkdir(exist_ok=True)
    
    def open_application(self, app_name: str) -> str:
        """Open any application by name with improved Windows compatibility"""
        
        # Enhanced app commands with multiple variations and paths
        app_commands = {
            # Microsoft Office (multiple possible paths)
            "word": ["winword.exe", "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE"],
            "excel": ["excel.exe", "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE"], 
            "powerpoint": ["powerpnt.exe", "C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE"],
            "outlook": ["outlook.exe", "C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE"],
            "teams": ["ms-teams:", "Teams.exe"],
            
            # Browsers
            "chrome": [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "start chrome",
                "chrome.exe",
                "google-chrome"
            ],
            "firefox": ["firefox.exe", "C:\\Program Files\\Mozilla Firefox\\firefox.exe"],
            "edge": ["msedge.exe", "MicrosoftEdge.exe", "microsoft-edge:"],
            "brave": ["brave.exe", "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"],
            
            # Common Windows Apps
            "notepad": ["notepad.exe"],
            "calculator": ["calc.exe"],
            "paint": ["mspaint.exe"],
            "wordpad": ["write.exe"],
            "cmd": ["cmd.exe"],
            "powershell": ["powershell.exe", "pwsh.exe"],
            "terminal": ["wt.exe", "WindowsTerminal.exe"],
            
            # Development Tools
            "vscode": ["code.exe", "Code.exe", "C:\\Program Files\\Microsoft VS Code\\Code.exe"],
            "visual studio": ["devenv.exe", "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\Common7\\IDE\\devenv.exe"],
            "git": ["git-bash.exe", "C:\\Program Files\\Git\\git-bash.exe"],
            "github desktop": ["GitHubDesktop.exe"],
            "postman": ["Postman.exe"],
            
            # Media & Entertainment
            "vlc": ["vlc.exe", "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"],
            "spotify": ["spotify.exe", "Spotify.exe"],
            "discord": ["discord.exe", "Discord.exe"],
            "whatsapp": ["whatsapp.exe", "WhatsApp.exe"],
            "telegram": ["telegram.exe", "Telegram.exe"],
            "zoom": ["zoom.exe", "Zoom.exe"],
            
            # Adobe Products
            "photoshop": ["photoshop.exe", "Photoshop.exe"],
            "illustrator": ["illustrator.exe", "Illustrator.exe"],
            "premiere": ["premiere.exe", "Adobe Premiere Pro.exe"],
            
            # System Tools
            "explorer": ["explorer.exe"],
            "control panel": ["control.exe"],
            "task manager": ["taskmgr.exe"],
            "registry": ["regedit.exe"],
            "services": ["services.msc"],
            "device manager": ["devmgmt.msc"],
            
            # Games & Others
            "steam": ["steam.exe", "C:\\Program Files (x86)\\Steam\\steam.exe"],
            "epic games": ["EpicGamesLauncher.exe"],
            "blender": ["blender.exe"],
            "obs": ["obs64.exe", "obs-studio"],
        }
        
        app_lower = app_name.lower()
        
        # Method 1: Try exact match with multiple command variations
        for key, commands in app_commands.items():
            if key == app_lower or app_lower in key or key in app_lower:
                for command in commands:
                    try:
                        if command.startswith("start "):
                            # Use Windows start command
                            subprocess.Popen(command, shell=True)
                            return f"✅ {app_name} successfully opened via start command!"
                        elif command.startswith("C:\\"):
                            # Try specific path
                            if os.path.exists(command):
                                subprocess.Popen([command], shell=False)
                                return f"✅ {app_name} successfully opened from: {command}"
                        elif ":" in command:
                            # Protocol handler (like ms-teams:)
                            subprocess.Popen(f'start "" "{command}"', shell=True)
                            return f"✅ {app_name} opened via protocol: {command}"
                        else:
                            # Try simple command
                            subprocess.Popen(f'start "" "{command}"', shell=True)
                            return f"✅ {app_name} successfully opened!"
                    except Exception as e:
                        continue
        
        # Method 2: Try Windows start command
        try:
            subprocess.run(f'start "" "{app_name}"', shell=True, check=True, timeout=5)
            return f"✅ {app_name} opened via Windows start menu!"
        except:
            pass
        
        # Method 3: Try PowerShell Get-Process to find running instances
        try:
            result = subprocess.run(
                f'powershell "Get-Process | Where-Object {{$_.ProcessName -like \'*{app_name}*\'}} | Select-Object -First 1"',
                shell=True, capture_output=True, text=True, timeout=10
            )
            if result.stdout.strip():
                # If found running, try to bring to foreground
                subprocess.run(f'powershell "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::AppActivate(\'{app_name}\')"', shell=True)
                return f"✅ {app_name} was already running - brought to foreground!"
        except:
            pass
        
        # Method 4: Try searching in common installation directories
        common_paths = [
            "C:\\Program Files",
            "C:\\Program Files (x86)", 
            os.path.expanduser("~\\AppData\\Local"),
            os.path.expanduser("~\\AppData\\Roaming"),
            "C:\\Windows\\System32"
        ]
        
        for base_path in common_paths:
            try:
                for root, dirs, files in os.walk(base_path):
                    for file in files:
                        if (app_lower in file.lower() or file.lower().startswith(app_lower)) and file.endswith('.exe'):
                            full_path = os.path.join(root, file)
                            try:
                                subprocess.Popen([full_path], shell=True)
                                return f"✅ {app_name} found and opened from: {full_path}"
                            except:
                                continue
                    # Limit search depth to avoid performance issues
                    if root.count(os.sep) - base_path.count(os.sep) > 2:
                        dirs[:] = []
            except:
                continue
        
        return f"❌ Could not find or open {app_name}. Please check:\n1. App name spelling\n2. App is installed\n3. Try running Alice as administrator for some system apps"

system_controller = AdvancedSystemController()

@function_tool(
    name="open_any_app",
    description=(
        "कोई भी application open करने के लिए use करें। "
        "Examples: Word, Excel, PowerPoint, Chrome, Notepad, Calculator, VS Code, etc."
    )
)
async def open_any_app(app_name: str) -> str:
    """
    Open any application on the system
    
    Args:
        app_name: Name of the application to open (e.g., "Word", "Chrome", "Calculator")
    """
    try:
        result = system_controller.open_application(app_name)
        if "successfully opened" in result:
            return f"{result}\n\n{app_name} खुल गया है! और कुछ चाहिए? 😊"
        else:
            return f"{result}\n\nKoi aur app try करें या exact name बताएं। 🤔"
    except Exception as e:
        logger.error(f"Error opening app {app_name}: {e}")
        return f"Sorry! {app_name} open करने में problem आई। Error: {str(e)} 😔"

@function_tool(
    name="create_and_research",
    description=(
        "Research करके summary notepad में create करता है। "
        "Topic research करके findings को organized format में notepad file में save करता है।"
    )
)
async def create_and_research(topic: str, filename: str = "") -> str:
    """
    Research a topic and create a summary in Notepad
    
    Args:
        topic: Topic to research
        filename: Optional filename for the notepad file
    """
    try:
        # Import search function
        from Alice_duckduckgo_search import duckduckgo_search
        
        # Research the topic
        search_result = await duckduckgo_search.ainvoke(f"comprehensive guide {topic}")
        
        if not filename:
            filename = f"{topic.replace(' ', '_')}_research_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        
        file_path = system_controller.temp_dir / filename
        
        # Create comprehensive research summary
        summary_content = f"""
===========================================
📊 RESEARCH SUMMARY: {topic.upper()}
===========================================
📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👤 Researcher: Alice AI Assistant
🔍 Search Query: {topic}

===========================================
🔍 RESEARCH FINDINGS:
===========================================

{search_result}

===========================================
✅ SUMMARY COMPLETED
===========================================
यह summary Alice AI द्वारा automatically generate की गई है।
Additional research के लिए specific questions पूछें।

📝 File Location: {file_path}
"""
        
        # Save to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        
        # Open in Notepad
        subprocess.Popen(f'notepad.exe "{file_path}"', shell=True)
        
        return f"✅ **Research Complete!**\n\n🔍 Topic: {topic}\n📝 File: {filename}\n💾 Saved at: {file_path}\n\nNotepad में research summary open हो गई है! आप edit भी कर सकते हैं। 😊"
        
    except Exception as e:
        logger.error(f"Error in research and create: {e}")
        return f"Research करने में problem आई: {str(e)}\n\nManual search करके मैं basic summary बना सकती हूं। 🤔"

@function_tool(
    name="manage_files",
    description=(
        "File operations जैसे create, copy, move, delete, search files। "
        "Presentations, documents, या कोई भी file management के लिए use करें।"
    )
)
async def manage_files(operation: str, file_path: str = "", destination: str = "", content: str = "") -> str:
    """
    Perform file operations like create, copy, move, delete, search
    
    Args:
        operation: Type of operation (create, copy, move, delete, search, open)
        file_path: Path of the file to operate on
        destination: Destination path for copy/move operations
        content: Content for create operation
    """
    try:
        operation = operation.lower()
        
        if operation == "create":
            if not file_path:
                file_path = str(system_controller.temp_dir / f"alice_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content if content else f"# File created by Alice\n\nCreated on: {datetime.now()}\n\n")
            
            return f"✅ File created: {file_path}\n\nFile बन गई है! Open करना है? 📝"
        
        elif operation == "copy":
            if not destination:
                destination = str(system_controller.temp_dir)
            
            shutil.copy2(file_path, destination)
            return f"✅ File copied from {file_path} to {destination}\n\nCopy हो गई! 📋"
        
        elif operation == "move":
            if not destination:
                return "Destination path specify करें move operation के लिए! 📁"
            
            shutil.move(file_path, destination)
            return f"✅ File moved from {file_path} to {destination}\n\nMove complete! 🚚"
        
        elif operation == "delete":
            if os.path.exists(file_path):
                os.remove(file_path)
                return f"✅ File deleted: {file_path}\n\nFile delete हो गई! ⚠️"
            else:
                return f"❌ File not found: {file_path}"
        
        elif operation == "search":
            search_results = []
            search_path = Path(file_path) if file_path else Path.home()
            
            for file in search_path.rglob("*"):
                if file.is_file() and content.lower() in file.name.lower():
                    search_results.append(str(file))
                if len(search_results) >= 10:  # Limit results
                    break
            
            if search_results:
                result = f"🔍 Search Results for '{content}':\n\n"
                for i, file in enumerate(search_results, 1):
                    result += f"{i}. {file}\n"
                return result + "\nKoi specific file open करनी है? 📁"
            else:
                return f"❌ No files found matching '{content}'"
        
        elif operation == "open":
            if os.path.exists(file_path):
                os.startfile(file_path)
                return f"✅ File opened: {file_path}\n\nFile खुल गई है! 📂"
            else:
                return f"❌ File not found: {file_path}"
        
        else:
            return "Available operations: create, copy, move, delete, search, open\nKaunsa operation करना है? 🤔"
    
    except Exception as e:
        logger.error(f"Error in file operation: {e}")
        return f"File operation में error आया: {str(e)} 😔"

@function_tool(
    name="presentation_creator",
    description=(
        "PowerPoint presentation automatically create करता है given topic के साथ।"
        "Complete slides के साथ professional presentation बनाता है।"
    )
)
async def presentation_creator(topic: str, slides_count: int = 5) -> str:
    """
    Create a PowerPoint presentation on a given topic
    
    Args:
        topic: Topic for the presentation
        slides_count: Number of slides to create (default: 5)
    """
    try:
        # Create presentation content
        presentation_content = f"""
PowerPoint Presentation: {topic}

Slide 1: Title Slide
- Title: {topic}
- Subtitle: Comprehensive Overview
- Presenter: Alice AI Assistant
- Date: {datetime.now().strftime('%B %d, %Y')}

Slide 2: Introduction
- What is {topic}?
- Why is it important?
- Key objectives

Slide 3: Main Points
- Core concepts
- Key features
- Important aspects

Slide 4: Benefits & Applications
- Advantages
- Real-world uses
- Impact

Slide 5: Conclusion
- Summary of key points
- Future outlook
- Questions & Discussion

Note: यह Alice AI द्वारा auto-generated outline है।
PowerPoint में import करके customize कर सकते हैं।
"""
        
        # Save presentation outline
        filename = f"{topic.replace(' ', '_')}_presentation_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        file_path = system_controller.temp_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(presentation_content)
        
        # Try to open PowerPoint
        try:
            subprocess.Popen("powerpnt.exe", shell=True)
            return f"✅ **Presentation Created!**\n\n📊 Topic: {topic}\n📝 Outline saved: {filename}\n💻 PowerPoint opened\n\nOutline को PowerPoint में copy-paste करके professional slides बना सकते हैं! 🎯"
        except:
            return f"✅ **Presentation Outline Ready!**\n\n📊 Topic: {topic}\n📝 File: {filename}\n\nPowerPoint manually open करके outline use कर सकते हैं। File location: {file_path} 📋"
    
    except Exception as e:
        logger.error(f"Error creating presentation: {e}")
        return f"Presentation create करने में problem आई: {str(e)} 😔"

@function_tool(
    name="multi_task_executor",
    description=(
        "Multiple tasks को simultaneously execute करता है। "
        "Example: research + file creation + app opening एक साथ।"
    )
)
async def multi_task_executor(tasks: str) -> str:
    """
    Execute multiple tasks simultaneously
    
    Args:
        tasks: Comma-separated list of tasks to execute
    """
    try:
        task_list = [task.strip() for task in tasks.split(',')]
        results = []
        
        for task in task_list:
            if 'research' in task.lower() or 'search' in task.lower():
                topic = task.split('research')[-1].split('search')[-1].strip()
                if topic:
                    result = await create_and_research(topic)
                    results.append(f"📊 Research: {result}")
            
            elif 'open' in task.lower():
                app_name = task.replace('open', '').strip()
                if app_name:
                    result = await open_any_app(app_name)
                    results.append(f"🚀 App: {result}")
            
            elif 'create file' in task.lower():
                filename = task.replace('create file', '').strip()
                result = await manage_files("create", filename, "", f"File created by multi-task executor\nTask: {task}\nTime: {datetime.now()}")
                results.append(f"📝 File: {result}")
            
            else:
                results.append(f"⚠️ Unknown task: {task}")
        
        final_result = "🔄 **Multi-Task Execution Complete!**\n\n" + "\n\n".join(results)
        return final_result + "\n\nSaare tasks complete हो गए! Aur kuch chahiye? 🎯"
    
    except Exception as e:
        logger.error(f"Error in multi-task execution: {e}")
        return f"Multi-task execution में problem आई: {str(e)} 😔"