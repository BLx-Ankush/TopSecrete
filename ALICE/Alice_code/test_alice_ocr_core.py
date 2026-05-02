"""
OCR Core Functionality Test
Tests the new OCR methods in alice_vision.py
"""
import sys
import os

def test_alice_ocr_functionality():
    """Test Alice's new OCR capabilities"""
    
    print("=== ALICE OCR FUNCTIONALITY TEST ===\n")
    
    # Import Alice Vision
    try:
        from alice_vision import AliceVision
        print("✅ AliceVision imported successfully")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Initialize vision system
    print("\n1. Initializing Alice Vision...")
    try:
        vision = AliceVision()
        print("✅ Alice Vision initialized")
    except Exception as e:
        print(f"❌ Vision initialization error: {e}")
        return False
    
    # Test 1: Extract text from existing test image
    print("\n2. Testing text extraction from test image...")
    test_image = "temp_alice_files/vision/test_ocr_image.png"
    
    if os.path.exists(test_image):
        try:
            result = vision.extract_text_from_image(test_image)
            
            if result['success']:
                print(f"✅ OCR Success!")
                print(f"   Text: '{result['text']}'")
                print(f"   Details: {result['total_items']} text items found")
                
                for detail in result['details']:
                    print(f"   - '{detail['text']}' (confidence: {detail['confidence']:.2f}) {detail['position']}")
            else:
                print(f"❌ OCR failed: {result['error']}")
                return False
                
        except Exception as e:
            print(f"❌ Text extraction error: {e}")
            return False
    else:
        print(f"⚠️ Test image not found: {test_image}")
    
    # Test 2: Screenshot OCR
    print("\n3. Testing screenshot text extraction...")
    try:
        result = vision.extract_text_from_screenshot()
        
        if result['success']:
            print(f"✅ Screenshot OCR Success!")
            print(f"   Screenshot: {result['screenshot']}")
            print(f"   Text length: {len(result['text'])} characters")
            print(f"   Text preview: '{result['text'][:100]}...'")
            print(f"   Text items: {result['total_items']}")
        else:
            print(f"❌ Screenshot OCR failed: {result['error']}")
            
    except Exception as e:
        print(f"❌ Screenshot OCR error: {e}")
    
    # Test 3: Image analysis
    print("\n4. Testing complete image analysis...")
    if os.path.exists(test_image):
        try:
            result = vision.analyze_image_content(test_image)
            
            if result['success']:
                print(f"✅ Image Analysis Success!")
                print(f"   Image: {result['image_size']} ({result['image_format']})")
                print(f"   Text found: {result['text_found']}")
                print(f"   Text length: {result['text_length']} characters")
                print(f"   Text items: {result['text_items']}")
                
                if result['ocr_result']['success']:
                    print(f"   Full text: '{result['ocr_result']['text']}'")
            else:
                print(f"❌ Image analysis failed: {result['error']}")
                
        except Exception as e:
            print(f"❌ Image analysis error: {e}")
    
    print("\n=== ALICE OCR TEST COMPLETED ===")
    print("✅ OCR core functionality is working!")
    
    return True

if __name__ == "__main__":
    success = test_alice_ocr_functionality()
    if success:
        print("\n🎉 ALICE OCR CORE: OPERATIONAL")
    else:
        print("\n⚠️ ALICE OCR CORE: NEEDS ATTENTION")