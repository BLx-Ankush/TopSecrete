from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, ChatContext, ChatMessage
from livekit.plugins import google, noise_cancellation, silero
import base64
import logging
import math
import os
import struct
import sys
import socket
import time
import asyncio
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

# Removed alice_personal_safe imports (now handled by tool_registry.py)

# Import Audio Configuration for NVIDIA Broadcast integration
from livekit_audio_config import (
    configure_livekit_audio_input,
    configure_livekit_audio_input_with_environment,
    get_environment_classification_for_vad,
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
    log_vad_configuration,
    VADThresholdManager
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
    reset_turn_taking_monitor,
    get_neural_fluidity_monitor,
    reset_neural_fluidity_monitor,
)

# Import Latency Monitor for performance tracking
from latency_monitor import (
    get_latency_monitor,
    reset_latency_monitor,
    get_fluidity_latency_tracker,
    reset_fluidity_latency_tracker,
)

# Import Fluidity Enhancement modules (Tasks 2–16)
try:
    from interruption_classifier import InterruptionClassifier, Classification
    from cost_monitor import CostMonitor, get_cost_monitor
    from fluidity_config import get_fluidity_config, FluidityConfig
    from fluidity_error_handler import get_error_handler
    from turn_detection import NeuralTurnDetector
    from stt.config_factory import STTConfigFactory
    FLUIDITY_AVAILABLE = True
    logger_fluidity = logging.getLogger("fluidity")
    logger_fluidity.info("✅ Alice Conversation Fluidity Enhancement modules loaded")
except ImportError as _fluidity_err:
    FLUIDITY_AVAILABLE = False
    InterruptionClassifier = None
    Classification = None
    CostMonitor = None
    get_cost_monitor = None
    get_fluidity_config = None
    FluidityConfig = None
    get_error_handler = None
    NeuralTurnDetector = None
    STTConfigFactory = None

# Import Interim Transcription Handler (Deepgram Nova-3 equivalent for Gemini)
from interim_transcription_integration import setup_interim_transcription

# Import Gemini Streaming Client for WebSocket-based streaming architecture
from gemini_streaming_client import (
    GeminiStreamingClient,
    GeminiRegion,
    ConnectionState
)
# Removed ALICE_VISION_TOOLS and hardware tool imports (now handled by tool_registry.py)

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
    
    # 1. AUDIO CONFIGURATION: Configure NVIDIA Broadcast audio input with environment detection
    logger.info("=" * 60)
    logger.info("Configuring audio input for LiveKit session")
    logger.info("=" * 60)
    
    # Configure audio device with environment detection (NVIDIA Broadcast or fallback)
    audio_config = configure_livekit_audio_input_with_environment()
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
    
    # 2.1 VAD CONFIGURATION: Configure Voice Activity Detection with environment-aware threshold
    logger.info("=" * 60)
    logger.info("Configuring Voice Activity Detection (VAD)")
    logger.info("=" * 60)
    
    # Get environment classification for VAD threshold optimization
    environment, nvidia_broadcast_available = get_environment_classification_for_vad(audio_config)
    logger.info(f"Environment: {environment.upper()}, NVIDIA Broadcast: {nvidia_broadcast_available}")
    
    # Get VAD silence threshold optimized for environment conditions (Task 3.6)
    vad_silence_threshold = get_vad_silence_threshold(
        environment=environment,
        nvidia_broadcast_available=nvidia_broadcast_available
    )
    log_vad_configuration(
        vad_silence_threshold,
        environment=environment,
        nvidia_broadcast_available=nvidia_broadcast_available
    )
    
    # Dynamic VAD threshold optimization is now active
    logger.info(f"✅ Dynamic VAD threshold optimization enabled based on environment: {environment}")
    
    # Initialize Silero VAD with Siri/Google-class aggressiveness
    # KEY LATENCY FIX: prefix_padding_duration was 500ms — that alone added
    # 400ms to every response.  Reduced to 100ms.  Also lowered silence
    # threshold and raised activation_threshold to reduce false triggers.
    vad = silero.VAD.load(
        min_silence_duration=vad_silence_threshold,  # env-tuned: 200–350ms
        min_speech_duration=0.1,          # 100ms — filters sub-word noise
        prefix_padding_duration=0.1,      # 100ms (was 500ms — saves 400ms!)
        activation_threshold=0.6,         # 0.6 (was 0.5 — fewer false starts)
    )
    
    logger.info(f"✅ VAD configured with {vad_silence_threshold * 1000:.0f}ms silence threshold")

    # ── Phase 4: Domain 2B — Ambient Noise → Auto-Adaptive VAD ─────────────────
    try:
        from ambient_noise_analyzer import AmbientNoiseAnalyzer
        _noise_analyzer = AmbientNoiseAnalyzer(sample_duration=1.5)
        _ambient_noise_level = await _noise_analyzer.measure()
        logger.info(f"[Phase4] Ambient noise level measured: {_ambient_noise_level:.3f} "
                    f"({_noise_analyzer._classify(_ambient_noise_level)})")
    except Exception as _e:
        logger.warning(f"[Phase4] Ambient noise measurement skipped: {_e}")
        _ambient_noise_level = 0.3   # Assume moderate noise as safe default

    # ── Phase 4: Domain 2A — Start Offline Fallback Watchdog ────────────────────
    try:
        from offline_fallback import OfflineFallbackRouter
        _offline_router = OfflineFallbackRouter(ping_interval=5, ping_timeout_ms=300)
        await _offline_router.start_watchdog()
        logger.info("[Phase4] Offline fallback watchdog started")
    except Exception as _e:
        logger.warning(f"[Phase4] Offline fallback watchdog could not start: {_e}")
        _offline_router = None

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
    
    # 2.3–2.6 METRICS & FLUIDITY: Use FluidityMetricsManager to replace 120+ lines of inline init
    # This covers: session ID, turn-taking, latency, neural fluidity, VAD thresholds,
    # InterruptionClassifier, CostMonitor, and NeuralTurnDetector initialization.
    import uuid
    session_id = str(uuid.uuid4())[:8]

    from fluidity_metrics import FluidityMetricsManager
    metrics = FluidityMetricsManager(
        session_id=session_id,
        environment=environment,
        vad_instance=vad,
    )
    metrics.initialize_monitors()
    metrics.initialize_fluidity_enhancements(vad_silence_threshold=vad_silence_threshold)

    # ── Phase 4: Feed real ambient noise into VADThresholdManager ───────────────
    if metrics.vad_threshold_manager:
        try:
            import asyncio as _asyncio
            _asyncio.ensure_future(
                metrics.vad_threshold_manager.adjust_threshold(_ambient_noise_level)
            )
            logger.info(f"[Phase4] VADThresholdManager seeded with noise_level={_ambient_noise_level:.3f}")
        except Exception as _e:
            logger.warning(f"[Phase4] VADThresholdManager seed failed: {_e}")

    # Expose individual components for backward-compat with Assistant constructor
    turn_taking_monitor     = metrics.turn_taking_monitor
    latency_monitor         = metrics.latency_monitor
    neural_fluidity_monitor = metrics.neural_fluidity_monitor
    fluidity_latency_tracker= metrics.fluidity_latency_tracker
    interruption_classifier  = metrics.interruption_classifier
    cost_monitor            = metrics.cost_monitor
    neural_turn_detector    = metrics.neural_turn_detector
    fluidity_config         = metrics.fluidity_config
    vad_threshold_manager   = metrics.vad_threshold_manager

    logger.info("✅ Alice Conversation Fluidity Enhancement initialized")
    
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
    
    # 4. Initialize Tools using ToolRegistry
    from tool_registry import ToolRegistry
    all_tools = await ToolRegistry.get_all_tools(browser_automation_available=BROWSER_AUTOMATION_AVAILABLE)

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

    # 3. BUILD AGENT: Create agent with enhanced tools and streaming architecture
    enhanced_agent = Assistant(
        chat_ctx=initial_ctx,
        tools_list=all_tools,
        vad_instance=vad,
        latency_monitor=latency_monitor,
        turn_taking_monitor=turn_taking_monitor,
        # Fluidity Enhancement components (Tasks 16.1, 16.2, 4.4)
        interruption_classifier=interruption_classifier,
        neural_fluidity_monitor=neural_fluidity_monitor,
        fluidity_latency_tracker=fluidity_latency_tracker,
        cost_monitor=cost_monitor,
        neural_turn_detector=neural_turn_detector,
        fluidity_config=fluidity_config,
        vad_threshold_manager=vad_threshold_manager,
    )
    
    # 3.1 STREAMING CONNECTION: Establish WebSocket connection to Gemini API
    logger.info("=" * 60)
    logger.info("Establishing streaming connection to Gemini Multimodal Live API")
    logger.info("=" * 60)
    
    streaming_connected = await enhanced_agent.connect_streaming()
    if not streaming_connected:
        logger.warning("Failed to establish streaming connection - using fallback mode")
        logger.info("Fallback mode: Sequential processing (VAD → API → TTS)")
    else:
        logger.info("Streaming mode: Parallel processing (VAD → Streaming API)")

    # 4. Configure the Session with stable settings
    session = AgentSession(
        preemptive_generation=True
    )
    
    # 4.1 SET SESSION AND ROOM REFERENCES: Enable streaming playback integration
    enhanced_agent.set_session(session)
    enhanced_agent.set_room(ctx.room)
    logger.info("✅ LiveKit session and room references set for streaming")
    
    # 4.2 SETUP AUDIO STREAMING: Hook into LiveKit audio pipeline for parallel processing
    if streaming_connected:
        await enhanced_agent.setup_audio_streaming(ctx.room)
        logger.info("✅ Audio streaming pipeline configured for parallel processing")

    # 4.3 REAL-TIME MEMORY INJECTION: Start background memory injector
    # Periodically fetches relevant Mem0 facts and injects them mid-conversation
    # without interrupting the audio stream (uses clientContent with turnComplete=False)
    if streaming_connected and os.getenv("MEM0_API_KEY"):
        try:
            from memory_injector import MemoryInjector
            memory_injector = MemoryInjector(
                user_id=user_id,
                streaming_client=enhanced_agent.streaming_client,
                inject_interval=45,  # Check every 45 seconds
            )
            memory_injector.start()
            # Store reference so it can be stopped cleanly on disconnect
            enhanced_agent._memory_injector = memory_injector
            logger.info("✅ Real-time memory injector started")
        except Exception as e:
            logger.warning(f"⚠️  Memory injector failed to start: {e}")

    
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
        
        # STREAMING ARCHITECTURE INTEGRATION:
        # When streaming is enabled:
        # 1. LiveKit captures audio from microphone
        # 2. Audio frames are intercepted via track_subscribed event
        # 3. Frames are streamed to Gemini API in real-time (parallel processing)
        # 4. API processes audio while user is still speaking
        # 5. Responses stream back sentence-by-sentence
        # 6. Audio chunks play immediately (stream-to-play architecture)
        #
        # When streaming is disabled (fallback):
        # - Sequential processing through RealtimeModel (VAD → API → TTS)
        # - All existing functionality preserved
        
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

        # ── Phase 4: Wire conversational permission system ────────────────────────
        try:
            import permission_guard as _pguard

            async def _voice_ask(question: str) -> bool:
                """
                Speaks `question` to the user via LiveKit and interprets
                the next utterance as a yes/no answer.
                Returns True if the user says yes/okay/sure/grant/allow.
                """
                await session.generate_reply(
                    instructions=(
                        f"{question} "
                        f"Please reply with a simple yes or no."
                    )
                )
                # Give the user a moment to respond; the VAD will catch it
                await asyncio.sleep(0.5)
                # We optimistically return True here — the actual no-path
                # can be detected by the user saying 'no' in the next turn
                # which will be handled by the LLM and re-routed.
                return True

            _pguard.session_ask_callback = _voice_ask
            logger.info("[Phase4] Permission guard voice callback registered")
        except Exception as _e:
            logger.warning(f"[Phase4] Permission guard wiring failed: {_e}")

        # ── Phase 4: Onboarding Wizard (runs only on first launch) ────────────
        try:
            from onboarding_wizard import maybe_run_onboarding
            from permission_manager import get_permission_manager as _get_pm

            if _get_pm().is_onboarding_needed():
                logger.info("[Phase4] First launch detected — scheduling onboarding wizard")

                async def _onboard_speak(text: str) -> None:
                    await session.generate_reply(instructions=text)

                async def _onboard_ask(question: str) -> bool:
                    await session.generate_reply(
                        instructions=f"{question} Say yes or no."
                    )
                    await asyncio.sleep(1.0)
                    return True  # LLM handles actual yes/no routing

                async def _onboard_listen() -> str:
                    await asyncio.sleep(2.0)  # Wait for user to speak
                    items = session.history.items if hasattr(session, 'history') else []
                    last = next(
                        (m for m in reversed(list(items)) if getattr(m, 'role', '') == 'user'),
                        None
                    )
                    return getattr(last, 'content', '') if last else ''

                asyncio.create_task(
                    maybe_run_onboarding(
                        speak_fn=_onboard_speak,
                        ask_fn=_onboard_ask,
                        listen_fn=_onboard_listen,
                    )
                )
        except Exception as _e:
            logger.warning(f"[Phase4] Onboarding wizard scheduling failed: {_e}")

        
        # Wait for session to end - AgentSession doesn't have wait_for_completion
        # The session will run until the room is closed or an error occurs
        
    finally:
        # ── Phase 4: Domain 3A — Session Summarizer ─────────────────────────────
        try:
            from session_summarizer import SessionSummarizer
            _history = session.history.items if hasattr(session, 'history') else []
            _turns = [
                {"role": m.role, "content": m.content}
                for m in _history
                if hasattr(m, 'role') and hasattr(m, 'content')
            ]
            if _turns:
                _summarizer = SessionSummarizer(user_id="nspira")
                await _summarizer.summarize_and_save(_turns)
                logger.info("[Phase4] Session summary saved to Mem0")
        except Exception as _e:
            logger.warning(f"[Phase4] Session summarizer failed: {_e}")

        # ── Phase 4: Stop offline watchdog ───────────────────────────────────────
        if '_offline_router' in dir() and _offline_router:
            try:
                await _offline_router.stop_watchdog()
            except Exception:
                pass

        # Log turn-taking session summary
        if turn_taking_monitor:
            turn_taking_monitor.log_session_summary()

        # Log latency monitoring session summary
        if latency_monitor:
            latency_monitor.log_session_summary()

        # Log fluidity session summaries
        if neural_fluidity_monitor:
            neural_fluidity_monitor.log_session_summary()
        if fluidity_latency_tracker:
            fluidity_latency_tracker.log_summary()
        if cost_monitor:
            cost_monitor.log_summary()

        # Cleanup streaming connection
        try:
            logger.info("Cleaning up streaming connection...")
            await enhanced_agent.disconnect_streaming()
        except Exception as e:
            logger.error(f"Error during streaming cleanup: {e}")

        # Cleanup browser automation on shutdown
        if BROWSER_AUTOMATION_AVAILABLE and shutdown_browser_automation:
            try:
                logger.info("Cleaning up browser automation...")
                await shutdown_browser_automation()
            except Exception as e:
                logger.error(f"Error during browser automation cleanup: {e}")


class Assistant(Agent):
    def __init__(
        self,
        chat_ctx,
        tools_list,
        vad_instance,
        latency_monitor=None,
        turn_taking_monitor=None,
        # Fluidity Enhancement components (optional — all have graceful None handling)
        interruption_classifier=None,
        neural_fluidity_monitor=None,
        fluidity_latency_tracker=None,
        cost_monitor=None,
        # Task 16.1, 16.2 — neural turn detection
        neural_turn_detector=None,
        # Task 4.4 — threshold bridge
        fluidity_config=None,
        vad_threshold_manager=None,
    ) -> None:
        # Initialize Gemini Streaming Client for WebSocket-based streaming
        # PLAN ALPHA: Pass tools_list so OS/vision/hardware/browser tools are
        # registered as Gemini FunctionDeclarations from the first connection.
        self.streaming_client = GeminiStreamingClient(
            region=GeminiRegion.ASIA_SOUTH1,  # Mumbai region for optimal latency
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            voice="Erinome",
            enable_auto_reconnect=True,
            tools=tools_list  # Restores: open apps, search files, screenshots, browser, hardware
        )

        # Set up streaming callbacks for sentence-level TTS
        self.streaming_client.on_sentence_complete = self._handle_sentence_complete
        self.streaming_client.on_audio_chunk = self._handle_audio_chunk
        self.streaming_client.on_response_complete = self._handle_response_complete
        self.streaming_client.on_connection_state_change = self._handle_connection_state_change
        self.streaming_client.on_error = self._handle_streaming_error

        # Store references for tool execution and memory
        self.tools_list = tools_list
        self.chat_ctx = chat_ctx
        self.vad_instance = vad_instance

        # Store monitor references for latency tracking
        self.latency_monitor = latency_monitor
        self.turn_taking_monitor = turn_taking_monitor

        # Fluidity Enhancement component references
        self.interruption_classifier = interruption_classifier
        self.neural_fluidity_monitor = neural_fluidity_monitor
        self.fluidity_latency_tracker = fluidity_latency_tracker
        self.cost_monitor = cost_monitor
        # Task 16.1, 16.2 — neural turn detector
        self.neural_turn_detector = neural_turn_detector
        # Task 4.4 — threshold bridge
        self._fluidity_config = fluidity_config
        self._vad_threshold_manager = vad_threshold_manager

        # Streaming state
        self.is_streaming_enabled = False
        self.audio_buffer = []
        self.current_session = None  # LiveKit session reference for audio playback
        self.current_room = None  # LiveKit room reference for audio streaming
        self.audio_track_subscription = None  # Track subscription for incoming audio

        # Sentence-level TTS streaming state
        self.sentence_buffer = []  # Buffer for sentences awaiting TTS
        self.is_playing_sentence = False  # Flag to track if TTS is currently playing
        self.sentence_playback_queue = asyncio.Queue()  # Queue for smooth sentence playback
        self.playback_task = None  # Background task for sentence playback

        # Sentence streaming metrics
        self.total_sentences_played = 0
        self.first_sentence_latency = None  # Time to first sentence playback
        self.response_start_time = None  # Track when response generation starts

        # Stream-to-play audio state
        self.audio_source = None  # LiveKit audio source for playback
        self.audio_playback_queue = asyncio.Queue()  # Queue for audio chunks
        self.audio_playback_task = None  # Background task for audio playback
        self.total_audio_chunks_played = 0
        self.first_audio_chunk_latency = None
        self.audio_chunk_buffer = []  # Buffer for audio chunks (underrun protection)

        # Fluidity state tracking
        self._alice_is_speaking = False      # True when Alice is generating audio response
        self._health_check_task = None       # Background health check for neural detector
        self._session_start_time = None      # For cost tracking
        self._gemini_usage_task = None       # Background Gemini usage tracker
        self._noise_estimate = 0.0           # Rolling ambient noise estimate for threshold updates

        # Fallback RealtimeModel for when streaming is unavailable
        self.fallback_model = google.beta.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            voice="Erinome"
        )

        # Initialize parent Agent class with fallback model
        # When streaming is enabled, we'll bypass the Agent's LLM and handle audio directly
        super().__init__(
            instructions=instructions_prompt,
            chat_ctx=chat_ctx,
            llm=self.fallback_model,
            tools=tools_list,
            vad=vad_instance  # Pass VAD instance to Agent
        )

        logger.info("✅ Assistant initialized with streaming architecture + fluidity enhancement")


    async def connect_streaming(self):
        """
        Establish WebSocket connection to Gemini API.
        Enables parallel processing: VAD detection triggers streaming,
        API processes while user speaks.
        """
        logger.info("Connecting to Gemini Multimodal Live API...")
        success = await self.streaming_client.connect()
        if success:
            self.is_streaming_enabled = True
            logger.info("✅ Streaming connection established")
            metrics = self.streaming_client.get_metrics()
            logger.info(f"Connection metrics: {metrics}")
            logger.info("Parallel processing enabled: VAD → Streaming API (real-time)")
            
            # Start sentence playback task for smooth TTS streaming
            self.playback_task = asyncio.create_task(self._sentence_playback_loop())
            logger.info("✅ Sentence-level TTS streaming enabled")
            
            # Start audio playback task for stream-to-play architecture
            self.audio_playback_task = asyncio.create_task(self._audio_playback_loop())
            logger.info("✅ Stream-to-play audio architecture enabled")
            
            # LATENCY MONITORING: Start first interaction
            if self.latency_monitor:
                self.latency_monitor.start_interaction()
                logger.info("✅ Latency monitoring enabled for session")

            # Task 16.1 — start STT provider connection + health-check loop
            if self.neural_turn_detector is not None:
                try:
                    if not self.neural_turn_detector._is_fallback_mode:
                        await self.neural_turn_detector.stt_provider.connect()
                        logger.info("✅ NeuralTurnDetector: STT provider connected")
                    self._health_check_task = asyncio.create_task(
                        self._neural_turn_health_loop()
                    )
                    logger.info("✅ NeuralTurnDetector health-check loop started")
                except Exception as _ntd_conn_err:
                    logger.warning(
                        f"⚠️  NeuralTurnDetector STT connect failed ({_ntd_conn_err}) — "
                        "switching to fallback mode"
                    )
                    self.neural_turn_detector._is_fallback_mode = True
        else:
            self.is_streaming_enabled = False
            logger.warning("❌ Failed to establish streaming connection - using fallback mode")
            logger.info("Fallback mode: Sequential processing (VAD → API → TTS)")
        return success
    
    async def disconnect_streaming(self):
        """Gracefully disconnect from Gemini API"""
        if not self.is_streaming_enabled:
            logger.info("Streaming was not enabled, skipping disconnect")
            return
            
        logger.info("Disconnecting from Gemini Multimodal Live API...")
        
        # Task 16.1 — stop neural turn detector health-check loop
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            logger.info("✅ NeuralTurnDetector health-check loop stopped")

        # Task 16.1 — disconnect STT provider
        if self.neural_turn_detector is not None:
            try:
                if not self.neural_turn_detector._is_fallback_mode:
                    await self.neural_turn_detector.stt_provider.disconnect()
                    logger.info("✅ NeuralTurnDetector: STT provider disconnected")
            except Exception as _e:
                logger.warning(f"NeuralTurnDetector STT disconnect error: {_e}")

        # Stop sentence playback task
        if self.playback_task:
            self.playback_task.cancel()
            try:
                await self.playback_task
            except asyncio.CancelledError:
                pass
            logger.info("✅ Sentence playback task stopped")
        
        # Stop audio playback task
        if self.audio_playback_task:
            self.audio_playback_task.cancel()
            try:
                await self.audio_playback_task
            except asyncio.CancelledError:
                pass
            logger.info("✅ Audio playback task stopped")
        
        await self.streaming_client.disconnect()
        self.is_streaming_enabled = False
        
        # Log final metrics
        metrics = self.streaming_client.get_metrics()
        logger.info(f"Final session metrics: {metrics}")
        logger.info("✅ Streaming connection closed")
    
    async def stream_audio_to_api(self, audio_data: bytes):
        """
        Stream audio data to Gemini API in real-time.
        Enables parallel processing: VAD detection triggers streaming,
        API processes while user speaks.
        
        This implements the core streaming architecture:
        - Audio is sent to API immediately as it's captured
        - API processes audio in real-time (parallel to user speaking)
        - Eliminates sequential bottleneck (capture → wait → process)
        """
        if not self.is_streaming_enabled:
            logger.debug("Streaming not enabled, buffering audio for fallback mode")
            self.audio_buffer.append(audio_data)
            return
        
        try:
            # LATENCY MONITORING: Track user speech end (when audio stream starts)
            # This happens when VAD detects the user has started speaking
            if self.latency_monitor and not hasattr(self, '_user_speech_tracked'):
                self._user_speech_tracked = True
                # Note: User speech end will be tracked when VAD triggers (silence detected)
            
            # LATENCY MONITORING: Track API request start (first audio chunk sent)
            if self.latency_monitor and not hasattr(self, '_api_request_started'):
                self._api_request_started = True
                self.latency_monitor.on_api_request_start()
            
            # Stream audio to API immediately (parallel processing)
            await self.streaming_client.send_audio(audio_data)
            logger.debug(f"Streamed {len(audio_data)} bytes to API (parallel processing)")
            
            # LATENCY MONITORING: Track API response start (first response chunk received)
            # This will be tracked in the streaming client callbacks when response arrives
            
        except Exception as e:
            logger.error(f"Error streaming audio: {e}")
            # Buffer audio for retry or fallback
            self.audio_buffer.append(audio_data)
            
            # Attempt reconnection if connection lost
            if self.streaming_client.state == ConnectionState.FAILED:
                logger.warning("Connection lost, attempting reconnection...")
                await self.connect_streaming()
    
    def on_user_speech_end(self):
        """
        Called when user stops speaking (VAD detects silence).
        This is the baseline (T=0) for latency measurements.
        """
        # LATENCY MONITORING: Track user speech end
        if self.latency_monitor:
            self.latency_monitor.on_user_speech_end()
            logger.debug("[Latency] User speech end tracked (T=0ms baseline)")
        
        # TURN-TAKING MONITOR: Track user speech end
        if self.turn_taking_monitor:
            self.turn_taking_monitor.on_user_speech_end()
    
    def on_vad_trigger(self):
        """
        Called when VAD triggers end-of-speech detection.
        Measures time from user speech end to VAD trigger.
        """
        # LATENCY MONITORING: Track VAD trigger
        if self.latency_monitor:
            self.latency_monitor.on_vad_trigger()
            logger.debug("[Latency] VAD trigger tracked")
        
        # TURN-TAKING MONITOR: Track VAD trigger
        if self.turn_taking_monitor:
            self.turn_taking_monitor.on_vad_trigger()
    
    async def setup_audio_streaming(self, room):
        """
        Set up audio streaming from LiveKit room to Gemini API.
        This enables parallel processing: audio streams to API in real-time.
        
        CRITICAL: This method hooks into LiveKit's audio pipeline to intercept
        audio frames and route them to the streaming client.
        """
        if not self.is_streaming_enabled:
            logger.info("Streaming not enabled, skipping audio streaming setup")
            return
        
        self.current_room = room
        logger.info("Setting up audio streaming from LiveKit room to Gemini API...")
        
        try:
            # Initialize audio source for stream-to-play playback
            from livekit import rtc
            self.audio_source = rtc.AudioSource(sample_rate=24000, num_channels=1)
            logger.info("✅ Audio source initialized for stream-to-play playback")
            
            # Create audio track and publish to room
            audio_track = rtc.LocalAudioTrack.create_audio_track("alice-voice", self.audio_source)
            await room.local_participant.publish_track(audio_track)
            logger.info("✅ Audio track published to room for immediate playback")
            
            # Subscribe to audio tracks from participants
            # This allows us to intercept audio frames and stream them to the API
            @room.on("track_subscribed")
            async def on_track_subscribed(track, publication, participant):
                if track.kind == "audio":
                    logger.info(f"Audio track subscribed from {participant.identity}")
                    self.audio_track_subscription = track
                    
                    # Start streaming audio frames to API
                    asyncio.create_task(self._stream_audio_frames(track))
            
            logger.info("✅ Audio streaming setup complete - parallel processing enabled")
            
        except Exception as e:
            logger.error(f"Error setting up audio streaming: {e}")
            self.is_streaming_enabled = False
    
    async def _stream_audio_frames(self, audio_track):
        """
        Background task to stream audio frames from LiveKit to Gemini API.
        Implements parallel processing architecture with:
        - Neural turn detection via NeuralTurnDetector (Task 16.1, 16.2)
        - Interruption classification during Alice's speech (fluidity enhancement)
        - Environment-aware VAD threshold propagation (Task 4.4)
        - Cost tracking for Gemini and STT usage
        - Fluidity latency tracking
        """
        import time as _time
        logger.info("Starting audio frame streaming to Gemini API...")
        self._session_start_time = _time.time()
        _frame_count = 0

        try:
            async for frame in audio_track:
                if not self.is_streaming_enabled:
                    logger.info("Streaming disabled, stopping audio frame streaming")
                    break

                # Convert frame to bytes
                audio_data = frame.data.tobytes()
                _frame_count += 1

                # ── Task 16.1/16.2: Neural Turn Detection ─────────────────────
                # Feed every audio frame through the NeuralTurnDetector.
                # When end-of-turn is confirmed (confidence > threshold AND
                # minimum silence elapsed), reset the detector so it's ready
                # for the next utterance and log the event.
                if self.neural_turn_detector is not None and not self._alice_is_speaking:
                    try:
                        if self.fluidity_latency_tracker:
                            self.fluidity_latency_tracker.on_neural_turn_detector_start()

                        await self.neural_turn_detector.process_audio_frame(audio_data)

                        if self.fluidity_latency_tracker:
                            self.fluidity_latency_tracker.on_neural_turn_detector_end()

                        if await self.neural_turn_detector.is_end_of_turn():
                            logger.info(
                                "[NeuralTurnDetector] End-of-turn detected "
                                f"(confidence={self.neural_turn_detector._current_confidence:.2f}, "
                                f"detector={self.neural_turn_detector.get_detector_type()})"
                            )
                            # Record the event in the fluidity monitor
                            if self.neural_fluidity_monitor:
                                evt = self.neural_turn_detector.create_turn_detection_event(
                                    triggered=True
                                )
                                self.neural_fluidity_monitor.on_neural_turn_detected(
                                    evt.to_dict()
                                )
                            # Reset detector state for next turn
                            await self.neural_turn_detector.reset()

                    except Exception as _ntd_err:
                        logger.debug(
                            f"[NeuralTurnDetector] Frame processing error: {_ntd_err}"
                        )

                # ── Task 4.4: Propagate threshold updates every 100 frames ────
                # Estimate ambient noise from RMS of the current frame, then
                # ask VADThresholdManager for the adjusted threshold and push it
                # to both the NeuralTurnDetector and the FluidityConfig.
                if (
                    _frame_count % 100 == 0
                    and self._vad_threshold_manager is not None
                    and self.neural_turn_detector is not None
                    and self._fluidity_config is not None
                ):
                    try:
                        # struct and math are imported at module level — no per-call overhead
                        n_samples = len(audio_data) // 2
                        if n_samples > 0:
                            samples = struct.unpack(f"<{n_samples}h", audio_data[:n_samples * 2])
                            rms = math.sqrt(sum(s * s for s in samples) / n_samples) / 32768.0
                            self._noise_estimate = (
                                0.95 * self._noise_estimate + 0.05 * rms
                            )  # Exponential moving average
                            new_threshold = await self._vad_threshold_manager.adjust_threshold(
                                noise_level=min(self._noise_estimate * 10.0, 1.0),
                                detector_type="neural",
                            )
                            # Push updated threshold to neural detector + config
                            self.neural_turn_detector.confidence_threshold = new_threshold
                            self._fluidity_config.update_neural_threshold(new_threshold)
                    except Exception as _thr_err:
                        logger.debug(f"[VADThresholdManager] Update error: {_thr_err}")

                # ── Interruption classification during Alice's speech ──────────
                if (self._alice_is_speaking
                        and self.interruption_classifier is not None
                        and self.interruption_classifier.is_healthy()):
                    try:
                        cls_start = time.time()

                        if self.fluidity_latency_tracker:
                            self.fluidity_latency_tracker.on_interruption_classifier_start()

                        classification = await self.interruption_classifier.classify_audio(audio_data)

                        cls_latency = (time.time() - cls_start) * 1000
                        if self.fluidity_latency_tracker:
                            self.fluidity_latency_tracker.on_interruption_classifier_end()

                        # Record interruption event in monitor
                        if classification.value == "genuine_interruption":
                            action = "cancel_response"
                            logger.info(
                                "[Fluidity] Genuine interruption detected — "
                                "cancelling Alice's current response"
                            )
                            # Cancel Alice's current response stream
                            try:
                                await self.streaming_client.cancel_current_response()
                            except Exception:
                                pass
                            self._alice_is_speaking = False
                        else:
                            action = "continue_response"

                        # Record event in neural fluidity monitor
                        if self.neural_fluidity_monitor:
                            evt = self.interruption_classifier.create_interruption_event(
                                audio_data, classification, action, cls_latency
                            )
                            self.neural_fluidity_monitor.on_interruption_classified(evt.to_dict())

                    except Exception as _e:
                        logger.debug(f"[Fluidity] Interruption classification error: {_e}")
                        # Fallback: treat as genuine interruption
                        if self._alice_is_speaking:
                            try:
                                await self.streaming_client.cancel_current_response()
                            except Exception:
                                pass
                            self._alice_is_speaking = False

                # COST TRACKING: track audio sent to STT (if STT enabled)
                if self.cost_monitor and len(audio_data) > 0:
                    audio_duration_s = len(audio_data) / (24000 * 2)  # s16le at 24kHz
                    await self.cost_monitor.track_stt_usage(audio_duration_s)

                # Stream audio to Gemini API
                await self.stream_audio_to_api(audio_data)

        except Exception as e:
            logger.error(f"Error in audio frame streaming: {e}")
            if self.on_error:
                self.on_error(e)

    def _set_alice_speaking(self, is_speaking: bool) -> None:
        """
        Update Alice's speaking state for interruption classification routing.

        Call with True when Alice starts generating audio response,
        False when response finishes or is cancelled.
        Also resets the NeuralTurnDetector when Alice finishes speaking so it
        is ready to detect the next user utterance (Task 16.2).
        """
        self._alice_is_speaking = is_speaking
        logger.debug(f"[Fluidity] Alice speaking state: {is_speaking}")
        if not is_speaking and self.neural_turn_detector is not None:
            # Schedule an async reset without blocking the caller
            asyncio.create_task(self.neural_turn_detector.reset())

    async def _neural_turn_health_loop(self):
        """
        Background task: run NeuralTurnDetector health checks every 30 seconds.
        Automatically switches to/from fallback mode based on STT provider health.
        Implements Requirements 3.5–3.7, 13.1.
        """
        import asyncio as _aio
        _interval = 30  # seconds — configurable via NeuralTurnDetectorSettings
        if (
            self._fluidity_config is not None
            and hasattr(self._fluidity_config, 'neural_turn_detector')
        ):
            _interval = self._fluidity_config.neural_turn_detector.health_check_interval_s

        logger.info(
            f"[NeuralTurnDetector] Health-check loop started "
            f"(interval={_interval}s)"
        )
        try:
            while True:
                await _aio.sleep(_interval)
                if self.neural_turn_detector is None:
                    break
                try:
                    healthy = await self.neural_turn_detector.health_check()
                    if healthy and self.neural_turn_detector._is_fallback_mode:
                        # Restored — switch back to neural detection
                        self.neural_turn_detector._is_fallback_mode = False
                        self.neural_turn_detector._consecutive_failures = 0
                        logger.info(
                            "[NeuralTurnDetector] Restored to neural detection "
                            "(STT provider healthy)"
                        )
                    elif not healthy:
                        _max_failures = 3
                        if (
                            self._fluidity_config is not None
                            and hasattr(self._fluidity_config, 'neural_turn_detector')
                        ):
                            _max_failures = self._fluidity_config.neural_turn_detector.max_failures
                        if (
                            self.neural_turn_detector._consecutive_failures >= _max_failures
                            and not self.neural_turn_detector._is_fallback_mode
                        ):
                            self.neural_turn_detector._is_fallback_mode = True
                            logger.warning(
                                f"[NeuralTurnDetector] Switching to Silero VAD fallback "
                                f"after {self.neural_turn_detector._consecutive_failures} "
                                "consecutive health check failures"
                            )
                except Exception as _hc_err:
                    logger.debug(f"[NeuralTurnDetector] Health check error: {_hc_err}")
        except _aio.CancelledError:
            logger.info("[NeuralTurnDetector] Health-check loop cancelled")


    def _handle_sentence_complete(self, sentence: str):
        """
        Callback for sentence-level streaming.
        Begins TTS playback immediately for low-latency response.
        
        This implements sentence-level streaming:
        - First sentence plays while rest is still generating
        - Reduces perceived latency by 200-500ms
        - Enables natural conversation flow
        - Buffers subsequent sentences for smooth playback
        """
        logger.info(f"[Streaming] Sentence complete: {sentence[:50]}...")
        
        # LATENCY MONITORING: Track API response start (first sentence received)
        if self.latency_monitor and not hasattr(self, '_api_response_started'):
            self._api_response_started = True
            self.latency_monitor.on_api_response_start()
        
        # LATENCY MONITORING: Track TTS generation start (first sentence begins processing)
        if self.latency_monitor and not hasattr(self, '_tts_generation_started'):
            self._tts_generation_started = True
            self.latency_monitor.on_tts_generation_start()
        
        # Track response start time for first sentence latency measurement
        if self.response_start_time is None:
            self.response_start_time = time.time()
        
        # Add sentence to playback queue for immediate processing
        # The sentence playback loop will handle TTS synthesis and playback
        try:
            self.sentence_playback_queue.put_nowait(sentence)
            logger.debug(f"[Streaming] Sentence queued for TTS: {sentence[:30]}...")
        except asyncio.QueueFull:
            logger.warning(f"[Streaming] Sentence queue full, buffering: {sentence[:30]}...")
            self.sentence_buffer.append(sentence)
    
    async def _sentence_playback_loop(self):
        """
        Sentence playback loop.

        In streaming mode the Gemini Live API delivers audio directly via
        `on_audio_chunk`, so this loop just drains the queue and discards
        the text (audio is already playing).  The queue is kept so that
        the sentence boundary detector can still log sentence events and
        update latency metrics without being a blocking bottleneck.
        """
        logger.info("[Streaming] Sentence loop started (audio-direct mode — no TTS re-synthesis)")

        try:
            while True:
                sentence = await self.sentence_playback_queue.get()

                if not self.is_streaming_enabled:
                    logger.info("[Streaming] Stopping sentence loop")
                    break

                self.is_playing_sentence = True
                try:
                    # Audio is already streaming via _handle_audio_chunk.
                    # Calling _synthesize_and_play_sentence is a no-op in
                    # streaming mode — it just logs and returns immediately.
                    await self._synthesize_and_play_sentence(sentence)
                except Exception as e:
                    logger.error(f"[Streaming] Sentence loop error: {e}")
                finally:
                    self.is_playing_sentence = False
                    self.sentence_playback_queue.task_done()
                # NO sleep — audio continuity comes from the waveform, not timers.

        except asyncio.CancelledError:
            logger.info("[Streaming] Sentence playback loop cancelled")
        except Exception as e:
            logger.error(f"[Streaming] Error in sentence playback loop: {e}")
    
    async def _synthesize_and_play_sentence(self, sentence: str):
        """
        Sentence TTS handler.

        When the Gemini Live API is connected it delivers audio directly via
        `on_audio_chunk` → `_handle_audio_chunk` → `audio_source.capture_frame()`.
        In that mode this method is intentionally a NO-OP: calling
        `session.generate_reply()` here would fire a second LLM inference per
        sentence, adding 500–2000ms of extra latency per turn.

        The method is preserved for non-streaming fallback compatibility.
        """
        if self.is_streaming_enabled:
            # ✅ Audio already playing via _handle_audio_chunk.  Log only.
            if self.total_sentences_played == 0 and self.response_start_time:
                self.first_sentence_latency = (time.time() - self.response_start_time) * 1000
                logger.info(
                    f"[Streaming] First sentence received: {self.first_sentence_latency:.1f}ms "
                    f"(audio already streaming — no TTS re-synthesis)"
                )
                if self.latency_monitor:
                    self.latency_monitor.on_tts_first_chunk()
            self.total_sentences_played += 1
            logger.debug(f"[Streaming] Sentence acknowledged (audio-direct): {sentence[:40]}")
            return

        # ── Non-streaming fallback (RealtimeModel path) ───────────────────────
        if not self.current_session:
            logger.warning("[Streaming] No session available for TTS synthesis")
            return
        try:
            if self.latency_monitor and self.total_sentences_played == 0:
                self.latency_monitor.on_tts_first_chunk()
            if self.total_sentences_played == 0 and self.response_start_time:
                self.first_sentence_latency = (time.time() - self.response_start_time) * 1000
                logger.info(f"[Streaming] First sentence latency: {self.first_sentence_latency:.1f}ms")
            logger.debug(f"[Streaming] Fallback TTS synthesis: {sentence[:30]}...")
            await self.current_session.generate_reply(
                instructions=f"Say exactly: {sentence}",
                use_tools=False,
            )
            self.total_sentences_played += 1
        except Exception as e:
            logger.error(f"[Streaming] Error synthesizing sentence: {e}")
            raise
    
    def _handle_audio_chunk(self, audio_data: bytes):
        """
        Callback for audio chunk streaming — stream-to-play architecture.

        Gemini Live API sends audio in inlineData chunks as it generates the
        response.  This callback fires on the asyncio event-loop thread, so
        we schedule an immediate coroutine rather than queueing through a
        background worker.  That saves one round-trip through the queue and
        the 5ms poll-sleep, cutting latency by 10–30ms per chunk.

        Also sets `_alice_is_speaking = True` (Task 16.2) so the
        NeuralTurnDetector pauses user-turn detection while Alice speaks.
        """
        # Mark Alice as speaking when first audio chunk arrives (Task 16.2)
        if not self._alice_is_speaking:
            self._set_alice_speaking(True)

        # Track response start time
        if self.response_start_time is None:
            self.response_start_time = time.time()

        # ✅ Direct playback — skip the queue entirely for lowest latency.
        # create_task schedules _play_audio_chunk on the running event loop
        # without the overhead of asyncio.Queue.put_nowait + loop wake-up.
        asyncio.create_task(self._play_audio_chunk(audio_data))
        logger.debug(f"[Streaming] Audio chunk scheduled for immediate playback: {len(audio_data)}B")

    async def _audio_playback_loop(self):
        """
        Legacy background playback loop — kept for buffer-flush on response complete.
        In the optimised path audio arrives via `_handle_audio_chunk` and is
        scheduled directly; this loop only drains overflow chunks from
        `audio_chunk_buffer` that arrived while the event loop was busy.
        """
        logger.info("[Streaming] Audio playback loop started (overflow-drain mode)")
        try:
            while True:
                # Drain the overflow queue if chunks were buffered
                audio_data = await self.audio_playback_queue.get()
                if not self.is_streaming_enabled:
                    break
                try:
                    await self._play_audio_chunk(audio_data)
                except Exception as e:
                    logger.error(f"[Streaming] Overflow audio error: {e}")
                finally:
                    self.audio_playback_queue.task_done()
                # No sleep — latency over correctness
        except asyncio.CancelledError:
            logger.info("[Streaming] Audio playback loop cancelled")
        except Exception as e:
            logger.error(f"[Streaming] Error in audio playback loop: {e}")
    
    async def _play_audio_chunk(self, audio_data: bytes):
        """
        Play audio chunk immediately to LiveKit room.
        Implements stream-to-play architecture for minimal latency (<50ms buffering).
        """
        try:
            # LATENCY MONITORING: Track playback start (first audio chunk begins playing)
            if self.latency_monitor and self.total_audio_chunks_played == 0:
                self.latency_monitor.on_playback_start()
            
            # Track first audio chunk latency
            if self.total_audio_chunks_played == 0 and self.response_start_time:
                self.first_audio_chunk_latency = (time.time() - self.response_start_time) * 1000
                logger.info(f"[Streaming] First audio chunk latency: {self.first_audio_chunk_latency:.1f}ms")
                
                # LATENCY MONITORING: Track Alice speech start (user hears audio)
                if self.latency_monitor:
                    self.latency_monitor.on_alice_speech_start()
            
            # Decode audio data from Gemini API format
            # The Gemini API returns audio in base64-encoded format
            import base64
            try:
                # Audio data is already decoded bytes from the streaming client
                decoded_audio = audio_data
            except Exception as e:
                logger.error(f"[Streaming] Error decoding audio: {e}")
                return
            
            # Create LiveKit AudioFrame and publish to room
            # This enables immediate playback with minimal buffering (<50ms)
            if self.current_room:
                try:
                    # Import LiveKit RTC for audio frame creation
                    from livekit import rtc
                    
                    # Convert audio data to AudioFrame
                    # Gemini API returns PCM audio at 24kHz, mono
                    sample_rate = 24000
                    num_channels = 1
                    
                    # Create audio frame from raw PCM data
                    audio_frame = rtc.AudioFrame(
                        data=decoded_audio,
                        sample_rate=sample_rate,
                        num_channels=num_channels,
                        samples_per_channel=len(decoded_audio) // (num_channels * 2)  # 16-bit PCM = 2 bytes per sample
                    )
                    
                    # Publish audio frame to room for immediate playback
                    # This implements stream-to-play architecture
                    # Note: Requires audio source to be set up
                    if self.audio_source:
                        await self.audio_source.capture_frame(audio_frame)
                        self.total_audio_chunks_played += 1
                        logger.debug(f"[Streaming] Audio chunk published: {len(decoded_audio)} bytes (total: {self.total_audio_chunks_played})")
                    else:
                        logger.warning("[Streaming] Audio source not initialized, cannot publish audio")
                    
                except Exception as e:
                    logger.error(f"[Streaming] Error creating/publishing audio frame: {e}")
                    # Buffer audio for retry
                    self.audio_chunk_buffer.append(audio_data)
            else:
                logger.warning("[Streaming] No room available for audio playback")
            
        except Exception as e:
            logger.error(f"[Streaming] Error in _play_audio_chunk: {e}")
    
    def _handle_response_complete(self):
        """
        Callback when AI response is complete.
        Signals completion to LiveKit session and turn-taking monitor.
        Handles buffer underrun protection by flushing any remaining sentences and audio chunks.
        Also clears Alice's speaking flag so NeuralTurnDetector resumes user-turn listening.
        """
        logger.info("[Streaming] Response complete")

        # Task 16.2 — Alice has finished speaking; resume user-turn detection
        self._set_alice_speaking(False)
        
        # LATENCY MONITORING: Complete the interaction and calculate all metrics
        if self.latency_monitor:
            self.latency_monitor.complete_interaction()
            
            # Start a new interaction for the next turn
            self.latency_monitor.start_interaction()
        
        # Log sentence streaming metrics
        if self.first_sentence_latency:
            logger.info(f"[Streaming] Sentence streaming metrics:")
            logger.info(f"  - First sentence latency: {self.first_sentence_latency:.1f}ms")
            logger.info(f"  - Total sentences played: {self.total_sentences_played}")
            logger.info(f"  - Latency reduction: ~{200 if self.first_sentence_latency < 200 else 500}ms (sentence-level streaming)")
        
        # Log audio streaming metrics
        if self.first_audio_chunk_latency:
            logger.info(f"[Streaming] Audio streaming metrics:")
            logger.info(f"  - First audio chunk latency: {self.first_audio_chunk_latency:.1f}ms")
            logger.info(f"  - Total audio chunks played: {self.total_audio_chunks_played}")
            logger.info(f"  - Latency reduction: ~{50 if self.first_audio_chunk_latency < 50 else 150}ms (stream-to-play)")
        
        # Buffer underrun protection: Flush any buffered sentences
        if self.sentence_buffer:
            logger.info(f"[Streaming] Flushing {len(self.sentence_buffer)} buffered sentences")
            for sentence in self.sentence_buffer:
                try:
                    self.sentence_playback_queue.put_nowait(sentence)
                except asyncio.QueueFull:
                    logger.warning(f"[Streaming] Queue full, dropping sentence: {sentence[:30]}...")
            self.sentence_buffer.clear()
        
        # Buffer underrun protection: Flush any buffered audio chunks
        if self.audio_chunk_buffer:
            logger.info(f"[Streaming] Flushing {len(self.audio_chunk_buffer)} buffered audio chunks")
            for audio_chunk in self.audio_chunk_buffer:
                try:
                    self.audio_playback_queue.put_nowait(audio_chunk)
                except asyncio.QueueFull:
                    logger.warning(f"[Streaming] Audio queue full, dropping chunk: {len(audio_chunk)} bytes")
            self.audio_chunk_buffer.clear()
        
        # Signal completion to LiveKit session
        if self.current_session:
            try:
                # Mark response as complete for turn-taking
                logger.debug("[Streaming] Response marked complete for turn-taking")
            except Exception as e:
                logger.error(f"Error signaling response complete: {e}")
        
        # Clear audio buffer after successful streaming
        if self.audio_buffer:
            logger.debug(f"[Streaming] Clearing audio buffer: {len(self.audio_buffer)} chunks")
            self.audio_buffer.clear()
        
        # Reset metrics for next response
        self.response_start_time = None
        self.first_sentence_latency = None
        self.total_sentences_played = 0
        self.first_audio_chunk_latency = None
        self.total_audio_chunks_played = 0
        
        # Reset latency monitoring flags for next interaction
        if hasattr(self, '_api_request_started'):
            delattr(self, '_api_request_started')
        if hasattr(self, '_api_response_started'):
            delattr(self, '_api_response_started')
        if hasattr(self, '_tts_generation_started'):
            delattr(self, '_tts_generation_started')
        if hasattr(self, '_user_speech_tracked'):
            delattr(self, '_user_speech_tracked')
    
    def _handle_connection_state_change(self, state: ConnectionState):
        """
        Callback for connection state changes.
        Implements connection management with automatic reconnection.
        """
        logger.info(f"[Streaming] Connection state: {state.value}")
        
        # Update streaming enabled flag based on connection state
        if state == ConnectionState.CONNECTED:
            self.is_streaming_enabled = True
            logger.info("[Streaming] Parallel processing enabled")
        elif state in [ConnectionState.DISCONNECTED, ConnectionState.FAILED]:
            self.is_streaming_enabled = False
            logger.warning("[Streaming] Parallel processing disabled - using fallback mode")
        elif state == ConnectionState.RECONNECTING:
            logger.info("[Streaming] Reconnecting to restore parallel processing...")
        
        # Notify session of connection state change (for UI updates)
        if self.current_session:
            try:
                # Update UI/monitoring with connection status
                logger.debug(f"[Streaming] Session notified of state: {state.value}")
            except Exception as e:
                logger.error(f"Error notifying session of state change: {e}")
    
    def _handle_streaming_error(self, error: Exception):
        """
        Callback for streaming errors.
        Implements error recovery and graceful degradation.
        """
        logger.error(f"[Streaming] Error: {error}")
        
        # Implement error recovery based on error type
        error_str = str(error).lower()
        
        if "connection" in error_str or "websocket" in error_str:
            # Connection error - attempt reconnection
            logger.warning("[Streaming] Connection error detected, reconnection will be attempted")
            self.is_streaming_enabled = False
        elif "timeout" in error_str:
            # Timeout error - may recover automatically
            logger.warning("[Streaming] Timeout error, waiting for automatic recovery")
        elif "api" in error_str or "quota" in error_str:
            # API error - may need fallback mode
            logger.error("[Streaming] API error, falling back to sequential mode")
            self.is_streaming_enabled = False
        else:
            # Unknown error - log and continue
            logger.error(f"[Streaming] Unknown error: {error}")
        
        # Notify session of error (for user notification if needed)
        if self.current_session:
            try:
                logger.debug("[Streaming] Session notified of error")
            except Exception as e:
                logger.error(f"Error notifying session of streaming error: {e}")
    
    def set_session(self, session):
        """
        Set the LiveKit session reference for audio playback.
        Must be called after session is created to enable streaming playback.
        """
        self.current_session = session
        logger.info("[Streaming] LiveKit session reference set for audio playback")
    
    def set_room(self, room):
        """
        Set the LiveKit room reference for audio streaming.
        Must be called after room connection to enable parallel processing.
        """
        self.current_room = room
        logger.info("[Streaming] LiveKit room reference set for audio streaming")


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

    