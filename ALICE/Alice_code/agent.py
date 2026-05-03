from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, ChatContext, ChatMessage
from livekit.plugins import google, noise_cancellation, silero
import logging
import os
import sys
import socket
from urllib.parse import urlparse

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

# Import Audio Configuration for NVIDIA Broadcast integration
from livekit_audio_config import (
    configure_livekit_audio_input,
    log_audio_device_selection,
    get_audio_device_info_for_voice_report
)
from audio_quality_validator import (
    validate_audio_quality_on_session_start,
    log_audio_quality_validation,
    get_audio_quality_voice_report
)

# Import VAD Configuration
from vad_config import (
    get_vad_silence_threshold,
    log_vad_configuration
)

# Import VAD Behavior Validation
from vad_behavior_validator import (
    validate_vad_behavior,
    log_vad_validation_results,
    get_vad_validation_voice_report
)

# Import VAD Turn-Taking Monitor
from vad_turn_taking_monitor import (
    get_turn_taking_monitor,
    reset_turn_taking_monitor
)

# Import Interim Transcription Handler (Deepgram Nova-3 equivalent for Gemini)
from interim_transcription_integration import setup_interim_transcription

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

# Servo control tool
from alice_servo_control import control_servo_motor

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

_DOTENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=_DOTENV_PATH, override=False)


def _preflight_livekit_dns() -> bool:
    """Fail fast with a clear message if LIVEKIT_URL is missing or DNS can't resolve.

    The LiveKit Agents worker otherwise retries forever, which hides the real issue.
    """
    livekit_url = (os.getenv("LIVEKIT_URL") or "").strip()
    if not livekit_url:
        logger.error(
            "LIVEKIT_URL is not set. Set it in %s (or environment) before starting.",
            _DOTENV_PATH,
        )
        return False

    parsed = urlparse(livekit_url)
    host = parsed.hostname
    scheme = (parsed.scheme or "").lower()
    port = parsed.port
    if port is None:
        port = 443 if scheme in {"wss", "https"} else 80

    if not host:
        logger.error(
            "LIVEKIT_URL looks invalid (%r). Expected e.g. wss://<project>.livekit.cloud",
            livekit_url,
        )
        return False

    try:
        # Resolve host -> addresses (DNS). This is what fails with socket.gaierror.
        socket.getaddrinfo(host, port)
        return True
    except socket.gaierror as exc:
        logger.error(
            "Cannot resolve LiveKit host %s:%s from LIVEKIT_URL=%r (DNS error: %s).",
            host,
            port,
            livekit_url,
            exc,
        )
        logger.error(
            "Fix: check internet/DNS, or update LIVEKIT_URL. For local dev you can use LIVEKIT_URL=ws://localhost:7880 with a local LiveKit server."
        )
        return False

async def entrypoint(ctx: agents.JobContext):
    """Enhanced entrypoint with MCP and Mem0 integration"""
    
    # 1. AUDIO CONFIGURATION: Configure NVIDIA Broadcast audio input
    logger.info("=" * 60)
    logger.info("Configuring audio input for LiveKit session")
    logger.info("=" * 60)
    
    # Configure audio device (NVIDIA Broadcast or fallback)
    audio_config = configure_livekit_audio_input()
    log_audio_device_selection(audio_config)
    
    # Validate audio quality on session start
    audio_device_index = int(audio_config['device_id']) if audio_config.get('device_id') else None
    audio_validation = validate_audio_quality_on_session_start(device_index=audio_device_index)
    log_audio_quality_validation(audio_validation)
    
    # Prepare voice report for user
    audio_status_message = get_audio_device_info_for_voice_report()
    if not audio_validation['passed']:
        audio_status_message += " " + get_audio_quality_voice_report(audio_validation)
    
    logger.info(f"Audio status message for user: {audio_status_message}")
    
    # 2. TOOL INITIALIZATION: Initialize all tools and dynamic MCP tools
    logger.info("Initializing enhanced Alice agent with MCP and Mem0")
    
    # 2.1 VAD CONFIGURATION: Configure Voice Activity Detection
    logger.info("=" * 60)
    logger.info("Configuring Voice Activity Detection (VAD)")
    logger.info("=" * 60)
    
    # Get VAD silence threshold from configuration
    vad_silence_threshold = get_vad_silence_threshold()
    log_vad_configuration(vad_silence_threshold)
    
    # Initialize Silero VAD with configured silence threshold
    vad = silero.VAD.load(
        min_silence_duration=vad_silence_threshold,
        # Additional VAD parameters for optimal performance
        min_speech_duration=0.05,  # Minimum speech duration to start detection (50ms)
        prefix_padding_duration=0.5,  # Padding before speech starts (500ms)
        activation_threshold=0.5,  # Threshold to consider a frame as speech
    )
    
    logger.info(f"✅ VAD configured with {vad_silence_threshold * 1000:.0f}ms silence threshold")
    
    # 2.2 VAD BEHAVIOR VALIDATION: Validate VAD behavior meets requirements
    logger.info("=" * 60)
    logger.info("Validating VAD Behavior")
    logger.info("=" * 60)
    
    # Run VAD behavior validation
    vad_validation_summary = validate_vad_behavior(vad, vad_silence_threshold * 1000)
    log_vad_validation_results(vad_validation_summary)
    
    # Prepare voice report for VAD validation
    vad_validation_message = get_vad_validation_voice_report(vad_validation_summary)
    logger.info(f"VAD validation message for user: {vad_validation_message}")
    
    # 2.3 TURN-TAKING MONITOR: Initialize turn-taking monitor
    logger.info("=" * 60)
    logger.info("Initializing Turn-Taking Monitor")
    logger.info("=" * 60)
    
    # Create unique session ID
    import uuid
    session_id = str(uuid.uuid4())[:8]
    turn_taking_monitor = get_turn_taking_monitor(session_id=session_id)
    logger.info(f"✅ Turn-taking monitor initialized for session: {session_id}")

    # 3. Setup MCP servers for extended functionality (temporarily disabled)
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
    
    # 4. Initialize Browser Automation (if available)
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
        whatsapp_automation_help,
        # Servo control tool
        control_servo_motor
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
    enhanced_agent = Assistant(chat_ctx=initial_ctx, tools_list=all_tools, vad_instance=vad)

    # 4. Configure the Session with stable settings
    session = AgentSession(
        preemptive_generation=True
    )
    
    # 5. INTERIM TRANSCRIPTION: Set up interim transcription handling
    # This provides Deepgram Nova-3 equivalent functionality for the Gemini Realtime Model
    logger.info("=" * 60)
    logger.info("Configuring interim transcription processing")
    logger.info("=" * 60)
    
    interim_integration = setup_interim_transcription(session)
    
    # Optional: Register custom callbacks for interim results
    def on_interim_transcript(transcript):
        """Called when interim transcription results arrive"""
        logger.debug(f"[Interim] Processing: {transcript.text[:30]}...")
    
    def on_final_transcript(transcript, differs_from_interim):
        """Called when final transcription arrives"""
        if differs_from_interim:
            logger.info(f"[Final] Reconciled transcript: {transcript.text[:50]}...")
    
    interim_integration.register_interim_callback(on_interim_transcript)
    interim_integration.register_final_callback(on_final_transcript)

    try:
        # Note: Audio device configuration (NVIDIA Broadcast) is handled at the system level
        # Windows should be configured to use "Microphone (NVIDIA Broadcast)" as default recording device
        # LiveKit will automatically use the system default microphone
        await session.start(
            room=ctx.room,
            agent=enhanced_agent,
            room_input_options=RoomInputOptions(
                noise_cancellation=noise_cancellation.BVC()
            ),
        )
        
        # Report audio status to user via voice
        status_messages = [audio_status_message]
        
        # Add VAD validation message if there were issues
        if not vad_validation_summary['all_passed']:
            status_messages.append(vad_validation_message)
        
        combined_status = " ".join(status_messages)
        
        await session.generate_reply(
            instructions=f"{Reply_prompts}\n\nIMPORTANT: After greeting, inform the user: {combined_status}"
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
        # Log turn-taking session summary
        if turn_taking_monitor:
            turn_taking_monitor.log_session_summary()
        
        # Cleanup browser automation on shutdown
        if BROWSER_AUTOMATION_AVAILABLE and shutdown_browser_automation:
            try:
                logger.info("Cleaning up browser automation...")
                await shutdown_browser_automation()
            except Exception as e:
                logger.error(f"Error during browser automation cleanup: {e}")


class Assistant(Agent):
    def __init__(self, chat_ctx, tools_list, vad_instance) -> None:
        super().__init__(
            instructions=instructions_prompt,
            chat_ctx=chat_ctx,
            llm=google.beta.realtime.RealtimeModel(
                model="gemini-2.5-flash-native-audio-preview-12-2025",
                voice="Erinome"
            ),
            tools=tools_list,
            vad=vad_instance  # Pass VAD instance to Agent
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

    if not _preflight_livekit_dns():
        raise SystemExit(2)

    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))

    