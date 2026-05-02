from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, ChatContext, ChatMessage
from livekit.plugins import google, noise_cancellation
import logging
import os
import sys

# Fix Windows Unicode encoding issues
if sys.platform == "win32":
    # Set UTF-8 encoding for stdout/stderr to handle Unicode characters
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    # Set environment variable for Python to use UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Import your custom modules
from Alice_prompts import instructions_prompt, Reply_prompts
from memory_loop import MemoryExtractor
from memory_store import ConversationMemory
# from alice_reasoning import thinking_capability
# MCP imports temporarily disabled due to dependency conflict
# from mcp_client.server import MCPServerSse
# from mcp_client.agent_tools import MCPToolsIntegration

# Import Safe Personal Mode with automation capabilities
from alice_personal_safe import (
    enable_personal_mode,
    disable_personal_mode, 
    open_application,
    check_personal_mode,
    refresh_app_database_tool,
    show_available_apps,
    perform_multi_app_task,
    create_file_and_open,
    open_vscode_new_window,
    open_browser,
    capture_screenshot,
    adjust_brightness,
    search_files_system,
    advanced_system_operations
)

# Import Alice Vision Tools (optional)
try:
    from alice_vision_tools import ALICE_VISION_TOOLS
    VISION_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Alice Vision Tools not available: {e}")
    ALICE_VISION_TOOLS = []
    VISION_AVAILABLE = False

# Import WhatsApp Automation
from alice_whatsapp_automation import (
    send_whatsapp_message,
    open_whatsapp_chat,
    whatsapp_automation_help
)

# Set up logging before optional imports that may log.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Browser Automation (optional)
try:
    from alice_browser_automation_integration import (
        initialize_browser_automation,
        shutdown_browser_automation,
        get_browser_automation_tools,
        check_browser_automation_available
    )
    BROWSER_AUTOMATION_AVAILABLE = True
    logger.info("✅ Browser Automation module loaded")
except ImportError as e:
    logger.warning(f"⚠️  Browser Automation not available: {e}")
    BROWSER_AUTOMATION_AVAILABLE = False
    get_browser_automation_tools = lambda: []
    initialize_browser_automation = None
    shutdown_browser_automation = None

# Optional mem0 import
try:
    from mem0 import AsyncMemoryClient
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    AsyncMemoryClient = None

# Initialize Mem0 client for persistent memory
mem0_client = None
if MEM0_AVAILABLE:
    try:
        mem0_client = AsyncMemoryClient(api_key=os.getenv("MEM0_API_KEY"))
        logger.info("Mem0 client initialized successfully")
    except Exception as e:
        logger.warning(f"Mem0 client not available: {e}")
        mem0_client = None
else:
    logger.info("Mem0 not installed - memory features disabled")

user_id = "Ankush"


load_dotenv()

async def entrypoint(ctx: agents.JobContext):
    """Enhanced entrypoint with MCP and Mem0 integration"""
    
    # 1. TOOL INITIALIZATION: Initialize all tools and dynamic MCP tools
    logger.info("Initializing enhanced Alice agent with MCP and Mem0")

    # 2. Setup MCP servers for extended functionality (temporarily disabled)
    # mcp_servers = []
    
    # Example: File system MCP server (if available)
    # try:
    #     # Add your MCP servers here - example commented out
    #     # fs_server = MCPServerSse("http://localhost:8080/sse", name="filesystem")
    #     # mcp_servers.append(fs_server)
    #     pass
    # except Exception as e:
    #     logger.warning(f"MCP servers not available: {e}")
    
    # Prepare MCP tools if servers are available
    mcp_tools = []
    # if mcp_servers:
    #     try:
    #         mcp_tools = await MCPToolsIntegration.prepare_dynamic_tools(mcp_servers)
    #         logger.info(f"Loaded {len(mcp_tools)} MCP tools")
    #     except Exception as e:
    #         logger.error(f"Failed to load MCP tools: {e}")
    
    # 3. Initialize Browser Automation (if available)
    browser_tools = []
    if BROWSER_AUTOMATION_AVAILABLE:
        try:
            logger.info("Initializing browser automation engine...")
            await initialize_browser_automation()
            browser_tools = get_browser_automation_tools()
            logger.info(f"✅ Browser automation ready with {len(browser_tools)} tools")
        except Exception as e:
            logger.error(f"Failed to initialize browser automation: {e}")
            logger.warning("Continuing without browser automation")
    
    # Combine built-in tools with MCP tools, Alice Vision, and Browser Automation
    all_tools = [
        enable_personal_mode,
        disable_personal_mode,
        open_application,
        check_personal_mode,
        refresh_app_database_tool,
        show_available_apps,
        perform_multi_app_task,
        create_file_and_open,
        open_vscode_new_window,
        open_browser,
        capture_screenshot,
        adjust_brightness,
        search_files_system,
        advanced_system_operations,
        # WhatsApp automation tools
        send_whatsapp_message,
        open_whatsapp_chat,
        whatsapp_automation_help
    ] + mcp_tools + ALICE_VISION_TOOLS + browser_tools

    # 4. STARTUP MEMORY: Fetch existing memories before the agent starts
    logger.info(f"Fetching initial memories for user: {user_id}")
    try:
        if os.getenv("MEM0_API_KEY"):
            # Use our fixed ConversationMemory class
            conversation_memory = ConversationMemory(user_id)
            memories = conversation_memory.get_all_memories()
            
            # Format them into a string
            if memories:
                memory_texts = []
                for memory in memories[:10]:  # Limit to last 10 memories for context
                    memory_text = memory.get('memory', '')
                    if memory_text:
                        memory_texts.append(memory_text)
                
                if memory_texts:
                    memory_str = f"\n\nKNOWN USER HISTORY:\n" + "\n".join(memory_texts)
                else:
                    memory_str = "\n(No previous history found.)"
            else:
                memory_str = "\n(No previous history found.)"
        else:
            memory_str = "\n(Memory system not configured - add MEM0_API_KEY to enable)"
            
    except Exception as e:
        logger.error(f"Error fetching initial memories: {e}")
        memory_str = "\n(Memory system unavailable)"

    # Create initial context with memory
    initial_ctx = ChatContext()
    initial_ctx.add_message(role="assistant", 
                            content=f'''The user's name is {user_id}.
                            {memory_str}''')

    # 3. BUILD AGENT: Create agent with enhanced tools
    enhanced_agent = Assistant(chat_ctx=initial_ctx, tools_list=all_tools)

    # 5. Configure the Session with stable settings
    session = AgentSession(
        preemptive_generation=True
    )

    try:
        await session.start(
            room=ctx.room,
            agent=enhanced_agent,
            room_input_options=RoomInputOptions(
                noise_cancellation=noise_cancellation.BVC()
            ),
        )
        await session.generate_reply(
            instructions=Reply_prompts
        )
        
        # Start memory extractor to save conversations
        # Get the actual conversation history AFTER the session has started
        conv_ctx = MemoryExtractor()
        # Start memory saving in background (non-blocking)
        import asyncio
        asyncio.create_task(conv_ctx.run(session.history.items))
        
        # Wait for session to end - AgentSession doesn't have wait_for_completion
        # The session will run until the room is closed or an error occurs
        
    finally:
        # Cleanup browser automation on shutdown
        if BROWSER_AUTOMATION_AVAILABLE and shutdown_browser_automation:
            try:
                logger.info("Cleaning up browser automation...")
                await shutdown_browser_automation()
            except Exception as e:
                logger.error(f"Error during browser automation cleanup: {e}")


class Assistant(Agent):
    def __init__(self, chat_ctx, tools_list) -> None:
        super().__init__(
            instructions=instructions_prompt,
            chat_ctx=chat_ctx,
            llm=google.beta.realtime.RealtimeModel(
                model="gemini-2.5-flash-native-audio-preview-12-2025",
                voice="Erinome"
            ),
            tools=tools_list
        )


if __name__ == "__main__":
    import sys
    import asyncio
    
    # --- Windows Specific Fix ---
    if sys.platform == "win32":
        # Force the use of ProactorEventLoop on Windows
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        # Create a loop manually to avoid the "no current event loop" error
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    # ----------------------------

    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))

    