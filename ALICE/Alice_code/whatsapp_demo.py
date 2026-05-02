#!/usr/bin/env python3
"""
Alice WhatsApp Automation Demo
Demonstrates how to use Alice's WhatsApp features
"""

import asyncio
from alice_personal_safe import (
    send_whatsapp_message_alice, 
    open_whatsapp_chat_alice, 
    whatsapp_help_alice,
    enable_personal_mode
)

async def demo_whatsapp_automation():
    """Demo Alice's WhatsApp capabilities"""
    
    print("🚀 Alice WhatsApp Automation Demo")
    print("=" * 50)
    
    # Enable personal mode for full access
    print("\n1. Enabling Personal Mode...")
    personal_mode_result = await enable_personal_mode()
    print(personal_mode_result)
    
    # Show help
    print("\n2. WhatsApp Help & Instructions...")
    help_result = await whatsapp_help_alice()
    print(help_result)
    
    print("\n" + "=" * 50)
    print("💡 Demo Commands You Can Try:")
    print("=" * 50)
    
    demo_commands = [
        "# Open a chat",
        "result = await open_whatsapp_chat_alice('Mom')",
        "",
        "# Send a message", 
        "result = await send_whatsapp_message_alice('Mom', 'Hello from Alice! 🤖')",
        "",
        "# Multiple contacts",
        "result = await send_whatsapp_message_alice('Dad', 'Dinner ready!')",
        "result = await send_whatsapp_message_alice('Brother', 'Happy Birthday!')"
    ]
    
    for cmd in demo_commands:
        if cmd.startswith("#"):
            print(f"\n{cmd}")
        elif cmd == "":
            print()
        else:
            print(f"  {cmd}")
    
    print(f"\n📝 Note: Replace 'Mom', 'Dad' etc. with actual contact names from your WhatsApp")
    print(f"🔧 Make sure WhatsApp Desktop is installed and you're logged in!")
    
    return "Demo completed! Ready to use WhatsApp automation. 🎉"

# For standalone testing
if __name__ == "__main__":
    result = asyncio.run(demo_whatsapp_automation())
    print(f"\n✅ {result}")