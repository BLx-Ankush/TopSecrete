"""
Accurate analysis - checking what actually opens vs what should open
"""
import asyncio
import sys
import os
import subprocess
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from alice_personal_safe import open_application, enable_personal_mode

async def accurate_app_analysis():
    """Accurate analysis of what actually happens when opening apps"""
    
    await enable_personal_mode()
    
    print("🔍 ACCURATE APP OPENING ANALYSIS")
    print("=" * 60)
    
    # Test specific apps and analyze what actually gets matched/opened
    test_cases = [
        ("VS Code", "vscode", "Should open Visual Studio Code"),
        ("VS Code", "code", "Should open Visual Studio Code"),  
        ("Discord", "Discord", "Should open Discord chat app"),
        ("Firefox", "firefox", "Should open Firefox browser"),
        ("CapCut", "CapCut", "Should open CapCut video editor"),
        ("Zoom", "Zoom", "Should open Zoom meeting app"),
    ]
    
    for app_name, command, expectation in test_cases:
        print(f"\n🔹 Testing: {app_name} with command '{command}'")
        print(f"   Expected: {expectation}")
        
        try:
            result = await open_application(command)
            
            # Parse the actual result to see what was matched and opened
            lines = result.split('\n')
            matched_line = [line for line in lines if "Matched:" in line]
            path_line = [line for line in lines if "Path:" in line]
            
            if matched_line:
                matched = matched_line[0].replace("🎯 Matched:", "").strip()
                print(f"   ✅ Alice matched: '{matched}'")
            
            if path_line:
                path = path_line[0].replace("🚀 Path:", "").strip()
                print(f"   📂 Actual path: {path}")
                
                # Analyze if this is the correct app
                if app_name == "VS Code":
                    if "microsoft vs code" in path.lower() or "code.exe" in path.lower():
                        print(f"   ✅ CORRECT: This is actually VS Code")
                    else:
                        print(f"   ❌ WRONG: This is NOT VS Code - it's something else")
                
                elif app_name == "Discord":
                    if "discord" in path.lower() and not "start" in path.lower():
                        print(f"   ✅ CORRECT: This is actually Discord")
                    elif "start" in path.lower():
                        print(f"   ⚠️  FALLBACK: Using Windows start command (may or may not work)")
                    else:
                        print(f"   ❌ WRONG: This is NOT Discord")
                
                elif app_name == "Firefox":
                    if "firefox" in path.lower() and ("mozilla" in path.lower() or "firefox.exe" in path.lower()):
                        print(f"   ✅ CORRECT: This is actually Firefox")
                    elif "start" in path.lower():
                        print(f"   ⚠️  FALLBACK: Using Windows start command (may or may not work)")
                    else:
                        print(f"   ❌ WRONG: This is NOT Firefox")
                
                elif app_name == "CapCut":
                    if "capcut" in path.lower() and not "start" in path.lower():
                        print(f"   ✅ CORRECT: This is actually CapCut")
                    elif "start" in path.lower():
                        print(f"   ⚠️  FALLBACK: Using Windows start command (may or may not work)")
                    else:
                        print(f"   ❌ WRONG: This is NOT CapCut")
                
                elif app_name == "Zoom":
                    if "zoom" in path.lower() and ("zoom.exe" in path.lower() or "zoom\\bin" in path.lower()):
                        print(f"   ✅ CORRECT: This is actually Zoom")
                    else:
                        print(f"   ❌ WRONG: This might not be the main Zoom app")
                
            else:
                print(f"   ❌ ERROR: Could not extract path information")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print(f"\n" + "=" * 60)
    print("📊 SUMMARY OF ACTUAL ISSUES:")
    print("=" * 60)
    
    # Let's check what actually exists on the system
    print("\n🔍 CHECKING WHAT'S ACTUALLY INSTALLED:")
    
    # Check for VS Code
    vscode_paths = [
        "C:\\Program Files\\Microsoft VS Code\\Code.exe",
        "C:\\Program Files (x86)\\Microsoft VS Code\\Code.exe",
        "C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe"
    ]
    
    print("\n• VS Code:")
    vscode_found = False
    for path in vscode_paths:
        expanded_path = os.path.expandvars(path)
        if os.path.exists(expanded_path):
            print(f"   ✅ Found at: {expanded_path}")
            vscode_found = True
            break
    if not vscode_found:
        print(f"   ❌ VS Code not found in standard locations")
    
    # Check for Discord
    discord_paths = [
        "C:\\Users\\%USERNAME%\\AppData\\Local\\Discord\\Update.exe",
        "C:\\Users\\%USERNAME%\\AppData\\Roaming\\Discord\\Discord.exe"
    ]
    
    print("\n• Discord:")
    discord_found = False
    for path in discord_paths:
        expanded_path = os.path.expandvars(path)
        if os.path.exists(expanded_path):
            print(f"   ✅ Found at: {expanded_path}")
            discord_found = True
            break
    if not discord_found:
        print(f"   ❌ Discord not found in standard locations")
    
    # Check for Firefox
    firefox_paths = [
        "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
        "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe"
    ]
    
    print("\n• Firefox:")
    firefox_found = False
    for path in firefox_paths:
        if os.path.exists(path):
            print(f"   ✅ Found at: {path}")
            firefox_found = True
            break
    if not firefox_found:
        print(f"   ❌ Firefox not found in standard locations")
    
    print("\n" + "=" * 60)
    print("⚠️  CONCLUSION: Alice may be matching wrong executables")
    print("   or using fallback methods that don't guarantee the correct app opens")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(accurate_app_analysis())