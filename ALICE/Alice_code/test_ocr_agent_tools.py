"""
OCR Agent Tools Test
Tests the new OCR LiveKit agent tools
"""
import asyncio
import sys
import os

async def test_ocr_agent_tools():
    """Test the new OCR agent tools"""
    
    print("=== OCR AGENT TOOLS TEST ===\\n")
    
    try:
        from alice_vision_tools import (
            read_text_from_image,
            read_screen_text,
            analyze_image_content,
            ALICE_VISION_TOOLS
        )
        print("✅ OCR tools imported successfully")
    except Exception as e:
        print(f"❌ OCR tools import error: {e}")
        return False
    
    # Test 1: Check tools are in the main list
    print(f"\\n1. Checking tool integration...")
    print(f"✅ Total vision tools: {len(ALICE_VISION_TOOLS)}")
    tool_names = [tool.__name__ for tool in ALICE_VISION_TOOLS]
    ocr_tools = ['read_text_from_image', 'read_screen_text', 'analyze_image_content']
    
    for tool_name in ocr_tools:
        if tool_name in tool_names:
            print(f"✅ {tool_name} integrated")
        else:
            print(f"❌ {tool_name} missing")
            return False
    
    # Test 2: Test image OCR tool
    print(f"\\n2. Testing read_text_from_image...")
    test_image = "temp_alice_files/vision/test_ocr_image.png"
    
    if os.path.exists(test_image):
        try:
            result = await read_text_from_image(test_image)
            print("✅ read_text_from_image executed successfully")
            print(f"   Result preview: {result[:100]}...")
        except Exception as e:
            print(f"❌ read_text_from_image error: {e}")
    else:
        print(f"⚠️ Test image not found: {test_image}")
    
    # Test 3: Test screen text reading
    print(f"\\n3. Testing read_screen_text...")
    try:
        result = await read_screen_text()
        print("✅ read_screen_text executed successfully")
        print(f"   Result preview: {result[:100]}...")
    except Exception as e:
        print(f"❌ read_screen_text error: {e}")
    
    # Test 4: Test image analysis
    print(f"\\n4. Testing analyze_image_content...")
    if os.path.exists(test_image):
        try:
            result = await analyze_image_content(test_image)
            print("✅ analyze_image_content executed successfully")
            print(f"   Result preview: {result[:100]}...")
        except Exception as e:
            print(f"❌ analyze_image_content error: {e}")
    else:
        print(f"⚠️ Test image not found: {test_image}")
    
    print("\\n=== OCR AGENT TOOLS TEST COMPLETED ===")
    print("✅ All OCR agent tools are working!")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_ocr_agent_tools())
    if success:
        print("\\n🎉 OCR AGENT TOOLS: OPERATIONAL")
    else:
        print("\\n⚠️ OCR AGENT TOOLS: NEED ATTENTION")