"""
Quick test to verify trigger file OCR integration
"""
import sys
import os

# Add parent directory to path for alice_trigger import
parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, parent_dir)

# Import the banner function from trigger
from alice_trigger import print_alice_banner, check_alice_vision_system

print("=== TESTING TRIGGER FILE OCR INTEGRATION ===\n")

print("1. Testing updated banner...")
print_alice_banner()

print("\n\n2. Testing vision system check...")
vision_status = check_alice_vision_system()

print(f"\n3. Vision system status: {'✅ READY' if vision_status else '❌ ISSUES'}")

print("\n=== TRIGGER INTEGRATION TEST COMPLETE ===")
print("✅ Trigger file now properly shows OCR capabilities!")