"""
Mock STT Provider for Testing Alice's Conversation Fluidity Enhancement.

This module provides a fully configurable in-memory mock of the STTProvider
interface. It is intended exclusively for use in automated tests — it never
makes real network calls and returns pre-configured TranscriptionResult objects
that are injected via an asyncio queue.

Design goals
------------
* Drop-in replacement for AssemblyAI / Deepgram providers in unit tests.
* Configurable failure modes: connection errors, dropped connections, slow
  transcriptions, and empty result streams.
* Thread-safe call tracking so tests can assert exact call sequences.
* Rich assertion helpers that produce readable failure messages.

Usage example
-------------
    async def test_turn_detected():
        provider = MockSTTProvider()

        # Pre-load a transcription result
        result = make_transcription_result("Hello world", end_of_utterance=True)
        await provider.inject_result(result)

        await provider.connect()
        await provider.stream_audio(b"\\x00" * 480)
        got = await provider.get_transcription_result()

        provider.assert_connected()
        provider.assert_audio_streamed(1)
        assert got.end_of_utterance

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.7, 2.8
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence
from unittest.mock import MagicMock

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graceful import of real project models.
# Falls back to a minimal inline dataclass when the project path is not on
# sys.path (e.g., when running tests from an isolated environment).
# ---------------------------------------------------------------------------
try:
    # Prefer the canonical fluidity_models (richer: provider_type, audio_duration_ms, etc.)
    from fluidity_models import TranscriptionResult  # type: ignore
    _USING_FLUIDITY_MODELS = True
    logger.debug("mock_stt_provider: using TranscriptionResult from fluidity_models")
except ImportError:
    try:
        # Second choice: the leaner stt.models.TranscriptionResult
        from stt.models import TranscriptionResult  # type: ignore
        _USING_FLUIDITY_MODELS = False
        logger.debug("mock_stt_provider: using TranscriptionResult from stt.models")
    except ImportError:
        # Final fallback: define a minimal compatible dataclass inline.
        logger.warning(
            "mock_stt_provider: neither fluidity_models nor stt.models available; "
            "using inline TranscriptionResult fallback."
        )
        _USING_FLUIDITY_MODELS = False

        @dataclass  # type: ignore[no-redef]
        class TranscriptionResult:  # noqa: F811
            """
            Minimal fallback TranscriptionResult dataclass.

            Matches the common denominator of fluidity_models.TranscriptionResult
            and stt.models.TranscriptionResult so mock tests work without any
            project imports.
            """

            text: str
            confidence: float
            end_of_utterance: bool
            is_final: bool
            timestamp_ms: int
            acoustic_features: Dict[str, Any] = field(default_factory=dict)
            linguistic_features: Dict[str, Any] = field(default_factory=dict)
            provider_type: str = "mock"
            audio_duration_ms: int = 0

            def to_dict(self) -> Dict[str, Any]:
                """Serialize to plain dict."""
                return {
                    "text": self.text,
                    "confidence": self.confidence,
                    "end_of_utterance": self.end_of_utterance,
                    "is_final": self.is_final,
                    "timestamp_ms": self.timestamp_ms,
                    "acoustic_features": self.acoustic_features,
                    "linguistic_features": self.linguistic_features,
                    "provider_type": self.provider_type,
                    "audio_duration_ms": self.audio_duration_ms,
                }


# ---------------------------------------------------------------------------
# Connection behaviour enum
# ---------------------------------------------------------------------------

class ConnectionBehaviour:
    """
    Named constants that control how MockSTTProvider reacts to connect().

    Attributes
    ----------
    SUCCESS        Normal successful connection.
    FAIL_ALWAYS    connect() always raises ConnectionError.
    FAIL_THEN_OK   connect() fails for the first N calls, then succeeds.
    DROP_AFTER_N   Connection succeeds but drops silently after N stream_audio
                   calls.  Subsequent stream_audio / get_transcription_result
                   calls raise ConnectionError.
    """

    SUCCESS = "success"
    FAIL_ALWAYS = "fail_always"
    FAIL_THEN_OK = "fail_then_ok"
    DROP_AFTER_N = "drop_after_n"


# ---------------------------------------------------------------------------
# Helper factory
# ---------------------------------------------------------------------------

def make_transcription_result(
    text: str = "",
    confidence: float = 0.95,
    end_of_utterance: bool = False,
    is_final: bool = True,
    acoustic_features: Optional[Dict[str, Any]] = None,
    linguistic_features: Optional[Dict[str, Any]] = None,
    provider_type: str = "mock",
    audio_duration_ms: int = 200,
) -> TranscriptionResult:
    """
    Convenience factory for building TranscriptionResult objects in tests.

    Chooses the correct constructor signature depending on which
    TranscriptionResult class was successfully imported.

    Parameters
    ----------
    text               Transcribed speech text.
    confidence         STT confidence score [0.0, 1.0].
    end_of_utterance   True when the STT provider signals end-of-utterance.
    is_final           True for final (non-partial) results.
    acoustic_features  Dict with keys: pitch_trend, energy_trend, speech_rate.
    linguistic_features Dict with keys: sentence_complete, has_discourse_marker,
                       question_detected.
    provider_type      Provider label embedded in the result.
    audio_duration_ms  Duration (ms) of audio that produced this result.

    Returns
    -------
    TranscriptionResult
        A fully populated instance ready for injection into MockSTTProvider.
    """
    acoustic = acoustic_features or {
        "pitch_trend": "falling",
        "energy_trend": "falling",
        "speech_rate": 120.0,
    }
    linguistic = linguistic_features or {
        "sentence_complete": True,
        "has_discourse_marker": False,
        "question_detected": False,
    }
    timestamp_ms = int(time.time() * 1000)

    # fluidity_models.TranscriptionResult has a richer signature
    if _USING_FLUIDITY_MODELS:
        try:
            return TranscriptionResult(  # type: ignore[call-arg]
                text=text,
                confidence=confidence,
                end_of_utterance=end_of_utterance,
                is_final=is_final,
                timestamp_ms=timestamp_ms,
                acoustic_features=acoustic,
                linguistic_features=linguistic,
                provider_type=provider_type,
                audio_duration_ms=audio_duration_ms,
            )
        except TypeError:
            pass  # Fall through to the simpler constructor below

    return TranscriptionResult(
        text=text,
        confidence=confidence,
        end_of_utterance=end_of_utterance,
        is_final=is_final,
        timestamp_ms=timestamp_ms,
        acoustic_features=acoustic,
        linguistic_features=linguistic,
    )


# ---------------------------------------------------------------------------
# MockSTTProvider
# ---------------------------------------------------------------------------

class MockSTTProvider:
    """
    In-memory mock STT provider implementing the STTProvider interface.

    The mock records every call made to it, enables injection of
    TranscriptionResult objects via an asyncio queue, and exposes assertion
    helpers for clean test code.

    Thread-safety
    -------------
    Call counts are tracked with plain ``int`` attributes. Each awaitable
    method is safe to call from a single asyncio event loop (the standard
    test scenario). If parallel coroutines drive the mock, wrap the shared
    attributes with an asyncio.Lock.

    Parameters
    ----------
    connection_behaviour
        One of the :class:`ConnectionBehaviour` constants.
    fail_count
        For FAIL_THEN_OK: how many connect() calls fail before success.
    drop_after_n_frames
        For DROP_AFTER_N: stream_audio drops after this many frames.
    connect_delay_s
        Simulated async delay inside connect().
    stream_delay_s
        Simulated async delay inside stream_audio().
    transcription_delay_s
        Simulated async delay inside get_transcription_result().
    disconnect_delay_s
        Simulated async delay inside disconnect().
    provider_type
        String label embedded in TranscriptionResult objects returned by
        the mock when no queue results are available and
        ``return_none_when_empty`` is False.
    return_none_when_empty
        If True, get_transcription_result() returns None when the queue is
        empty (realistic behaviour).  If False, it returns a default result.
    """

    def __init__(
        self,
        *,
        connection_behaviour: str = ConnectionBehaviour.SUCCESS,
        fail_count: int = 1,
        drop_after_n_frames: int = 10,
        connect_delay_s: float = 0.0,
        stream_delay_s: float = 0.0,
        transcription_delay_s: float = 0.0,
        disconnect_delay_s: float = 0.0,
        provider_type: str = "mock",
        return_none_when_empty: bool = True,
    ) -> None:
        # Configuration -------------------------------------------------------
        self._connection_behaviour = connection_behaviour
        self._fail_count = fail_count
        self._drop_after_n_frames = drop_after_n_frames
        self._connect_delay_s = connect_delay_s
        self._stream_delay_s = stream_delay_s
        self._transcription_delay_s = transcription_delay_s
        self._disconnect_delay_s = disconnect_delay_s
        self._provider_type = provider_type
        self._return_none_when_empty = return_none_when_empty

        # Internal state ------------------------------------------------------
        self._connected: bool = False
        self._connect_fail_attempts: int = 0   # For FAIL_THEN_OK
        self._frames_streamed: int = 0         # For DROP_AFTER_N gate

        # Call tracking -------------------------------------------------------
        self.connect_call_count: int = 0
        self.disconnect_call_count: int = 0
        self.stream_audio_call_count: int = 0
        self.get_result_call_count: int = 0
        self.is_connected_call_count: int = 0

        # Audio capture -------------------------------------------------------
        self._audio_frames: List[bytes] = []

        # Transcription queue -------------------------------------------------
        self._result_queue: asyncio.Queue = asyncio.Queue()

        # Optional side-effect callbacks (called with the relevant argument) --
        self.on_stream_audio: Optional[Callable[[bytes], None]] = None
        self.on_get_result: Optional[Callable[[], None]] = None

        logger.debug(
            "MockSTTProvider created (behaviour=%s, provider_type=%s)",
            connection_behaviour,
            provider_type,
        )

    # ------------------------------------------------------------------
    # STTProvider interface implementation
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """
        Simulate establishing a connection to the STT provider.

        Raises
        ------
        ConnectionError
            For FAIL_ALWAYS behaviour, or during the failing phase of
            FAIL_THEN_OK.
        """
        self.connect_call_count += 1
        if self._connect_delay_s > 0:
            await asyncio.sleep(self._connect_delay_s)

        behaviour = self._connection_behaviour

        if behaviour == ConnectionBehaviour.FAIL_ALWAYS:
            logger.debug("MockSTTProvider.connect() → ConnectionError (FAIL_ALWAYS)")
            raise ConnectionError("MockSTTProvider: configured to always fail")

        if behaviour == ConnectionBehaviour.FAIL_THEN_OK:
            if self._connect_fail_attempts < self._fail_count:
                self._connect_fail_attempts += 1
                logger.debug(
                    "MockSTTProvider.connect() → ConnectionError (FAIL_THEN_OK, "
                    "attempt %d/%d)",
                    self._connect_fail_attempts,
                    self._fail_count,
                )
                raise ConnectionError(
                    f"MockSTTProvider: simulated failure "
                    f"({self._connect_fail_attempts}/{self._fail_count})"
                )

        # Success path
        self._connected = True
        self._frames_streamed = 0
        logger.debug("MockSTTProvider.connect() → connected")

    async def stream_audio(self, audio_frame: bytes) -> None:
        """
        Record an audio frame and optionally simulate a connection drop.

        Parameters
        ----------
        audio_frame
            Raw PCM bytes from the audio pipeline.

        Raises
        ------
        ConnectionError
            If not connected, or if DROP_AFTER_N limit has been reached.
        """
        self.stream_audio_call_count += 1

        if not self._connected:
            raise ConnectionError(
                "MockSTTProvider.stream_audio() called while not connected"
            )

        self._frames_streamed += 1

        # Simulate connection drop for DROP_AFTER_N behaviour
        if (
            self._connection_behaviour == ConnectionBehaviour.DROP_AFTER_N
            and self._frames_streamed > self._drop_after_n_frames
        ):
            self._connected = False
            logger.debug(
                "MockSTTProvider: connection dropped after %d frames",
                self._drop_after_n_frames,
            )
            raise ConnectionError(
                f"MockSTTProvider: simulated connection drop after "
                f"{self._drop_after_n_frames} frames"
            )

        if self._stream_delay_s > 0:
            await asyncio.sleep(self._stream_delay_s)

        self._audio_frames.append(audio_frame)

        if self.on_stream_audio is not None:
            self.on_stream_audio(audio_frame)

        logger.debug(
            "MockSTTProvider.stream_audio() → frame %d (%d bytes)",
            len(self._audio_frames),
            len(audio_frame),
        )

    async def get_transcription_result(self) -> Optional[TranscriptionResult]:
        """
        Return the next pre-loaded TranscriptionResult from the queue.

        Returns
        -------
        TranscriptionResult or None
            The next result from the injection queue, None if the queue is
            empty and ``return_none_when_empty`` is True, or a default result
            otherwise.

        Raises
        ------
        ConnectionError
            If not connected when the call is made.
        """
        self.get_result_call_count += 1

        if not self._connected:
            raise ConnectionError(
                "MockSTTProvider.get_transcription_result() called while not connected"
            )

        if self._transcription_delay_s > 0:
            await asyncio.sleep(self._transcription_delay_s)

        if self.on_get_result is not None:
            self.on_get_result()

        try:
            result: TranscriptionResult = self._result_queue.get_nowait()
            logger.debug(
                "MockSTTProvider.get_transcription_result() → %r (queue size now %d)",
                result.text,
                self._result_queue.qsize(),
            )
            return result
        except asyncio.QueueEmpty:
            if self._return_none_when_empty:
                logger.debug("MockSTTProvider.get_transcription_result() → None (queue empty)")
                return None
            # Return a silent placeholder result
            return make_transcription_result(
                text="",
                confidence=0.0,
                end_of_utterance=False,
                is_final=False,
                provider_type=self._provider_type,
            )

    async def disconnect(self) -> None:
        """
        Simulate disconnecting from the STT provider.

        Idempotent: calling disconnect() on an already-disconnected provider
        is a no-op (no exception is raised).
        """
        self.disconnect_call_count += 1
        if self._disconnect_delay_s > 0:
            await asyncio.sleep(self._disconnect_delay_s)

        was_connected = self._connected
        self._connected = False
        logger.debug(
            "MockSTTProvider.disconnect() → was_connected=%s", was_connected
        )

    async def is_connected(self) -> bool:
        """
        Return the current connection state.

        Returns
        -------
        bool
            True if connected, False otherwise.
        """
        self.is_connected_call_count += 1
        return self._connected

    # ------------------------------------------------------------------
    # Injection helpers
    # ------------------------------------------------------------------

    async def inject_result(self, result: TranscriptionResult) -> None:
        """
        Place a TranscriptionResult into the queue to be returned by
        get_transcription_result().

        Parameters
        ----------
        result
            The TranscriptionResult to enqueue.
        """
        await self._result_queue.put(result)
        logger.debug(
            "MockSTTProvider: injected result %r (queue size now %d)",
            result.text,
            self._result_queue.qsize(),
        )

    def inject_result_sync(self, result: TranscriptionResult) -> None:
        """
        Synchronous variant of inject_result for use in non-async setup code.

        Parameters
        ----------
        result
            The TranscriptionResult to enqueue.
        """
        self._result_queue.put_nowait(result)
        logger.debug(
            "MockSTTProvider: (sync) injected result %r", result.text
        )

    async def inject_results(self, results: Sequence[TranscriptionResult]) -> None:
        """
        Enqueue multiple TranscriptionResult objects at once.

        Parameters
        ----------
        results
            Iterable of TranscriptionResult objects to enqueue in order.
        """
        for r in results:
            await self._result_queue.put(r)
        logger.debug(
            "MockSTTProvider: injected %d results (queue size now %d)",
            len(results),  # type: ignore[arg-type]
            self._result_queue.qsize(),
        )

    def clear_queue(self) -> None:
        """Drain all pending results from the queue."""
        drained = 0
        while not self._result_queue.empty():
            try:
                self._result_queue.get_nowait()
                drained += 1
            except asyncio.QueueEmpty:
                break
        logger.debug("MockSTTProvider: cleared %d results from queue", drained)

    def reset(self) -> None:
        """
        Reset all call counters, audio frames, and connection state.

        Useful between test cases when reusing the same mock instance.
        """
        self._connected = False
        self._connect_fail_attempts = 0
        self._frames_streamed = 0

        self.connect_call_count = 0
        self.disconnect_call_count = 0
        self.stream_audio_call_count = 0
        self.get_result_call_count = 0
        self.is_connected_call_count = 0

        self._audio_frames.clear()
        self.clear_queue()
        logger.debug("MockSTTProvider: reset complete")

    # ------------------------------------------------------------------
    # Assertion helpers
    # ------------------------------------------------------------------

    def assert_connected(self, msg: str = "") -> None:
        """
        Assert that the provider is currently in a connected state.

        Parameters
        ----------
        msg
            Optional extra context appended to the assertion failure message.

        Raises
        ------
        AssertionError
            If the provider is not connected.
        """
        suffix = f" — {msg}" if msg else ""
        assert self._connected, (
            f"MockSTTProvider: expected to be connected but is disconnected{suffix}"
        )

    def assert_not_connected(self, msg: str = "") -> None:
        """
        Assert that the provider is currently disconnected.

        Raises
        ------
        AssertionError
            If the provider is connected.
        """
        suffix = f" — {msg}" if msg else ""
        assert not self._connected, (
            f"MockSTTProvider: expected to be disconnected but is connected{suffix}"
        )

    def assert_audio_streamed(self, n_frames: int, msg: str = "") -> None:
        """
        Assert that exactly *n_frames* audio frames were streamed.

        Parameters
        ----------
        n_frames
            Expected number of audio frames (i.e. calls to stream_audio()).
        msg
            Optional extra context for failure messages.

        Raises
        ------
        AssertionError
            If the actual streamed frame count does not match.
        """
        actual = len(self._audio_frames)
        suffix = f" — {msg}" if msg else ""
        assert actual == n_frames, (
            f"MockSTTProvider: expected {n_frames} audio frame(s) streamed, "
            f"got {actual}{suffix}"
        )

    def assert_connect_called(self, times: int = 1, msg: str = "") -> None:
        """
        Assert that connect() was called a specific number of times.

        Parameters
        ----------
        times
            Expected call count.
        """
        suffix = f" — {msg}" if msg else ""
        assert self.connect_call_count == times, (
            f"MockSTTProvider: expected connect() to be called {times} time(s), "
            f"got {self.connect_call_count}{suffix}"
        )

    def assert_disconnect_called(self, times: int = 1, msg: str = "") -> None:
        """
        Assert that disconnect() was called a specific number of times.

        Parameters
        ----------
        times
            Expected call count.
        """
        suffix = f" — {msg}" if msg else ""
        assert self.disconnect_call_count == times, (
            f"MockSTTProvider: expected disconnect() to be called {times} time(s), "
            f"got {self.disconnect_call_count}{suffix}"
        )

    def assert_get_result_called(self, times: int, msg: str = "") -> None:
        """
        Assert that get_transcription_result() was called a specific number of times.
        """
        suffix = f" — {msg}" if msg else ""
        assert self.get_result_call_count == times, (
            f"MockSTTProvider: expected get_transcription_result() to be called "
            f"{times} time(s), got {self.get_result_call_count}{suffix}"
        )

    def assert_min_audio_streamed(self, min_frames: int, msg: str = "") -> None:
        """
        Assert that at least *min_frames* audio frames were streamed.

        Useful when the exact frame count is non-deterministic.
        """
        actual = len(self._audio_frames)
        suffix = f" — {msg}" if msg else ""
        assert actual >= min_frames, (
            f"MockSTTProvider: expected at least {min_frames} audio frame(s) "
            f"streamed, got {actual}{suffix}"
        )

    def assert_total_audio_bytes(self, expected_bytes: int, msg: str = "") -> None:
        """
        Assert the total number of raw PCM bytes streamed across all frames.
        """
        actual = sum(len(f) for f in self._audio_frames)
        suffix = f" — {msg}" if msg else ""
        assert actual == expected_bytes, (
            f"MockSTTProvider: expected {expected_bytes} total audio bytes, "
            f"got {actual}{suffix}"
        )

    # ------------------------------------------------------------------
    # Inspection helpers
    # ------------------------------------------------------------------

    def get_audio_frames(self) -> List[bytes]:
        """
        Return a copy of all audio frames that have been streamed.

        Returns
        -------
        List[bytes]
            Ordered list of raw PCM byte chunks, one entry per stream_audio()
            call that completed without error.
        """
        return list(self._audio_frames)

    def get_total_audio_bytes(self) -> int:
        """Return the total number of raw PCM bytes received across all frames."""
        return sum(len(f) for f in self._audio_frames)

    def queue_size(self) -> int:
        """Return the number of TranscriptionResult objects waiting in the queue."""
        return self._result_queue.qsize()

    def summary(self) -> Dict[str, Any]:
        """
        Return a human-readable summary dict of the current mock state.

        Useful for debugging test failures.

        Returns
        -------
        Dict[str, Any]
            Snapshot of call counts, connection state, and queue size.
        """
        return {
            "connected": self._connected,
            "connect_calls": self.connect_call_count,
            "disconnect_calls": self.disconnect_call_count,
            "stream_audio_calls": self.stream_audio_call_count,
            "get_result_calls": self.get_result_call_count,
            "is_connected_calls": self.is_connected_call_count,
            "audio_frames_captured": len(self._audio_frames),
            "total_audio_bytes": self.get_total_audio_bytes(),
            "pending_results_in_queue": self.queue_size(),
            "behaviour": self._connection_behaviour,
            "provider_type": self._provider_type,
        }

    def __repr__(self) -> str:
        return (
            f"MockSTTProvider("
            f"behaviour={self._connection_behaviour!r}, "
            f"connected={self._connected}, "
            f"frames={len(self._audio_frames)}, "
            f"queue_size={self.queue_size()})"
        )


# ---------------------------------------------------------------------------
# pytest fixture
# ---------------------------------------------------------------------------
try:
    import pytest  # noqa: F401

    @pytest.fixture
    def mock_stt_provider() -> MockSTTProvider:
        """
        Pytest fixture that yields a fresh MockSTTProvider for each test.

        Usage
        -----
        .. code-block:: python

            async def test_something(mock_stt_provider):
                await mock_stt_provider.connect()
                ...
        """
        return MockSTTProvider()

    @pytest.fixture
    def mock_stt_provider_always_fail() -> MockSTTProvider:
        """Pytest fixture: provider that always fails to connect."""
        return MockSTTProvider(connection_behaviour=ConnectionBehaviour.FAIL_ALWAYS)

    @pytest.fixture
    def mock_stt_provider_drop_after_5() -> MockSTTProvider:
        """Pytest fixture: provider that drops connection after 5 audio frames."""
        return MockSTTProvider(
            connection_behaviour=ConnectionBehaviour.DROP_AFTER_N,
            drop_after_n_frames=5,
        )

except ImportError:
    pass  # pytest not installed; fixtures silently unavailable


# ---------------------------------------------------------------------------
# Standalone smoke-test / demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    async def _demo() -> None:
        print("=== MockSTTProvider Demo ===\n")

        provider = MockSTTProvider(provider_type="mock")

        # Inject two results
        provider.inject_result_sync(
            make_transcription_result("Hey Alice", end_of_utterance=False)
        )
        provider.inject_result_sync(
            make_transcription_result(
                "What's the weather?",
                end_of_utterance=True,
                confidence=0.98,
            )
        )

        await provider.connect()
        print(f"Connected: {await provider.is_connected()}")

        # Stream three 20 ms audio frames (480 bytes each at 24 kHz / 16-bit)
        for _ in range(3):
            await provider.stream_audio(b"\x00" * 480)

        r1 = await provider.get_transcription_result()
        r2 = await provider.get_transcription_result()
        r3 = await provider.get_transcription_result()  # Should be None

        print(f"Result 1: {r1.text!r} (EOU={r1.end_of_utterance})")
        print(f"Result 2: {r2.text!r} (EOU={r2.end_of_utterance})")
        print(f"Result 3 (empty queue): {r3}")

        await provider.disconnect()

        print("\n--- Assertions ---")
        provider.assert_not_connected()
        provider.assert_audio_streamed(3)
        provider.assert_connect_called(1)
        provider.assert_disconnect_called(1)

        print("\n--- Summary ---")
        for k, v in provider.summary().items():
            print(f"  {k}: {v}")

        print("\nAll assertions passed ✓")

    asyncio.run(_demo())
