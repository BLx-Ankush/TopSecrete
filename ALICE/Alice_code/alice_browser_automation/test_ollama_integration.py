"""
Simple test to verify Ollama and Qwen model integration
"""
import requests
import json

def test_ollama_connection():
    """Test if Ollama service is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            print("✅ Ollama service is running")
            models = response.json().get("models", [])
            print(f"   Found {len(models)} models:")
            for model in models:
                print(f"   - {model['name']}")
            return True
        else:
            print(f"❌ Ollama service returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to Ollama: {e}")
        return False

def test_qwen_model():
    """Test if Qwen model can generate responses"""
    try:
        payload = {
            "model": "qwen2.5-coder:3b",
            "prompt": "Generate a JSON object with a single field 'message' containing 'Hello World'",
            "stream": False
        }
        
        print("\n🔄 Testing Qwen model generation...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("response", "")
            print(f"✅ Qwen model generated response:")
            print(f"   {generated_text[:200]}...")
            print(f"   Total tokens: {result.get('eval_count', 'N/A')}")
            print(f"   Generation time: {result.get('total_duration', 0) / 1e9:.2f}s")
            return True
        else:
            print(f"❌ Model generation failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to generate with Qwen model: {e}")
        return False

def test_json_generation():
    """Test if Qwen model can generate valid JSON"""
    try:
        payload = {
            "model": "qwen2.5-coder:3b",
            "prompt": """Generate a valid JSON object for a browser action with these fields:
- action_type: "click"
- target_selector: {"css_selector": "button.submit"}
- parameters: {}
- expected_result: "Form submitted"

Return ONLY the JSON object, no explanation.""",
            "stream": False,
            "format": "json"
        }
        
        print("\n🔄 Testing JSON generation...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("response", "")
            print(f"✅ Qwen model generated JSON:")
            print(f"   {generated_text}")
            
            # Try to parse as JSON
            try:
                parsed = json.loads(generated_text)
                print(f"✅ JSON is valid!")
                print(f"   Keys: {list(parsed.keys())}")
                return True
            except json.JSONDecodeError as e:
                print(f"⚠️  Generated text is not valid JSON: {e}")
                return False
        else:
            print(f"❌ JSON generation failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to test JSON generation: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Ollama and Qwen Model Integration Test")
    print("=" * 60)
    
    # Test 1: Ollama connection
    ollama_ok = test_ollama_connection()
    
    if not ollama_ok:
        print("\n❌ Ollama service is not running. Please start it with: ollama serve")
        exit(1)
    
    # Test 2: Qwen model generation
    qwen_ok = test_qwen_model()
    
    # Test 3: JSON generation
    json_ok = test_json_generation()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    print(f"Ollama Connection: {'✅ PASS' if ollama_ok else '❌ FAIL'}")
    print(f"Qwen Generation:   {'✅ PASS' if qwen_ok else '❌ FAIL'}")
    print(f"JSON Generation:   {'✅ PASS' if json_ok else '❌ FAIL'}")
    
    if ollama_ok and qwen_ok and json_ok:
        print("\n🎉 All tests passed! Ollama and Qwen are ready for Alice integration.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
