import logging
import uuid
import sys

logger = logging.getLogger(__name__)

class FluidityMetricsManager:
    """
    Centralized manager for ALICE's conversation fluidity metrics,
    cost tracking, latency monitoring, and VAD (Voice Activity Detection) tuning.
    """
    def __init__(self, session_id=None, environment="quiet", vad_instance=None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.environment = environment
        self.vad_instance = vad_instance
        
        self.turn_taking_monitor = None
        self.latency_monitor = None
        self.neural_fluidity_monitor = None
        self.fluidity_latency_tracker = None
        
        self.fluidity_config = None
        self.interruption_classifier = None
        self.cost_monitor = None
        self.vad_threshold_manager = None
        self.neural_turn_detector = None
        
        self.is_fluidity_available = False

    def initialize_monitors(self):
        """Initializes basic metrics trackers."""
        logger.info("=" * 60)
        logger.info(f"Initializing Metrics Monitors for session: {self.session_id}")
        logger.info("=" * 60)

        # Import locally to avoid circular dependencies
        from vad_turn_taking_monitor import get_turn_taking_monitor, get_neural_fluidity_monitor
        from latency_monitor import get_latency_monitor, get_fluidity_latency_tracker
        
        self.turn_taking_monitor = get_turn_taking_monitor(session_id=self.session_id)
        self.latency_monitor = get_latency_monitor(session_id=self.session_id)
        self.neural_fluidity_monitor = get_neural_fluidity_monitor(session_id=self.session_id)
        self.fluidity_latency_tracker = get_fluidity_latency_tracker(session_id=self.session_id)
        
        logger.info("✅ Core monitors initialized")

    def initialize_fluidity_enhancements(self, vad_silence_threshold=0.5):
        """Initializes advanced neural detection, interruption classification, and cost tracking."""
        try:
            from fluidity_config import get_fluidity_config
            from vad_config import VADThresholdManager
            from interruption_classifier import InterruptionClassifier
            from cost_monitor import get_cost_monitor
            from turn_detection import NeuralTurnDetector
            from stt.config_factory import STTConfigFactory
            self.is_fluidity_available = True
        except ImportError as e:
            logger.warning(f"⚠️  Fluidity Enhancement modules not available: {e}")
            return

        logger.info("=" * 60)
        logger.info("Initializing Alice Conversation Fluidity Enhancement")
        logger.info("=" * 60)

        self.fluidity_config = get_fluidity_config()

        # Initialize VAD Threshold Manager
        self.vad_threshold_manager = VADThresholdManager(
            min_threshold=0.3,
            max_threshold=0.6,
            default_threshold=vad_silence_threshold,
        )
        logger.info("✅ VADThresholdManager initialized")

        # Initialize Interruption Classifier
        try:
            self.interruption_classifier = InterruptionClassifier(
                min_interruption_duration_ms=(
                    self.fluidity_config.interruption_classifier.min_interruption_duration_ms
                    if self.fluidity_config else 200
                ),
                speech_energy_threshold=(
                    self.fluidity_config.interruption_classifier.speech_energy_threshold
                    if self.fluidity_config else 0.02
                ),
                classification_timeout_ms=(
                    self.fluidity_config.interruption_classifier.classification_timeout_ms
                    if self.fluidity_config else 100
                ),
                fallback_enabled=True,
                conversation_id=self.session_id,
            )
        except Exception as exc:
            logger.warning(f"⚠️  InterruptionClassifier init error: {exc} — using fallback")
            self.interruption_classifier = InterruptionClassifier(
                fallback_enabled=True,
                conversation_id=self.session_id,
            )
            
        if self.interruption_classifier and self.interruption_classifier.is_healthy():
            logger.info("✅ InterruptionClassifier initialized")

        # Initialize Cost Monitor
        if get_cost_monitor:
            self.cost_monitor = get_cost_monitor(conversation_id=self.session_id)
            logger.info("✅ CostMonitor initialized")

        # Initialize NeuralTurnDetector
        if self.fluidity_config:
            _ntd_cfg = self.fluidity_config.neural_turn_detector
            _stt_provider = None
            if self.fluidity_config.stt.enabled and STTConfigFactory:
                try:
                    _stt_provider = STTConfigFactory.create_from_env()
                    logger.info(f"✅ STT provider created: {self.fluidity_config.stt.provider_type}")
                except Exception as _stt_err:
                    logger.warning(f"⚠️  STT provider creation failed ({_stt_err})")

            if _stt_provider:
                try:
                    self.neural_turn_detector = NeuralTurnDetector(
                        stt_provider=_stt_provider,
                        confidence_threshold=_ntd_cfg.confidence_threshold,
                        min_turn_silence_ms=_ntd_cfg.min_turn_silence_ms,
                        max_turn_silence_ms=_ntd_cfg.max_turn_silence_ms,
                        fallback_vad=self.vad_instance,
                    )
                    logger.info("✅ NeuralTurnDetector initialized with STT")
                except Exception as _ntd_err:
                    logger.warning(f"⚠️  NeuralTurnDetector init failed ({_ntd_err})")
            else:
                try:
                    from tests.mock_stt_provider import MockSTTProvider
                    self.neural_turn_detector = NeuralTurnDetector(
                        stt_provider=MockSTTProvider(),
                        confidence_threshold=_ntd_cfg.confidence_threshold,
                        min_turn_silence_ms=_ntd_cfg.min_turn_silence_ms,
                        max_turn_silence_ms=_ntd_cfg.max_turn_silence_ms,
                        fallback_vad=self.vad_instance,
                    )
                    self.neural_turn_detector._is_fallback_mode = True
                    logger.info("ℹ️  NeuralTurnDetector: No STT API keys — running in Silero VAD fallback mode")
                except Exception:
                    pass

        # Seed neural threshold from VADThresholdManager
        if self.neural_turn_detector and self.vad_threshold_manager and self.fluidity_config:
            _initial_neural_threshold = self.vad_threshold_manager.get_current_threshold_sync()
            self.fluidity_config.update_neural_threshold(_initial_neural_threshold)
            self.neural_turn_detector.confidence_threshold = _initial_neural_threshold
            logger.info(f"✅ VADThresholdManager → NeuralTurnDetector: threshold {_initial_neural_threshold:.3f}")
