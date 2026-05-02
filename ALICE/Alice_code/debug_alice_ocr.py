"""
Debug OCR Functionality - Test Alice's actual text reading capability
"""
import asyncio
import os
import sys

async def debug_alice_ocr():
    """Debug Alice's OCR functionality step by step"""
    
    print("=== DEBUGGING ALICE OCR FUNCTIONALITY ===\n")
    
    # Test 1: Check if OCR tools are accessible
    print("1. Testing OCR tool accessibility...")
    try:
        from alice_vision_tools import read_text_from_image, read_screen_text, analyze_image_content
        print("✅ OCR tools imported successfully")
    except Exception as e:
        print(f"❌ OCR tools import failed: {e}")
        return False
    
    # Test 2: Check if vision system is working
    print("\n2. Testing vision system initialization...")
    try:
        from alice_vision import AliceVision
        vision = AliceVision()
        print("✅ Vision system initialized")
    except Exception as e:
        print(f"❌ Vision system failed: {e}")
        return False
    
    # Test 3: Check if EasyOCR is working
    print("\n3. Testing EasyOCR engine...")
    try:
        result = vision.extract_text_from_image("temp_alice_files/vision/test_ocr_image.png")
        if result['success']:
            print(f"✅ EasyOCR working: '{result['text']}'")
        else:
            print(f"❌ EasyOCR failed: {result['error']}")
            return False
    except Exception as e:
        print(f"❌ EasyOCR engine error: {e}")
        return False
    
    # Test 4: Test agent tools directly
    print("\n4. Testing agent OCR tools...")
    try:
        # Test reading from test image
        if os.path.exists("temp_alice_files/vision/test_ocr_image.png"):
            result = await read_text_from_image("temp_alice_files/vision/test_ocr_image.png")
            print("✅ read_text_from_image result:")
            print(result[:200] + "..." if len(result) > 200 else result)
        else:
            print("⚠️ Test image not found, creating one...")
            # Create a simple test image
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new('RGB', (300, 100), color='white')
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            draw.text((10, 40), "TEST: Alice should read this!", fill='black', font=font)
            
            os.makedirs("temp_alice_files/vision", exist_ok=True)
            test_path = "temp_alice_files/vision/debug_test_image.png"
            img.save(test_path)
            
            result = await read_text_from_image(test_path)
            print("✅ Created test image and read result:")
            print(result[:200] + "..." if len(result) > 200 else result)
            
    except Exception as e:
        print(f"❌ Agent tools test failed: {e}")
        return False
    
    # Test 5: Test screen reading
    print("\n5. Testing screen text reading...")
    try:
        result = await read_screen_text()
        if "📱 SCREEN TEXT READING:" in result:
            print("✅ Screen reading working")
            print(f"   Found {len(result)} characters of text")
        else:
            print(f"⚠️ Screen reading result: {result[:100]}...")
    except Exception as e:
        print(f"❌ Screen reading failed: {e}")
        return False
    
    print("\n=== OCR DEBUG COMPLETED ===")
    return True

if __name__ == "__main__":
    success = asyncio.run(debug_alice_ocr())
    if success:
        print("\n✅ OCR DEBUGGING: All systems operational")
    else:
        print("\n❌ OCR DEBUGGING: Issues found")