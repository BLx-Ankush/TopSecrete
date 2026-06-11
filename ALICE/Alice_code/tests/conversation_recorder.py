"""
Conversation Recording and Playback for Regression Testing.

This module provides two complementary classes for capturing and replaying
Alice conversation sessions during test runs:

    ConversationRecorder
        Records audio frames and structured events (turn detections,
        interruptions, STT results, etc.) as they happen during an
        integration test or a live session.  Saves the recording to a
        self-contained JSON file.

    ConversationPlayer
        Loads a JSON recording produced by ConversationRecorder and plays
        it back deterministically, calling user-supplied callbacks for each
        audio frame.  Supports time-accurate playback (honouring the
        original inter-frame gaps) or instant playback for fast unit tests.

Typical usage
-------------
Recording::

    async def test_full_conversation():
        recorder = ConversationRecorder(session_id="test-001")

        for frame in audio_frames:
            recorder.record_audio_frame(frame, {"source": "microphone"})

        recorder.record_event("turn_detected", {"confidence": 0.92})
        recorder.save_to_json("recordings/test_001.json")

Playback::

    player = ConversationPlayer.load_from_json("recordings/test_001.json")

    async def handle_frame(frame_bytes: bytes, meta: dict) -> None:
        await stt_provider.stream_audio(frame_bytes)

    await player.play_audio_frames(handle_frame, realtime=False)
    events = player.get_events_of_type("turn_detected")

File format (JSON schema, version "1.0")
-----------------------------------------
::

    {
      "schema_version": "1.0",
      "session_id": "<str>",
      "recorded_at_iso": "<ISO-8601 timestamp>",
      "audio_config": {
        "sample_rate": 24000,
        "channels": 1,
        "encoding": "pcm_s16le"
      },
      "frames": [
        {
          "index": 0,
          "timestamp_ms": <int>,
          "duration_ms": <int>,
          "size_bytes": <int>,
          "audio_b64": "<base64-encoded PCM bytes>",
          "metadata": { ... }
        },
        ...
      ],
      "events": [
        {
          "index": 0,
          "event_type": "<str>",
          "timestamp_ms": <int>,
          "data": { ... }
        },
        ...
      ]
    }

Requirements: 10.2, 10.3, 10.4, 10.5, 11.1
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema version — bump when the JSON format changes in a breaking way
# ---------------------------------------------------------------------------
SCHEMA_VERSION: str = "1.0"

#: Audio pipeline constants (must match stt/provider.py and synthetic_audio.py)
SAMPLE_RATE: int = 24_000
CHANNELS: int = 1
ENCODING: str = "pcm_s16le"
BYTES_PER_SAMPLE: int = 2


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class RecordedFrame:
    """
    A single recorded audio frame with timing and metadata.

    Attributes
    ----------
    index
        Zero-based frame index within the recording.
    timestamp_ms
        Wall-clock timestamp (ms since epoch) when the frame was recorded.
    duration_ms
        Duration of the audio represented by this frame, computed from the
        PCM byte count.
    size_bytes
        Number of bytes in the raw PCM frame.
    audio_b64
        Base-64 encoded raw PCM bytes.
    metadata
        Arbitrary key-value pairs supplied by the caller at record time.
        Useful for tagging frames with VAD state, STT result IDs, etc.
    """

    index: int
    timestamp_ms: int
    duration_ms: float
    size_bytes: int
    audio_b64: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    @classmethod
    def from_audio_bytes(
        cls,
        index: int,
        audio_bytes: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "RecordedFrame":
        """
        Build a RecordedFrame from raw PCM bytes.

        Parameters
        ----------
        index
            Frame index within the recording.
        audio_bytes
            Raw PCM s16le bytes.
        metadata
            Optional caller-supplied metadata dict.
        """
        n_samples = len(audio_bytes) // BYTES_PER_SAMPLE
        duration_ms = (n_samples / SAMPLE_RATE) * 1000.0
        return cls(
            index=index,
            timestamp_ms=int(time.time() * 1000),
            duration_ms=round(duration_ms, 3),
            size_bytes=len(audio_bytes),
            audio_b64=base64.b64encode(audio_bytes).decode("ascii"),
            metadata=metadata or {},
        )

    def decode_audio(self) -> bytes:
        """
        Decode and return the raw PCM bytes.

        Returns
        -------
        bytes
            Raw PCM s16le bytes.
        """
        return base64.b64decode(self.audio_b64)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecordedFrame":
        """Deserialize from a JSON-compatible dictionary."""
        return cls(**data)


@dataclass
class RecordedEvent:
    """
    A single structured event captured during a conversation session.

    Events are used to record higher-level observations: turn detection
    triggers, interruption classifications, VAD state changes, STT results,
    custom annotations, etc.

    Attributes
    ----------
    index
        Zero-based event index within the recording.
    event_type
        String label identifying the type of event (e.g., "turn_detected",
        "interruption_classified", "vad_triggered").
    timestamp_ms
        Wall-clock timestamp (ms since epoch) when the event was recorded.
    data
        Arbitrary serializable payload associated with the event.
    """

    index: int
    event_type: str
    timestamp_ms: int
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecordedEvent":
        """Deserialize from a JSON-compatible dictionary."""
        return cls(**data)


# ---------------------------------------------------------------------------
# ConversationRecorder
# ---------------------------------------------------------------------------

class ConversationRecorder:
    """
    Records audio frames and structured events from a conversation session.

    The recorder buffers all data in memory and serializes to JSON on demand
    via :meth:`save_to_json`.  It is designed to be thread-safe for
    sequential access from a single asyncio coroutine (the typical test
    scenario).

    Parameters
    ----------
    session_id
        Human-readable identifier for this recording session.  Embedded in
        the JSON file for traceability.  Defaults to a timestamp-based ID.
    description
        Optional free-text description of what is being recorded.

    Attributes
    ----------
    session_id : str
    description : str
    frames : List[RecordedFrame]
        All recorded audio frames in chronological order.
    events : List[RecordedEvent]
        All recorded events in chronological order.

    Examples
    --------
    >>> recorder = ConversationRecorder(session_id="my-test")
    >>> recorder.record_audio_frame(b"\\x00" * 480, {"vad": "speech"})
    >>> recorder.record_event("turn_detected", {"confidence": 0.91})
    >>> recorder.save_to_json("/tmp/my_test.json")
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        description: str = "",
    ) -> None:
        self.session_id: str = session_id or _default_session_id()
        self.description: str = description
        self._recorded_at: datetime = datetime.now(tz=timezone.utc)

        self.frames: List[RecordedFrame] = []
        self.events: List[RecordedEvent] = []

        logger.debug(
            "ConversationRecorder created: session_id=%r", self.session_id
        )

    # ------------------------------------------------------------------
    # Recording methods
    # ------------------------------------------------------------------

    def record_audio_frame(
        self,
        audio_bytes: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RecordedFrame:
        """
        Record a raw PCM audio frame.

        Parameters
        ----------
        audio_bytes
            Raw PCM s16le bytes (any size; typically 20 ms = 960 bytes at
            24 kHz / 16-bit mono).
        metadata
            Optional key-value pairs to attach to this frame, e.g.::

                {"vad_state": "speech", "stt_result_id": "abc123"}

        Returns
        -------
        RecordedFrame
            The newly created frame object (also appended to ``self.frames``).

        Raises
        ------
        ValueError
            If *audio_bytes* is empty.

        Examples
        --------
        >>> recorder = ConversationRecorder()
        >>> frame = recorder.record_audio_frame(b"\\x00" * 480, {"source": "mic"})
        >>> frame.index
        0
        >>> frame.size_bytes
        480
        """
        if not audio_bytes:
            raise ValueError("audio_bytes must be non-empty")

        frame = RecordedFrame.from_audio_bytes(
            index=len(self.frames),
            audio_bytes=audio_bytes,
            metadata=metadata,
        )
        self.frames.append(frame)
        logger.debug(
            "ConversationRecorder: recorded frame %d (%d bytes, %.1f ms)",
            frame.index,
            frame.size_bytes,
            frame.duration_ms,
        )
        return frame

    def record_event(
        self,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> RecordedEvent:
        """
        Record a structured turn/interruption/VAD event.

        Parameters
        ----------
        event_type
            String identifier for the event.  Use consistent names across
            tests so that :meth:`ConversationPlayer.get_events_of_type` can
            filter them reliably.  Recommended names:

            * ``"turn_detected"``
            * ``"interruption_classified"``
            * ``"vad_triggered"``
            * ``"stt_result"``
            * ``"fallback_triggered"``
            * ``"session_start"`` / ``"session_end"``

        event_data
            Arbitrary serializable payload.  Must contain only types that
            ``json.dumps`` can handle (str, int, float, bool, list, dict,
            None).

        Returns
        -------
        RecordedEvent
            The newly created event object (also appended to ``self.events``).

        Examples
        --------
        >>> recorder = ConversationRecorder()
        >>> ev = recorder.record_event("turn_detected", {"confidence": 0.95})
        >>> ev.event_type
        'turn_detected'
        >>> ev.data["confidence"]
        0.95
        """
        if not event_type or not event_type.strip():
            raise ValueError("event_type must be a non-empty string")

        event = RecordedEvent(
            index=len(self.events),
            event_type=event_type.strip(),
            timestamp_ms=int(time.time() * 1000),
            data=event_data or {},
        )
        self.events.append(event)
        logger.debug(
            "ConversationRecorder: recorded event %d type=%r",
            event.index,
            event.event_type,
        )
        return event

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_to_json(self, filepath: Union[str, os.PathLike]) -> None:
        """
        Serialize the entire recording to a JSON file.

        The parent directory is created automatically if it does not exist.

        Parameters
        ----------
        filepath
            Destination path for the JSON file.  Typically ends in ``.json``.

        Raises
        ------
        OSError
            If the file cannot be created or written.

        Examples
        --------
        >>> recorder = ConversationRecorder(session_id="demo")
        >>> recorder.record_audio_frame(b"\\x00" * 480)
        >>> recorder.save_to_json("/tmp/demo.json")
        """
        filepath = str(filepath)
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        payload = self._to_dict()
        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

        size_kb = os.path.getsize(filepath) / 1024
        logger.info(
            "ConversationRecorder: saved %d frames + %d events to %s (%.1f KB)",
            len(self.frames),
            len(self.events),
            filepath,
            size_kb,
        )

    def _to_dict(self) -> Dict[str, Any]:
        """Build the full JSON payload dictionary."""
        return {
            "schema_version": SCHEMA_VERSION,
            "session_id": self.session_id,
            "description": self.description,
            "recorded_at_iso": self._recorded_at.isoformat(),
            "audio_config": {
                "sample_rate": SAMPLE_RATE,
                "channels": CHANNELS,
                "encoding": ENCODING,
            },
            "stats": {
                "total_frames": len(self.frames),
                "total_events": len(self.events),
                "total_audio_bytes": sum(f.size_bytes for f in self.frames),
                "total_duration_ms": sum(f.duration_ms for f in self.frames),
            },
            "frames": [f.to_dict() for f in self.frames],
            "events": [e.to_dict() for e in self.events],
        }

    # ------------------------------------------------------------------
    # Convenience / inspection
    # ------------------------------------------------------------------

    @property
    def total_duration_ms(self) -> float:
        """Total duration of all recorded audio frames in milliseconds."""
        return sum(f.duration_ms for f in self.frames)

    @property
    def total_audio_bytes(self) -> int:
        """Total number of raw PCM bytes across all recorded frames."""
        return sum(f.size_bytes for f in self.frames)

    def get_events_of_type(self, event_type: str) -> List[RecordedEvent]:
        """
        Return all recorded events matching *event_type*.

        Parameters
        ----------
        event_type
            Exact string to match against ``RecordedEvent.event_type``.

        Returns
        -------
        List[RecordedEvent]
            Matching events in recording order (may be empty).
        """
        return [e for e in self.events if e.event_type == event_type]

    def __repr__(self) -> str:
        return (
            f"ConversationRecorder("
            f"session_id={self.session_id!r}, "
            f"frames={len(self.frames)}, "
            f"events={len(self.events)}, "
            f"duration={self.total_duration_ms:.0f} ms)"
        )


# ---------------------------------------------------------------------------
# ConversationPlayer
# ---------------------------------------------------------------------------

class ConversationPlayer:
    """
    Loads and replays a conversation recording produced by ConversationRecorder.

    The player deserializes a JSON file and can replay audio frames by calling
    a user-supplied async callback for each frame.  It supports both
    time-accurate (realtime) playback and instant (fast) playback.

    Parameters
    ----------
    session_id
        Session ID extracted from the JSON file.
    description
        Description extracted from the JSON file.
    frames
        Ordered list of RecordedFrame objects.
    events
        Ordered list of RecordedEvent objects.
    audio_config
        Dict with keys: sample_rate, channels, encoding.

    Notes
    -----
    Instantiate via :meth:`load_from_json` rather than the constructor
    directly.

    Examples
    --------
    >>> player = ConversationPlayer.load_from_json("recording.json")
    >>> async def handle(frame_bytes, meta): ...
    >>> await player.play_audio_frames(handle)
    """

    def __init__(
        self,
        session_id: str,
        description: str,
        frames: List[RecordedFrame],
        events: List[RecordedEvent],
        audio_config: Dict[str, Any],
        schema_version: str = SCHEMA_VERSION,
    ) -> None:
        self.session_id: str = session_id
        self.description: str = description
        self.frames: List[RecordedFrame] = frames
        self.events: List[RecordedEvent] = events
        self.audio_config: Dict[str, Any] = audio_config
        self.schema_version: str = schema_version

        logger.debug(
            "ConversationPlayer loaded: session_id=%r, frames=%d, events=%d",
            session_id,
            len(frames),
            len(events),
        )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load_from_json(cls, filepath: Union[str, os.PathLike]) -> "ConversationPlayer":
        """
        Load a conversation recording from a JSON file.

        Parameters
        ----------
        filepath
            Path to the JSON file previously written by
            :meth:`ConversationRecorder.save_to_json`.

        Returns
        -------
        ConversationPlayer
            Ready-to-use player instance.

        Raises
        ------
        FileNotFoundError
            If *filepath* does not exist.
        json.JSONDecodeError
            If the file is not valid JSON.
        ValueError
            If the schema version is unsupported.

        Examples
        --------
        >>> player = ConversationPlayer.load_from_json("my_recording.json")
        >>> len(player.frames)
        42
        """
        filepath = str(filepath)
        if not os.path.isfile(filepath):
            raise FileNotFoundError(
                f"ConversationPlayer: recording file not found: {filepath!r}"
            )

        with open(filepath, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        schema_ver = data.get("schema_version", "unknown")
        if schema_ver != SCHEMA_VERSION:
            logger.warning(
                "ConversationPlayer: loading schema version %r (current: %r); "
                "compatibility not guaranteed.",
                schema_ver,
                SCHEMA_VERSION,
            )

        frames = [RecordedFrame.from_dict(f) for f in data.get("frames", [])]
        events = [RecordedEvent.from_dict(e) for e in data.get("events", [])]

        logger.info(
            "ConversationPlayer: loaded %d frames + %d events from %s",
            len(frames),
            len(events),
            filepath,
        )

        return cls(
            session_id=data.get("session_id", "unknown"),
            description=data.get("description", ""),
            frames=frames,
            events=events,
            audio_config=data.get("audio_config", {}),
            schema_version=schema_ver,
        )

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    async def play_audio_frames(
        self,
        callback: Callable[[bytes, Dict[str, Any]], Coroutine[Any, Any, None]],
        *,
        realtime: bool = False,
        frame_delay_ms: float = 0.0,
    ) -> int:
        """
        Replay all recorded audio frames by calling an async callback.

        Parameters
        ----------
        callback
            An async function (coroutine) that accepts two positional
            arguments:

            1. ``audio_bytes: bytes`` — raw PCM s16le frame data.
            2. ``metadata: dict`` — the frame's metadata dict.

            The callback is awaited for each frame in order.
        realtime
            If True, the player sleeps between frames to honour the original
            inter-frame timing.  The gap between consecutive frames is
            derived from the first frame's ``duration_ms``.  Default False
            (instant playback for fast tests).
        frame_delay_ms
            Fixed extra delay in milliseconds added between every frame
            (regardless of *realtime*).  Useful for throttling in integration
            tests.  Default 0.0 (no extra delay).

        Returns
        -------
        int
            Number of frames replayed.

        Examples
        --------
        >>> frames_played = await player.play_audio_frames(my_callback)
        >>> assert frames_played == len(player.frames)
        """
        if not self.frames:
            logger.warning("ConversationPlayer.play_audio_frames(): no frames to play")
            return 0

        played = 0
        prev_ts: Optional[float] = None

        for frame in self.frames:
            audio_bytes = frame.decode_audio()
            await callback(audio_bytes, dict(frame.metadata))
            played += 1

            # Optional timing logic
            if realtime and prev_ts is not None:
                gap_s = (frame.timestamp_ms - prev_ts) / 1000.0
                if gap_s > 0:
                    await asyncio.sleep(gap_s)

            if frame_delay_ms > 0:
                await asyncio.sleep(frame_delay_ms / 1000.0)

            prev_ts = frame.timestamp_ms

        logger.debug(
            "ConversationPlayer: played %d / %d frames", played, len(self.frames)
        )
        return played

    async def play_frames_chunked(
        self,
        callback: Callable[[bytes, Dict[str, Any]], Coroutine[Any, Any, None]],
        chunk_ms: int = 20,
        *,
        realtime: bool = False,
    ) -> int:
        """
        Re-chunk each recorded frame into fixed-size sub-frames before playback.

        Use this when the consumer expects a specific frame size (e.g., always
        20 ms frames) but the recording was made at a different granularity.

        Parameters
        ----------
        callback
            Same signature as :meth:`play_audio_frames`.
        chunk_ms
            Target sub-frame duration in ms.
        realtime
            Honour timing between sub-frames.

        Returns
        -------
        int
            Total number of sub-frames delivered to *callback*.
        """
        from synthetic_audio import chunk_audio  # type: ignore[import]

        total = 0
        for frame in self.frames:
            sub_frames = chunk_audio(frame.decode_audio(), chunk_ms=chunk_ms)
            for sf in sub_frames:
                await callback(sf, dict(frame.metadata))
                total += 1
                if realtime:
                    await asyncio.sleep(chunk_ms / 1000.0)
        return total

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_events_of_type(self, event_type: str) -> List[RecordedEvent]:
        """
        Return all events with a matching event_type.

        Parameters
        ----------
        event_type
            Exact string to match.

        Returns
        -------
        List[RecordedEvent]
            Matching events in recording order.

        Examples
        --------
        >>> events = player.get_events_of_type("turn_detected")
        >>> len(events)
        3
        """
        return [e for e in self.events if e.event_type == event_type]

    def get_frame_at(self, index: int) -> RecordedFrame:
        """
        Return the frame at a specific zero-based index.

        Raises
        ------
        IndexError
            If *index* is out of range.
        """
        if index < 0 or index >= len(self.frames):
            raise IndexError(
                f"ConversationPlayer: frame index {index} out of range "
                f"(0..{len(self.frames) - 1})"
            )
        return self.frames[index]

    def get_event_at(self, index: int) -> RecordedEvent:
        """
        Return the event at a specific zero-based index.

        Raises
        ------
        IndexError
            If *index* is out of range.
        """
        if index < 0 or index >= len(self.events):
            raise IndexError(
                f"ConversationPlayer: event index {index} out of range "
                f"(0..{len(self.events) - 1})"
            )
        return self.events[index]

    def get_unique_event_types(self) -> List[str]:
        """
        Return a sorted list of all unique event_type strings in the recording.

        Returns
        -------
        List[str]
            Sorted list of unique event type strings.
        """
        return sorted(set(e.event_type for e in self.events))

    @property
    def total_duration_ms(self) -> float:
        """Total duration of all recorded audio frames in milliseconds."""
        return sum(f.duration_ms for f in self.frames)

    @property
    def total_audio_bytes(self) -> int:
        """Total number of raw PCM bytes across all frames."""
        return sum(f.size_bytes for f in self.frames)

    # ------------------------------------------------------------------
    # Assertion helpers (for use in tests)
    # ------------------------------------------------------------------

    def assert_has_events(self, event_type: str, min_count: int = 1) -> None:
        """
        Assert that at least *min_count* events of *event_type* are present.

        Raises
        ------
        AssertionError
            If the count is below *min_count*.
        """
        found = self.get_events_of_type(event_type)
        assert len(found) >= min_count, (
            f"ConversationPlayer: expected at least {min_count} event(s) "
            f"of type {event_type!r}, found {len(found)}"
        )

    def assert_frame_count(self, expected: int) -> None:
        """
        Assert exact number of frames in the recording.

        Raises
        ------
        AssertionError
            If the frame count does not match.
        """
        assert len(self.frames) == expected, (
            f"ConversationPlayer: expected {expected} frame(s), "
            f"found {len(self.frames)}"
        )

    def __repr__(self) -> str:
        return (
            f"ConversationPlayer("
            f"session_id={self.session_id!r}, "
            f"frames={len(self.frames)}, "
            f"events={len(self.events)}, "
            f"duration={self.total_duration_ms:.0f} ms)"
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _default_session_id() -> str:
    """Generate a timestamp-based default session ID."""
    return datetime.now(tz=timezone.utc).strftime("session-%Y%m%d-%H%M%S")


# ---------------------------------------------------------------------------
# pytest fixtures
# ---------------------------------------------------------------------------

try:
    import pytest  # noqa: F401
    import tempfile

    @pytest.fixture
    def conversation_recorder() -> ConversationRecorder:
        """
        Pytest fixture that yields a fresh ConversationRecorder per test.

        Usage
        -----
        .. code-block:: python

            def test_recording(conversation_recorder):
                conversation_recorder.record_audio_frame(b"\\x00" * 480)
                assert len(conversation_recorder.frames) == 1
        """
        return ConversationRecorder(session_id="pytest-session")

    @pytest.fixture
    def recording_tempfile() -> str:
        """
        Pytest fixture that yields a temporary file path for JSON recordings.

        The file is automatically removed after the test completes.

        Usage
        -----
        .. code-block:: python

            def test_save_load(conversation_recorder, recording_tempfile):
                conversation_recorder.save_to_json(recording_tempfile)
                player = ConversationPlayer.load_from_json(recording_tempfile)
        """
        import tempfile as _tempfile
        with _tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        ) as f:
            tmp_path = f.name
        yield tmp_path
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

except ImportError:
    pass  # pytest not installed; fixtures silently unavailable


# ---------------------------------------------------------------------------
# Standalone demo / smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio
    import tempfile

    async def _demo() -> None:
        print("=== ConversationRecorder / ConversationPlayer Demo ===\n")

        # ---- Recording phase ----
        recorder = ConversationRecorder(
            session_id="demo-001",
            description="Demo conversation with two turns",
        )

        # Simulate 5 audio frames of 20 ms each (960 bytes at 24 kHz / 16-bit mono)
        frame_bytes = b"\x01\x02" * 480  # 960 bytes, non-silent
        for i in range(5):
            recorder.record_audio_frame(frame_bytes, metadata={"frame_no": i})

        # Record some turn events
        recorder.record_event("vad_triggered", {"energy": 0.42})
        recorder.record_event("stt_result", {"text": "What is the weather?", "confidence": 0.97})
        recorder.record_event("turn_detected", {"confidence": 0.93, "threshold": 0.70})
        recorder.record_event("stt_result", {"text": "", "is_final": False})
        recorder.record_event("interruption_classified", {"classification": "noise"})

        print(f"Recorder: {recorder}")
        print(f"  total_audio_bytes  : {recorder.total_audio_bytes}")
        print(f"  total_duration_ms  : {recorder.total_duration_ms:.1f}")

        # ---- Save ----
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        ) as f:
            tmp_path = f.name

        recorder.save_to_json(tmp_path)
        print(f"\nSaved to: {tmp_path}")

        # ---- Playback phase ----
        player = ConversationPlayer.load_from_json(tmp_path)
        print(f"\nPlayer: {player}")
        print(f"  unique event types : {player.get_unique_event_types()}")

        received_frames: list = []

        async def on_frame(audio: bytes, meta: dict) -> None:
            received_frames.append((audio, meta))

        played = await player.play_audio_frames(on_frame, realtime=False)
        print(f"\n  Frames played      : {played}")
        print(f"  Frames received    : {len(received_frames)}")

        # ---- Assertions ----
        player.assert_frame_count(5)
        player.assert_has_events("turn_detected", min_count=1)
        player.assert_has_events("stt_result", min_count=2)

        assert played == 5
        assert len(received_frames) == 5

        turn_events = player.get_events_of_type("turn_detected")
        assert len(turn_events) == 1
        assert turn_events[0].data["confidence"] == 0.93

        # ---- Cleanup ----
        os.unlink(tmp_path)

        print("\nAll assertions passed ✓")

    asyncio.run(_demo())
