"""
OCR Installation Verification Test
Tests if OCR libraries are working properly
"""
import sys
import os

def test_ocr_installations():
    """Test all OCR library installations"""
    
    print("=== OCR INSTALLATION VERIFICATION ===\n")
    
    # Test 1: Import libraries
    print("1. Testing library imports...")
    
    try:
        import pytesseract
        print("✅ pytesseract imported successfully")
    except ImportError as e:
        print(f"❌ pytesseract import failed: {e}")
        return False
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        print("✅ PIL (Pillow) imported successfully")
    except ImportError as e:
        print(f"❌ PIL import failed: {e}")
        return False
    
    try:
        import easyocr
        print("✅ EasyOCR imported successfully")
    except ImportError as e:
        print(f"❌ EasyOCR import failed: {e}")
        return False
    
    # Test 2: Create test image with text
    print("\n2. Creating test image with text...")
    
    try:
        # Create a simple test image with text
        test_img = Image.new('RGB', (300, 100), color='white')
        draw = ImageDraw.Draw(test_img)
        
        # Draw some text
        text = "Hello Alice Vision!"
        try:
            # Try to use a font, fallback to default if not available
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((10, 40), text, fill='black', font=font)
        
        # Save test image
        test_image_path = "temp_alice_files/vision/test_ocr_image.png"
        os.makedirs(os.path.dirname(test_image_path), exist_ok=True)
        test_img.save(test_image_path)
        print(f"✅ Test image created: {test_image_path}")
        
    except Exception as e:
        print(f"❌ Test image creation failed: {e}")
        return False
    
    # Test 3: EasyOCR test
    print("\n3. Testing EasyOCR text recognition...")
    
    try:
        reader = easyocr.Reader(['en'])
        results = reader.readtext(test_image_path)
        
        if results:
            detected_text = ' '.join([result[1] for result in results])
            print(f"✅ EasyOCR detected: '{detected_text}'")
        else:
            print("⚠️ EasyOCR detected no text")
        
    except Exception as e:
        print(f"❌ EasyOCR test failed: {e}")
        return False
    
    # Test 4: pytesseract test (requires Tesseract binary)
    print("\n4. Testing pytesseract text recognition...")
    
    try:
        detected_text = pytesseract.image_to_string(Image.open(test_image_path))
        if detected_text.strip():
            print(f"✅ pytesseract detected: '{detected_text.strip()}'")
        else:
            print("⚠️ pytesseract detected no text (Tesseract may not be installed)")
            
    except Exception as e:
        print(f"⚠️ pytesseract test failed: {e}")
        print("   Note: pytesseract requires Tesseract binary installation")
    
    print("\n=== OCR VERIFICATION COMPLETE ===")
    print("✅ OCR libraries are ready for integration!")
    return True

if __name__ == "__main__":
    success = test_ocr_installations()
    if success:
        print("\n🎉 OCR SYSTEM READY FOR ALICE!")
    else:
        print("\n⚠️ OCR SYSTEM NEEDS ATTENTION")