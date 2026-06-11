"""
Gemini Multimodal Live API WebSocket Streaming Client

This module implements a WebSocket-based streaming client for the Gemini Multimodal Live API,
enabling real-time bidirectional audio streaming with sentence-level response processing.

Key Features:
- WebSocket connection to Gemini Multimodal Live API
- Bidirectional audio streaming (send user audio, receive AI audio)
- Sentence-level response streaming with boundary detection
- Connection management (reconnection, error handling, graceful degradation)
- Regional routing optimization (asia-south1 Mumbai primary, with fallbacks)
- Comprehensive logging for debugging and monitoring

Performance Targets:
- Network latency: <100ms (via regional routing)
- Sentence-level streaming: First sentence playback within 200ms
- Connection resilience: Automatic reconnection with exponential backoff
"""

import asyncio
import base64
import json
import logging
import os
import time
from typing import Optional, Callable, Dict, Any, List
from enum import Enum

try:
    import websockets
    from websockets.asyncio.client import ClientConnection
    from websockets.exceptions import WebSocketException
except ImportError:
    raise ImportError(
        "websockets package is required for Gemini streaming client. "
        "Install with: pip install websockets"
    )

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """WebSocket connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class GeminiRegion(Enum):
    """Gemini API regional endpoints for latency optimization.

    NOTE: The Gemini Multimodal Live API (BidiGenerateContent) only supports
    API-key authentication via the global generativelanguage.googleapis.com
    endpoint.  Regional Vertex AI endpoints require OAuth2 / service-account
    auth and a different URL scheme.  All values below map to the same global
    endpoint when using an API key.
    """
    ASIA_SOUTH1 = "asia-south1"  # kept for config compat
    ASIA_SOUTHEAST1 = "asia-southeast1"
    US_CENTRAL1 = "us-central1"
    GLOBAL = "global"


class SentenceBoundaryDetector:
    """
    Detects sentence boundaries in streaming text for sentence-level TTS.
    
    Uses punctuation-based heuristics to identify complete sentences that can
    be sent to TTS immediately, reducing perceived latency.
    """
    
    SENTENCE_TERMINATORS = {'.', '!', '?', '。', '！', '？'}  # Including Hindi/multilingual
    BUFFER_SIZE = 5  # Minimum characters before considering sentence complete
    
    def __init__(self):
        self.buffer = ""
        self.completed_sentences: List[str] = []
    
    def add_text(self, text: str) -> List[str]:
        """
        Add streaming text and return any completed sentences.
        
        Args:
            text: New text chunk from streaming response
            
        Returns:
            List of completed sentences ready for TTS
        """
        self.buffer += text
        sentences = []
        
        # Look for sentence terminators
        for terminator in self.SENTENCE_TERMINATORS:
            if terminator in self.buffer:
                parts = self.buffer.split(terminator)
                # All parts except the last are complete sentences
                for i in range(len(parts) - 1):
                    sentence = parts[i].strip() + terminator
                    if len(sentence) >= self.BUFFER_SIZE:
                        sentences.append(sentence)
                        self.completed_sentences.append(sentence)
                # Keep the last part as buffer
                self.buffer = parts[-1]
                break
        
        return sentences
    
    def flush(self) -> Optional[str]:
        """
        Flush remaining buffer as final sentence.
        
        Returns:
            Remaining text if any, None otherwise
        """
        if self.buffer.strip():
            final = self.buffer.strip()
            self.buffer = ""
            return final
        return None
    
    def reset(self):
        """Reset detector state for new response"""
        self.buffer = ""
        self.completed_sentences.clear()


class GeminiStreamingClient:
    """
    WebSocket streaming client for Gemini Multimodal Live API.
    
    Handles bidirectional audio streaming with sentence-level response processing,
    automatic reconnection, and regional routing optimization.
    
    Usage:
        client = GeminiStreamingClient(api_key="your-api-key")
        await client.connect()
        
        # Send audio
        await client.send_audio(audio_data)
        
        # Receive responses via callbacks
        client.on_sentence_complete = lambda sentence: print(f"Sentence: {sentence}")
        client.on_audio_chunk = lambda audio: play_audio(audio)
        
        await client.disconnect()
    """
    
    # API Configuration
    API_VERSION = "v1alpha"
    MODEL_NAME = "gemini-2.5-flash-native-audio-preview-12-2025"
    VOICE_NAME = "Erinome"
    
    # Connection Configuration
    MAX_RECONNECT_ATTEMPTS = 5
    RECONNECT_BASE_DELAY = 1.0   # seconds
    RECONNECT_MAX_DELAY = 30.0   # seconds
    CONNECTION_TIMEOUT = 10.0    # seconds
    PING_INTERVAL = 20.0         # seconds (keep-alive)
    PING_TIMEOUT = 8.0           # seconds

    # Gemini Live API audio format
    # Input: 16-bit PCM at 16 kHz (mono) — what Gemini Live API expects
    # Output: 16-bit PCM at 24 kHz (mono) — what Gemini Live API returns
    AUDIO_INPUT_SAMPLE_RATE = 16000
    AUDIO_INPUT_MIME = "audio/pcm;rate=16000"
    AUDIO_OUTPUT_SAMPLE_RATE = 24000
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        region: GeminiRegion = GeminiRegion.ASIA_SOUTH1,
        model: str = MODEL_NAME,
        voice: str = VOICE_NAME,
        enable_auto_reconnect: bool = True,
        tools: Optional[List] = None
    ):
        """
        Initialize Gemini streaming client.
        
        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            region: Primary region for API routing (default: asia-south1 Mumbai)
            model: Gemini model name
            voice: Voice name for TTS
            enable_auto_reconnect: Enable automatic reconnection on failure
            tools: List of LiveKit FunctionTool or callable tools to register with Gemini.
                   These restore ALICE's OS, vision, browser and hardware capabilities.
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Provide via api_key parameter or GOOGLE_API_KEY env var"
            )
        
        self.region = region
        self.model = model
        self.voice = voice
        self.enable_auto_reconnect = enable_auto_reconnect
        
        # ── PLAN ALPHA FIX #1: Store tools for schema injection ──────────────
        # All LiveKit @function_tool decorated functions are stored here.
        # They will be translated to Gemini FunctionDeclarations and injected
        # into the WebSocket setup message so the model can call them.
        self.tools: List = tools or []
        # Map of tool_name -> callable for fast dispatch during functionCall events
        self._tool_dispatch: dict = {}
        if self.tools:
            import inspect
            for tool in self.tools:
                func = getattr(tool, "_func", tool)
                name = getattr(getattr(tool, "info", None), "name", None) \
                    or getattr(tool, "name", None) \
                    or func.__name__
                self._tool_dispatch[name] = func
            logger.info(
                f"[PLAN ALPHA] Registered {len(self._tool_dispatch)} tools with streaming client: "
                f"{list(self._tool_dispatch.keys())}"
            )
        
        # Connection state
        self.state = ConnectionState.DISCONNECTED
        self.ws: Optional[ClientConnection] = None
        self.reconnect_attempts = 0
        self.last_error: Optional[Exception] = None
        
        # Sentence boundary detection
        self.sentence_detector = SentenceBoundaryDetector()
        
        # Callbacks
        self.on_sentence_complete: Optional[Callable[[str], None]] = None
        self.on_audio_chunk: Optional[Callable[[bytes], None]] = None
        self.on_response_complete: Optional[Callable[[], None]] = None
        self.on_connection_state_change: Optional[Callable[[ConnectionState], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
        # Background tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        
        # Metrics
        self.connection_start_time: Optional[float] = None
        self.total_audio_sent = 0
        self.total_audio_received = 0
        self.total_sentences_received = 0
        
        logger.info(
            f"Initialized GeminiStreamingClient: region={region.value}, "
            f"model={model}, voice={voice}"
        )
    
    def _get_websocket_url(self, region: GeminiRegion) -> str:
        """
        Construct WebSocket URL for the Gemini Multimodal Live API.

        The Live API (BidiGenerateContent) uses a dedicated WebSocket path
        that is different from the REST streaming endpoint
        (:streamGenerateContent).  API-key authentication is only supported
        on the global generativelanguage.googleapis.com host; regional
        Vertex AI hosts require OAuth2.

        Args:
            region: Ignored — kept for API compatibility.  API-key auth
                    always routes to the global endpoint.

        Returns:
            WebSocket URL for Gemini Multimodal Live API (BidiGenerateContent)
        """
        # ✅ Correct Live API endpoint (BidiGenerateContent)
        return (
            "wss://generativelanguage.googleapis.com/ws/"
            "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
            f"?key={self.api_key}"
        )
    
    def _set_state(self, new_state: ConnectionState):
        """Update connection state and trigger callback"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            logger.info(f"Connection state: {old_state.value} -> {new_state.value}")
            
            if self.on_connection_state_change:
                try:
                    self.on_connection_state_change(new_state)
                except Exception as e:
                    logger.error(f"Error in connection state callback: {e}", exc_info=True)
    
    async def connect(self, region: Optional[GeminiRegion] = None) -> bool:
        """
        Establish WebSocket connection to Gemini API.
        
        Args:
            region: Override default region (optional)
            
        Returns:
            True if connection successful, False otherwise
        """
        target_region = region or self.region
        
        try:
            self._set_state(ConnectionState.CONNECTING)
            ws_url = self._get_websocket_url(target_region)
            
            logger.info(f"Connecting to Gemini API: region={target_region.value}")
            self.connection_start_time = time.time()
            
            # Establish WebSocket connection
            self.ws = await asyncio.wait_for(
                websockets.connect(
                    ws_url,
                    max_size=50 * 1024 * 1024,  # 50MB max message size for audio
                    ping_interval=self.PING_INTERVAL,
                    ping_timeout=self.PING_TIMEOUT,
                ),
                timeout=self.CONNECTION_TIMEOUT
            )
            
            connection_time = (time.time() - self.connection_start_time) * 1000
            logger.info(
                f"Connected to Gemini API: region={target_region.value}, "
                f"latency={connection_time:.1f}ms"
            )
            
            # Send initial configuration
            await self._send_config()
            
            self._set_state(ConnectionState.CONNECTED)
            self.reconnect_attempts = 0
            
            # Start background tasks
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"Connection timeout to region {target_region.value}")
            self.last_error = TimeoutError(f"Connection timeout: {target_region.value}")
            await self._handle_connection_failure(target_region)
            return False
            
        except WebSocketException as e:
            logger.error(f"WebSocket error connecting to {target_region.value}: {e}")
            self.last_error = e
            await self._handle_connection_failure(target_region)
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error connecting to {target_region.value}: {e}", exc_info=True)
            self.last_error = e
            await self._handle_connection_failure(target_region)
            return False
    
    async def _send_config(self):
        """Send BidiGenerateContent setup message to Gemini Live API.
        
        PLAN ALPHA FIX #2 & #3:
        - Translates all registered Python tools into Gemini FunctionDeclarations
        - Injects them into the setup payload so Gemini knows it can call them
        - Adds a system_instruction reminding Gemini to USE the tools actively
        """
        # The model name MUST be prefixed with "models/" for the Live API.
        model_name = self.model if self.model.startswith("models/") else f"models/{self.model}"
        config = {
            "setup": {
                "model": model_name,
                "generation_config": {
                    # AUDIO only — requesting TEXT causes the server to also
                    # run a text generation pass, adding ~100ms of extra latency.
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {
                                "voice_name": self.voice
                            }
                        }
                    }
                }
            }
        }

        # ── PLAN ALPHA FIX #2: Tool Schema Injection ─────────────────────────
        # If tools are registered, translate them to Gemini FunctionDeclarations
        # and inject into the setup payload. This is what enables ALICE to open
        # apps, control hardware, capture screenshots etc. via voice commands.
        if self._tool_dispatch:
            declarations = self._build_function_declarations()
            config["setup"]["tools"] = [{"function_declarations": declarations}]
            
            # ── PLAN ALPHA FIX #3: System Instruction ────────────────────────
            # Tell Gemini it MUST use tools rather than just describing actions.
            # Without this, even with tools registered, Gemini may respond with
            # "I'll open Chrome for you" instead of actually calling open_application.
            config["setup"]["system_instruction"] = {
                "parts": [{
                    "text": (
                        "You are ALICE, an advanced AI assistant and operating system agent "
                        "running on the user's Windows PC. You have DIRECT access to tools "
                        "that let you control the computer in real time.\n\n"
                        "CRITICAL RULE: When a user asks you to DO something (open an app, "
                        "search files, take a screenshot, browse the web, control hardware), "
                        "you MUST call the appropriate tool immediately. NEVER just describe "
                        "how to do it — actually DO it using your tools.\n\n"
                        "Your available capabilities:\n"
                        "- Open any application on the PC (Chrome, Notepad, Spotify, etc.)\n"
                        "- Search and manage files on the hard drive\n"
                        "- Take screenshots and see what's on screen\n"
                        "- Browse the web using the browser automation tool\n"
                        "- Adjust system settings (brightness, volume, etc.)\n"
                        "- Control physical hardware (servo motors, ultrasonic sensors)\n"
                        "- Run advanced OS operations\n\n"
                        "Always be proactive: execute first, then verbally confirm what you did."
                    )
                }]
            }
            logger.info(
                f"[PLAN ALPHA] Injected {len(declarations)} function declarations into setup"
            )

        await self._send_message(config)
        logger.debug("Sent BidiGenerateContent setup to Gemini Live API")

    def _build_function_declarations(self) -> list:
        """
        PLAN ALPHA FIX #2: Translate Python tools to Gemini FunctionDeclaration schema.
        
        Iterates over all registered tools, extracts name/description/parameter
        signatures using Python's inspect module, and converts Python types to
        the JSON Schema types required by the Gemini Live API.
        
        Python type -> Gemini schema type mapping:
            str   -> STRING
            int   -> INTEGER
            bool  -> BOOLEAN  
            float -> NUMBER
            other -> STRING  (safe fallback)
        """
        import inspect
        declarations = []
        
        for tool in self.tools:
            try:
                func = getattr(tool, "_func", tool)
                
                # Extract name: prefer LiveKit FunctionToolInfo, then attribute, then __name__
                tool_info = getattr(tool, "info", None)
                name = (getattr(tool_info, "name", None)
                        or getattr(tool, "name", None)
                        or func.__name__)
                
                # Extract description: prefer LiveKit info.description, then docstring
                desc = (getattr(tool_info, "description", None)
                        or inspect.getdoc(func)
                        or f"Execute the {name} action")
                
                # Parse parameter signature
                sig = inspect.signature(func)
                properties = {}
                required = []
                
                for param_name, param in sig.parameters.items():
                    # Skip self (instance methods) and ctx (LiveKit context injection)
                    if param_name in ("self", "ctx"):
                        continue
                    
                    # Map Python annotation to Gemini JSON Schema type
                    annotation = param.annotation
                    if annotation == int:
                        param_type = "INTEGER"
                    elif annotation == bool:
                        param_type = "BOOLEAN"
                    elif annotation == float:
                        param_type = "NUMBER"
                    else:
                        param_type = "STRING"  # Safe fallback for str, Any, etc.
                    
                    # Extract per-parameter description from docstring if available
                    param_desc = f"The {param_name} value"
                    
                    properties[param_name] = {
                        "type": param_type,
                        "description": param_desc
                    }
                    
                    # Parameters with no default are required
                    if param.default is inspect.Parameter.empty:
                        required.append(param_name)
                
                decl: dict = {
                    "name": name,
                    "description": desc.strip()
                }
                if properties:
                    decl["parameters"] = {
                        "type": "OBJECT",
                        "properties": properties
                    }
                    if required:
                        decl["parameters"]["required"] = required
                
                declarations.append(decl)
                logger.debug(f"[PLAN ALPHA] Registered tool declaration: {name}")
                
            except Exception as e:
                logger.warning(
                    f"[PLAN ALPHA] Failed to build declaration for tool {tool}: {e}"
                )
                continue
        
        return declarations

    async def _execute_tool_and_respond(self, function_call: dict):
        """
        PLAN ALPHA FIX #4: Execute a tool called by Gemini and send the result back.
        
        When Gemini decides to call a tool (e.g. open_application), it sends a
        functionCall event. This method:
          1. Extracts the tool name and arguments from the event
          2. Looks up the Python callable in self._tool_dispatch
          3. Executes it (supports both sync and async functions)
          4. Formats the return value into a Gemini functionResponse message
          5. Sends it back over the WebSocket so Gemini can continue the conversation
        """
        import inspect
        
        name = function_call.get("name", "")
        args = function_call.get("args", {})
        
        logger.info(f"[PLAN ALPHA] Gemini requested tool: '{name}' with args: {args}")
        
        result_payload: dict
        
        target_func = self._tool_dispatch.get(name)
        if target_func is None:
            logger.error(f"[PLAN ALPHA] Tool '{name}' not found in dispatch table. "
                         f"Available: {list(self._tool_dispatch.keys())}")
            result_payload = {"error": f"Tool '{name}' is not registered"}
        else:
            try:
                if inspect.iscoroutinefunction(target_func):
                    result = await target_func(**args)
                else:
                    # Run sync tools in the event loop's executor to avoid blocking audio
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, lambda: target_func(**args)
                    )
                
                result_str = str(result) if result is not None else "Done"
                result_payload = {"output": result_str}
                logger.info(
                    f"[PLAN ALPHA] Tool '{name}' executed successfully. "
                    f"Result: {result_str[:150]}"
                )
                
            except Exception as e:
                logger.error(
                    f"[PLAN ALPHA] Tool '{name}' raised an exception: {e}",
                    exc_info=True
                )
                result_payload = {"error": str(e)}
        
        # Send the functionResponse back to Gemini so it can formulate a voice reply
        response_msg = {
            "tool_response": {
                "function_responses": [
                    {
                        "name": name,
                        "response": result_payload
                    }
                ]
            }
        }
        
        try:
            await self._send_message(response_msg)
            logger.debug(f"[PLAN ALPHA] Sent functionResponse for '{name}'")
        except Exception as e:
            logger.error(
                f"[PLAN ALPHA] Failed to send functionResponse for '{name}': {e}"
            )
    
    async def _handle_connection_failure(self, failed_region: GeminiRegion):
        """
        Handle connection failure with fallback and reconnection logic.
        
        Args:
            failed_region: Region that failed to connect
        """
        self._set_state(ConnectionState.FAILED)
        
        if self.on_error and self.last_error:
            try:
                self.on_error(self.last_error)
            except Exception as e:
                logger.error(f"Error in error callback: {e}", exc_info=True)
        
        # Try fallback regions
        fallback_regions = self._get_fallback_regions(failed_region)
        
        for fallback in fallback_regions:
            logger.info(f"Attempting fallback to region: {fallback.value}")
            if await self.connect(region=fallback):
                logger.info(f"Successfully connected to fallback region: {fallback.value}")
                return
        
        # All regions failed, attempt reconnection if enabled
        if self.enable_auto_reconnect and self.reconnect_attempts < self.MAX_RECONNECT_ATTEMPTS:
            await self._reconnect()
        else:
            logger.error("All connection attempts failed")
            self._set_state(ConnectionState.FAILED)
    
    def _get_fallback_regions(self, failed_region: GeminiRegion) -> List[GeminiRegion]:
        """
        Get ordered list of fallback regions.
        
        Args:
            failed_region: Region that failed
            
        Returns:
            List of fallback regions to try
        """
        all_regions = [
            GeminiRegion.ASIA_SOUTH1,
            GeminiRegion.ASIA_SOUTHEAST1,
            GeminiRegion.US_CENTRAL1,
            GeminiRegion.GLOBAL
        ]
        
        # Remove failed region and return remaining
        return [r for r in all_regions if r != failed_region]
    
    async def _reconnect(self):
        """Attempt reconnection with exponential backoff"""
        self.reconnect_attempts += 1
        self._set_state(ConnectionState.RECONNECTING)
        
        # Calculate backoff delay
        delay = min(
            self.RECONNECT_BASE_DELAY * (2 ** (self.reconnect_attempts - 1)),
            self.RECONNECT_MAX_DELAY
        )
        
        logger.info(
            f"Reconnection attempt {self.reconnect_attempts}/{self.MAX_RECONNECT_ATTEMPTS} "
            f"in {delay:.1f}s"
        )
        
        await asyncio.sleep(delay)
        await self.connect()
    
    async def _send_message(self, message: Dict[str, Any]):
        """
        Send JSON message to WebSocket.
        
        Args:
            message: Message dictionary to send
        """
        if not self.ws or self.state != ConnectionState.CONNECTED:
            raise RuntimeError("WebSocket not connected")
        
        try:
            await self.ws.send(json.dumps(message))
        except WebSocketException as e:
            logger.error(f"Error sending message: {e}")
            raise
    
    async def send_audio(
        self,
        audio_data: bytes,
        mime_type: str = AUDIO_INPUT_MIME,  # type: ignore[assignment]
    ):
        """
        Send audio data to the Gemini Live API.

        The Live API expects base64-encoded PCM inside a JSON envelope.
        MIME type MUST include the sample rate (e.g. ``audio/pcm;rate=16000``).

        Args:
            audio_data: Raw 16-bit LE PCM bytes at 16 kHz mono.
            mime_type:  MIME type string (default: audio/pcm;rate=16000).
        """
        if not self.ws or self.state != ConnectionState.CONNECTED:
            logger.warning("Cannot send audio: not connected")
            return

        try:
            # base64 is imported at module level — no per-call import overhead
            audio_b64 = base64.b64encode(audio_data).decode("ascii")

            message = {
                "realtime_input": {
                    "media_chunks": [
                        {
                            "mime_type": mime_type,
                            "data": audio_b64,
                        }
                    ]
                }
            }

            await self._send_message(message)
            self.total_audio_sent += len(audio_data)
            logger.debug(f"Sent audio: {len(audio_data)}B ({mime_type})")

        except Exception as e:
            logger.error(f"Error sending audio: {e}", exc_info=True)
            if self.on_error:
                self.on_error(e)
    
    async def _receive_loop(self):
        """Background task to receive and process WebSocket messages"""
        try:
            async for message in self.ws:
                await self._handle_message(message)
                
        except WebSocketException as e:
            logger.error(f"WebSocket error in receive loop: {e}")
            if self.enable_auto_reconnect:
                await self._reconnect()
            else:
                self._set_state(ConnectionState.FAILED)
                
        except Exception as e:
            logger.error(f"Unexpected error in receive loop: {e}", exc_info=True)
            if self.on_error:
                self.on_error(e)
    
    async def _handle_message(self, message: str):
        """
        Process received WebSocket message.
        
        Args:
            message: JSON message from Gemini API
        """
        try:
            data = json.loads(message)
            
            # Handle text response (for sentence-level streaming)
            if "serverContent" in data:
                content = data["serverContent"]
                
                if "modelTurn" in content:
                    model_turn = content["modelTurn"]
                    
                    # Process text parts for sentence detection
                    if "parts" in model_turn:
                        for part in model_turn["parts"]:
                            
                            # ── PLAN ALPHA FIX #4: functionCall Event Handler ───
                            # When Gemini wants to execute an OS/hardware/vision
                            # tool, it sends a functionCall part. We dispatch it
                            # asynchronously so audio streaming is not blocked.
                            if "functionCall" in part:
                                fc = part["functionCall"]
                                logger.info(
                                    f"[PLAN ALPHA] functionCall received: {fc.get('name')}"
                                )
                                asyncio.create_task(
                                    self._execute_tool_and_respond(fc)
                                )
                                # Do NOT process further parts in this iteration —
                                # the tool response will trigger the next turn.
                                continue
                            
                            if "text" in part:
                                text = part["text"]
                                sentences = self.sentence_detector.add_text(text)
                                
                                # Trigger callback for each completed sentence
                                for sentence in sentences:
                                    self.total_sentences_received += 1
                                    logger.debug(f"Sentence complete: {sentence[:50]}...")
                                    
                                    if self.on_sentence_complete:
                                        try:
                                            self.on_sentence_complete(sentence)
                                        except Exception as e:
                                            logger.error(f"Error in sentence callback: {e}", exc_info=True)
                            
                            # Process audio parts
                            if "inlineData" in part:
                                inline_data = part["inlineData"]
                                if "data" in inline_data:
                                    # Decode base64 audio
                                    audio_data = base64.b64decode(inline_data["data"])
                                    self.total_audio_received += len(audio_data)
                                    
                                    logger.debug(f"Received audio chunk: {len(audio_data)} bytes")
                                    
                                    if self.on_audio_chunk:
                                        try:
                                            self.on_audio_chunk(audio_data)
                                        except Exception as e:
                                            logger.error(f"Error in audio callback: {e}", exc_info=True)
                
                # Handle turn complete
                if "turnComplete" in content and content["turnComplete"]:
                    # Flush any remaining text
                    final_sentence = self.sentence_detector.flush()
                    if final_sentence and self.on_sentence_complete:
                        try:
                            self.on_sentence_complete(final_sentence)
                        except Exception as e:
                            logger.error(f"Error in final sentence callback: {e}", exc_info=True)
                    
                    # Reset detector for next turn
                    self.sentence_detector.reset()
                    
                    logger.debug("Response complete")
                    if self.on_response_complete:
                        try:
                            self.on_response_complete()
                        except Exception as e:
                            logger.error(f"Error in response complete callback: {e}", exc_info=True)
            
            # Handle errors
            if "error" in data:
                error = data["error"]
                logger.error(f"API error: {error}")
                if self.on_error:
                    self.on_error(Exception(f"API error: {error}"))
                    
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
    
    async def cancel_current_response(self) -> None:
        """
        Signal the server to stop generating the current response.
        Sends a client_content message with turn_complete=True which
        causes the Live API to interrupt its current output.
        """
        if not self.ws or self.state != ConnectionState.CONNECTED:
            return
        try:
            await self._send_message({"client_content": {"turn_complete": True}})
            logger.debug("[GeminiStreamingClient] Sent cancel signal to server")
        except Exception as e:
            logger.warning(f"[GeminiStreamingClient] Cancel error: {e}")

    async def disconnect(self):
        """Gracefully disconnect from Gemini API"""
        logger.info("Disconnecting from Gemini API")
        
        # Cancel background tasks
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        # Close WebSocket
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        
        self._set_state(ConnectionState.DISCONNECTED)
        
        # Log metrics
        if self.connection_start_time:
            duration = time.time() - self.connection_start_time
            logger.info(
                f"Session metrics: duration={duration:.1f}s, "
                f"audio_sent={self.total_audio_sent} bytes, "
                f"audio_received={self.total_audio_received} bytes, "
                f"sentences={self.total_sentences_received}"
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current client metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "state": self.state.value,
            "region": self.region.value,
            "reconnect_attempts": self.reconnect_attempts,
            "total_audio_sent": self.total_audio_sent,
            "total_audio_received": self.total_audio_received,
            "total_sentences_received": self.total_sentences_received,
            "connection_duration": (
                time.time() - self.connection_start_time
                if self.connection_start_time else 0
            ),
            "last_error": str(self.last_error) if self.last_error else None
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()


# Example usage
async def example_usage():
    """Example demonstrating GeminiStreamingClient usage"""
    
    # Initialize client with Mumbai region for optimal latency
    client = GeminiStreamingClient(
        region=GeminiRegion.ASIA_SOUTH1,
        enable_auto_reconnect=True
    )
    
    # Set up callbacks
    def on_sentence(sentence: str):
        print(f"Sentence: {sentence}")
        # Send to TTS immediately for low-latency playback
    
    def on_audio(audio_data: bytes):
        print(f"Audio chunk: {len(audio_data)} bytes")
        # Play audio immediately (stream-to-play)
    
    def on_state_change(state: ConnectionState):
        print(f"Connection state: {state.value}")
    
    client.on_sentence_complete = on_sentence
    client.on_audio_chunk = on_audio
    client.on_connection_state_change = on_state_change
    
    # Connect
    if await client.connect():
        print("Connected successfully!")
        
        # Send audio (example)
        # audio_data = capture_audio()
        # await client.send_audio(audio_data)
        
        # Keep connection alive
        await asyncio.sleep(60)
        
        # Disconnect
        await client.disconnect()
        
        # Print metrics
        print("Metrics:", client.get_metrics())
    else:
        print("Connection failed")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run example
    asyncio.run(example_usage())
