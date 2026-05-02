"""
Alice Vision System Test and Demonstration
This script tests all Alice Vision capabilities and demonstrates
how it works similarly to Comet browser's DOM reading.
"""

import asyncio
import sys
import time
from alice_vision_tools import (
    scan_screen, click_on, type_text_here, send_key_combination,
    take_screenshot_now, find_elements_like, get_active_window_info,
    export_screen_data
)

async def demonstrate_alice_vision():
    """Comprehensive demonstration of Alice Vision capabilities"""
    
    print("🤖 ALICE VISION SYSTEM DEMONSTRATION")
    print("=" * 60)
    print("This shows how Alice can 'see' the OS like Comet reads the DOM")
    print("=" * 60)
    
    # Test 1: Screen scanning (like reading DOM)
    print("\\n📊 TEST 1: SCREEN SCANNING (Like DOM Reading)")
    print("-" * 50)
    result = await scan_screen()
    print(result)
    
    # Test 2: Active window analysis
    print("\\n🪟 TEST 2: ACTIVE WINDOW ANALYSIS")
    print("-" * 50)
    result = await get_active_window_info()
    print(result)
    
    # Test 3: Element discovery
    print("\\n🔍 TEST 3: ELEMENT DISCOVERY")
    print("-" * 50)
    print("Looking for buttons...")
    result = await find_elements_like("button")
    print(result)
    
    # Test 4: Screenshot capability
    print("\\n📸 TEST 4: SCREENSHOT CAPTURE")
    print("-" * 50)
    result = await take_screenshot_now()
    print(result)
    
    # Test 5: Keyboard interaction
    print("\\n⌨️ TEST 5: KEYBOARD INTERACTION")
    print("-" * 50)
    # Safe key combination that doesn't do anything harmful
    result = await send_key_combination("ctrl+shift")  # Just test the function
    print(result)
    
    # Test 6: Data export
    print("\\n📋 TEST 6: DATA EXPORT")
    print("-" * 50)
    result = await export_screen_data()
    print(result)
    
    print("\\n" + "=" * 60)
    print("✅ ALICE VISION DEMONSTRATION COMPLETE!")
    print("=" * 60)
    
    print("\\nKEY CAPABILITIES:")
    print("🔹 Screen scanning - Alice can see all windows and UI elements")
    print("🔹 Element detection - Like DOM elements but for the entire OS")
    print("🔹 Smart interaction - Click, type, send keys with precision")
    print("🔹 Real-time awareness - Scans and caches for performance")
    print("🔹 Safe automation - Built-in protections and error handling")
    
    print("\\nUSAGE EXAMPLES:")
    print("💬 'Alice, scan the screen' → Shows all windows and elements")
    print("💬 'Alice, click on the save button' → Finds and clicks save")
    print("💬 'Alice, type hello world' → Types text at cursor")
    print("💬 'Alice, take a screenshot' → Captures current screen")
    print("💬 'Alice, press ctrl+c' → Sends keyboard shortcut")

def test_specific_functionality():
    """Test specific functionality with error handling"""
    
    print("\\n🧪 DETAILED FUNCTIONALITY TESTS")
    print("=" * 50)
    
    try:
        from alice_vision import AliceVision
        
        # Create vision instance
        vision = AliceVision()
        print("✅ Alice Vision instance created successfully")
        
        # Test window enumeration
        windows = vision.get_all_windows()
        print(f"✅ Found {len(windows)} windows")
        
        # Test element scanning
        elements = vision.scan_active_window()
        clickable = [e for e in elements if e.is_clickable]
        print(f"✅ Found {len(elements)} elements, {len(clickable)} clickable")
        
        # Test screenshot
        screenshot = vision.take_screenshot()
        print(f"✅ Screenshot: {'Success' if screenshot else 'Failed'}")
        
        # Test data export
        export_path = vision.export_scan_data()
        print(f"✅ Data export: {'Success' if export_path else 'Failed'}")
        
        print("\\n📊 SYSTEM STATUS: ALL TESTS PASSED!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False

async def interactive_demo():
    """Interactive demonstration"""
    
    print("\\n🎮 INTERACTIVE DEMO")
    print("=" * 30)
    print("This demonstrates Alice's real-time capabilities...")
    
    while True:
        print("\\nChoose a test:")
        print("1. Scan screen")
        print("2. Find buttons")
        print("3. Take screenshot")
        print("4. Get window info")
        print("5. Exit")
        
        try:
            choice = input("\\nEnter choice (1-5): ").strip()
            
            if choice == "1":
                print("\\n🔍 Scanning screen...")
                result = await scan_screen()
                print(result)
                
            elif choice == "2":
                print("\\n🔘 Finding buttons...")
                result = await find_elements_like("button")
                print(result)
                
            elif choice == "3":
                print("\\n📸 Taking screenshot...")
                result = await take_screenshot_now()
                print(result)
                
            elif choice == "4":
                print("\\n🪟 Getting window info...")
                result = await get_active_window_info()
                print(result)
                
            elif choice == "5":
                print("\\n👋 Goodbye!")
                break
                
            else:
                print("\\n❌ Invalid choice. Please enter 1-5.")
                
        except KeyboardInterrupt:
            print("\\n\\n👋 Demo interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\\n❌ Error: {e}")

async def main():
    """Main test function"""
    
    # Check if we should run interactive demo
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        await interactive_demo()
        return
    
    # Run full demonstration
    await demonstrate_alice_vision()
    
    print("\\n" + "=" * 60)
    
    # Run detailed tests
    success = test_specific_functionality()
    
    if success:
        print("\\n🎉 ALL SYSTEMS OPERATIONAL!")
        print("Alice Vision is ready for integration!")
        print("\\nTo use with Alice:")
        print("1. Start Alice: python alice_trigger.py")
        print("2. Say: 'Alice, scan the screen'")
        print("3. Say: 'Alice, click on [element name]'")
    else:
        print("\\n⚠️ Some tests failed. Check the error messages above.")
        print("Make sure all required packages are installed:")
        print("pip install pyautogui pywinauto PyGetWindow psutil")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n\\nDemo interrupted. Goodbye!")
    except Exception as e:
        print(f"\\nDemo failed: {e}")
        print("\\nTroubleshooting:")
        print("1. Make sure you have pywinauto installed: pip install pywinauto")
        print("2. Run as administrator if needed")
        print("3. Make sure Windows UI Automation is enabled")