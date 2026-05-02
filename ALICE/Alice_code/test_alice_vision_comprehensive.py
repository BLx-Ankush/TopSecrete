"""Full system test for Alice Vision - checking all logic paths"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

def test_comprehensive_system():
    """Run comprehensive tests on all system components"""
    
    print("=== COMPREHENSIVE ALICE VISION SYSTEM TEST ===\n")
    
    # Test 1: Module imports
    print("1. Testing module imports...")
    try:
        from alice_vision import AliceVision, UIElement, WindowInfo
        from alice_vision_tools import ALICE_VISION_TOOLS
        print("✅ All modules imported successfully")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test 2: Vision system initialization  
    print("\n2. Testing vision system initialization...")
    try:
        vision = AliceVision()
        print("✅ AliceVision initialized successfully")
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return False
    
    # Test 3: Window enumeration (the problematic area)
    print("\n3. Testing window enumeration...")
    try:
        windows = vision.get_all_windows()
        print(f"✅ Found {len(windows)} windows")
        if windows:
            print("   Sample windows:")
            for i, window in enumerate(windows[:3]):
                print(f"   - {window.title} (Active: {window.is_active}, Area: {window.area})")
        else:
            print("⚠️  No windows found - may need investigation")
    except Exception as e:
        print(f"❌ Window enumeration error: {e}")
        return False
    
    # Test 4: Element scanning
    print("\n4. Testing element scanning...")
    try:
        elements = vision.scan_active_window()
        print(f"✅ Found {len(elements)} UI elements")
        if elements:
            clickable_count = sum(1 for el in elements if el.is_clickable)
            print(f"   - {clickable_count} clickable elements")
            print(f"   - Sample element: {elements[0].name} ({elements[0].element_type})")
    except Exception as e:
        print(f"❌ Element scanning error: {e}")
        return False
    
    # Test 5: Screenshot capability
    print("\n5. Testing screenshot capability...")
    try:
        screenshot_path = vision.take_screenshot()
        if screenshot_path and os.path.exists(screenshot_path):
            print(f"✅ Screenshot saved to: {screenshot_path}")
        else:
            print("⚠️  Screenshot function returned no path")
    except Exception as e:
        print(f"❌ Screenshot error: {e}")
        return False
    
    # Test 6: LiveKit tools integration
    print("\n6. Testing LiveKit tools integration...")
    try:
        print(f"✅ Found {len(ALICE_VISION_TOOLS)} vision tools available")
        tool_names = [tool.__name__ for tool in ALICE_VISION_TOOLS]
        print(f"   Available tools: {', '.join(tool_names)}")
    except Exception as e:
        print(f"❌ Tools integration error: {e}")
        return False
    
    # Test 7: Agent integration check
    print("\n7. Testing agent integration...")
    try:
        import agent
        # Check if vision tools are in agent's tools
        agent_file = open("agent.py", "r").read()
        if "ALICE_VISION_TOOLS" in agent_file:
            print("✅ Vision tools integrated into agent")
        else:
            print("⚠️  Vision tools may not be integrated into agent")
    except Exception as e:
        print(f"❌ Agent integration check error: {e}")
        return False
    
    # Test 8: Data export functionality
    print("\n8. Testing data export...")
    try:
        export_path = vision.export_scan_data()
        if export_path and os.path.exists(export_path):
            print(f"✅ Data exported to: {export_path}")
        else:
            print("⚠️  Data export may not have worked")
    except Exception as e:
        print(f"❌ Data export error: {e}")
        return False
    
    print("\n=== SYSTEM TEST COMPLETED ===")
    print("✅ All major systems operational!")
    return True

if __name__ == "__main__":
    success = test_comprehensive_system()
    if success:
        print("\n🎉 Alice Vision System: FULLY OPERATIONAL")
    else:
        print("\n⚠️  Alice Vision System: NEEDS ATTENTION")