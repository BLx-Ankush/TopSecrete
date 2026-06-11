"""
Automated Test Suite for ALICE's Upgraded Architecture
This script loads the ToolRegistry and performs safe integration testing.
It avoids executing destructive commands (like sending real messages or clicking randomly).
"""

import asyncio
import logging
import inspect
import sys
from pathlib import Path

# Fix Windows console UTF-8 encoding for emojis
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

async def run_tests():
    logger.info("=== ALICE Architecture Verification Suite ===")
    
    # 1. Test Tool Registry Loading
    logger.info("\n--- Test 1: Tool Registry ---")
    try:
        sys.path.append(r"d:\ALICE(NEW)\Alice Upgraded\Alice (Alpha)\ALICE\Alice_code")
        
        from tool_registry import ToolRegistry
        logger.info("ToolRegistry imported successfully.")
        
        tools = await ToolRegistry.get_all_tools(browser_automation_available=False)
        logger.info(f"Loaded {len(tools)} tools from registry.")
        
        # Verify specific tools are present
        tool_names = [t.__name__ if hasattr(t, '__name__') else t.name for t in tools]
        
        assert "semantic_click" in tool_names, "Missing semantic_click tool"
        assert "semantic_type_into" in tool_names, "Missing semantic_type_into tool"
        assert "send_whatsapp_message" in tool_names, "Missing send_whatsapp_message tool"
        logger.info("✅ All core Phase 3 tools are present in the registry.")
    except Exception as e:
        logger.error(f"❌ Tool Registry test failed: {e}")

    # 2. Test Fluidity Metrics initialization
    logger.info("\n--- Test 2: Fluidity Metrics ---")
    try:
        from fluidity_metrics import FluidityMetricsManager
        metrics = FluidityMetricsManager()
        metrics.initialize_monitors()
        metrics.initialize_fluidity_enhancements()
        logger.info("✅ FluidityMetricsManager initializes sub-components successfully.")
    except Exception as e:
        logger.error(f"❌ Fluidity metrics test failed: {e}")

    # 3. Test Memory Injector initialization
    logger.info("\n--- Test 3: Memory Injector ---")
    try:
        from memory_injector import MemoryInjector
        
        # Mock streaming client
        class MockClient:
            state = 1
            async def _send_message(self, msg):
                pass
                
        injector = MemoryInjector(user_id="test_user", streaming_client=MockClient())
        injector.record_turn("Hello ALICE")
        logger.info(f"Recent turns buffered: {injector._recent_turns}")
        logger.info("✅ MemoryInjector initializes and buffers turns successfully.")
    except Exception as e:
        logger.error(f"❌ Memory Injector test failed: {e}")

    # 4. Test Semantic Vision availability
    logger.info("\n--- Test 4: Semantic Vision Engine ---")
    try:
        from alice_semantic_vision import get_semantic_vision_engine
        import os
        if "GEMINI_API_KEY" not in os.environ:
            os.environ["GEMINI_API_KEY"] = "mock_key_for_testing"
        
        engine = get_semantic_vision_engine()
        logger.info(f"Semantic Vision Engine initialized: {engine}")
        logger.info("✅ Semantic Vision Engine loads successfully.")
    except Exception as e:
        logger.error(f"❌ Semantic Vision test failed: {e}")
        
    logger.info("\n=== Testing Complete ===")

if __name__ == "__main__":
    asyncio.run(run_tests())
