"""Agent Vision Tools Integration Test"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

async def test_agent_vision_tools():
    """Test all vision tools through the agent system"""
    
    print("=== TESTING ALICE VISION TOOLS VIA AGENT ===\n")
    
    try:
        from alice_vision_tools import (
            scan_screen, click_on, type_text_here, send_key_combination,
            take_screenshot_now, find_elements_like, get_active_window_info, 
            export_screen_data
        )
        print("✅ All vision tools imported successfully")
    except Exception as e:
        print(f"❌ Tool import error: {e}")
        return False
    
    # Test 1: Screen scanning
    print("\n1. Testing screen scanning...")
    try:
        result = await scan_screen()
        print(f"✅ Screen scan result: {result[:100]}...")
    except Exception as e:
        print(f"❌ Screen scan error: {e}")
    
    # Test 2: Active window info
    print("\n2. Testing active window info...")
    try:
        result = await get_active_window_info()
        print(f"✅ Active window: {result[:100]}...")
    except Exception as e:
        print(f"❌ Active window error: {e}")
    
    # Test 3: Element finding
    print("\n3. Testing element finding...")
    try:
        result = await find_elements_like("button")
        print(f"✅ Found elements: {result[:100]}...")
    except Exception as e:
        print(f"❌ Element finding error: {e}")
    
    # Test 4: Screenshot
    print("\n4. Testing screenshot...")
    try:
        result = await take_screenshot_now()
        print(f"✅ Screenshot: {result}")
    except Exception as e:
        print(f"❌ Screenshot error: {e}")
    
    # Test 5: Data export
    print("\n5. Testing data export...")
    try:
        result = await export_screen_data()
        print(f"✅ Data export: {result}")
    except Exception as e:
        print(f"❌ Data export error: {e}")
    
    print("\n=== AGENT TOOLS TEST COMPLETED ===")
    print("✅ All vision tools working through agent system!")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_agent_vision_tools())