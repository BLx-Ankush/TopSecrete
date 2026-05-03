"""
VAD Turn-Taking Monitor Module

This module monitors VAD-based turn-taking behavior to ensure:
- VAD end-of-speech detection triggers LLM responses
- Alice responds within 200ms of VAD trigger
- Conversation state is maintained across overlapping exchanges

Requirements: 4.3, 5.1, 5.2, 5.3
"""

import logging
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TurnTakingMetrics:
    """Metrics for a single conversation turn"""
    turn_id: int
    user_speech_start: Optional[float] = None
    user_speech_end: Optional[float] = None
    vad_trigger_time: Optional[float] = None
    llm_response_start: Optional[float] = None
    alice_speech_start: Optional[float] = None
    
    # Calculated latencies
    vad_trigger_latency_ms: Optional[float] = None  # Time from speech end to VAD trigger
    llm_response_latency_ms: Optional[float] = None  # Time from VAD trigger to LLM response
    total_turn_latency_ms: Optional[float] = None  # Time from user stops to Alice starts
    
    # Context preservation
    conversation_context_preserved: bool = True
    overlapping_exchange: bool = False
    
    def calculate_latencies(self):
        """Calculate latency metrics from timestamps"""
        if self.user_speech_end and self.vad_trigger_time:
            self.vad_trigger_latency_ms = (self.vad_trigger_time - self.user_speech_end) * 1000
        
        if self.vad_trigger_time and self.llm_response_start:
            self.llm_response_latency_ms = (self.llm_response_start - self.vad_trigger_time) * 1000
        
        if self.user_speech_end and self.alice_speech_start:
            self.total_turn_latency_ms = (self.alice_speech_start - self.user_speech_end) * 1000
    
    def meets_requirements(self) -> bool:
        """Check if turn meets latency requirements (< 200ms response time)"""
        if self.llm_response_latency_ms is None:
            return False
        return self.llm_response_latency_ms <= 200


@dataclass
class TurnTakingSession:
    """Session-level turn-taking metrics"""
    session_id: str
    start_time: float = field(default_factory=time.time)
    turns: List[TurnTakingMetrics] = field(default_factory=list)
    current_turn_id: int = 0
    
    def get_summary(self) -> Dict[str, any]:
        """Get session summary with aggregated metrics"""
        if not self.turns:
            return {
                'session_id': self.session_id,
                'total_turns': 0,
                'message': 'No turns recorded'
            }
        
        # Calculate aggregated metrics
        response_latencies = [t.llm_response_latency_ms for t in self.turns if t.llm_response_latency_ms is not None]
        total_latencies = [t.total_turn_latency_ms for t in self.turns if t.total_turn_latency_ms is not None]
        
        turns_meeting_requirements = sum(1 for t in self.turns if t.meets_requirements())
        overlapping_exchanges = sum(1 for t in self.turns if t.overlapping_exchange)
        context_preserved = sum(1 for t in self.turns if t.conversation_context_preserved)
        
        summary = {
            'session_id': self.session_id,
            'total_turns': len(self.turns),
            'turns_meeting_requirements': turns_meeting_requirements,
            'requirement_compliance_rate': turns_meeting_requirements / len(self.turns) if self.turns else 0,
            'overlapping_exchanges': overlapping_exchanges,
            'context_preservation_rate': context_preserved / len(self.turns) if self.turns else 0,
        }
        
        if response_latencies:
            summary['avg_response_latency_ms'] = sum(response_latencies) / len(response_latencies)
            summary['min_response_latency_ms'] = min(response_latencies)
            summary['max_response_latency_ms'] = max(response_latencies)
        
        if total_latencies:
            summary['avg_total_turn_latency_ms'] = sum(total_latencies) / len(total_latencies)
            summary['min_total_turn_latency_ms'] = min(total_latencies)
            summary['max_total_turn_latency_ms'] = max(total_latencies)
        
        return summary


class VADTurnTakingMonitor:
    """
    Monitor for VAD-based turn-taking behavior.
    
    This class tracks conversation turns and measures:
    - VAD trigger latency
    - LLM response latency
    - Total turn-taking latency
    - Context preservation across turns
    """
    
    def __init__(self, session_id: str = "default"):
        """
        Initialize turn-taking monitor.
        
        Args:
            session_id: Unique identifier for this conversation session
        """
        self.session = TurnTakingSession(session_id=session_id)
        self.current_turn: Optional[TurnTakingMetrics] = None
        
        logger.info(f"[Turn-Taking Monitor] Initialized for session: {session_id}")
    
    def on_user_speech_start(self) -> None:
        """Called when user starts speaking"""
        # Start a new turn
        self.session.current_turn_id += 1
        self.current_turn = TurnTakingMetrics(turn_id=self.session.current_turn_id)
        self.current_turn.user_speech_start = time.time()
        
        logger.debug(f"[Turn {self.current_turn.turn_id}] User speech started")
    
    def on_user_speech_end(self) -> None:
        """Called when user stops speaking"""
        if self.current_turn is None:
            logger.warning("[Turn-Taking Monitor] Speech end without speech start")
            return
        
        self.current_turn.user_speech_end = time.time()
        
        if self.current_turn.user_speech_start:
            duration_ms = (self.current_turn.user_speech_end - self.current_turn.user_speech_start) * 1000
            logger.debug(f"[Turn {self.current_turn.turn_id}] User speech ended (duration: {duration_ms:.0f}ms)")
    
    def on_vad_trigger(self) -> None:
        """Called when VAD triggers end-of-speech detection"""
        if self.current_turn is None:
            logger.warning("[Turn-Taking Monitor] VAD trigger without active turn")
            return
        
        self.current_turn.vad_trigger_time = time.time()
        
        # Calculate VAD trigger latency
        if self.current_turn.user_speech_end:
            latency_ms = (self.current_turn.vad_trigger_time - self.current_turn.user_speech_end) * 1000
            logger.info(f"[Turn {self.current_turn.turn_id}] VAD triggered (latency: {latency_ms:.0f}ms from speech end)")
    
    def on_llm_response_start(self) -> None:
        """Called when LLM starts generating response"""
        if self.current_turn is None:
            logger.warning("[Turn-Taking Monitor] LLM response without active turn")
            return
        
        self.current_turn.llm_response_start = time.time()
        
        # Calculate LLM response latency from VAD trigger
        if self.current_turn.vad_trigger_time:
            latency_ms = (self.current_turn.llm_response_start - self.current_turn.vad_trigger_time) * 1000
            
            # Check if meets requirement (< 200ms)
            meets_req = latency_ms <= 200
            status = "✓" if meets_req else "✗"
            
            logger.info(
                f"[Turn {self.current_turn.turn_id}] {status} LLM response started "
                f"(latency: {latency_ms:.0f}ms from VAD trigger, requirement: <200ms)"
            )
    
    def on_alice_speech_start(self) -> None:
        """Called when Alice starts speaking"""
        if self.current_turn is None:
            logger.warning("[Turn-Taking Monitor] Alice speech without active turn")
            return
        
        self.current_turn.alice_speech_start = time.time()
        
        # Calculate total turn latency
        if self.current_turn.user_speech_end:
            latency_ms = (self.current_turn.alice_speech_start - self.current_turn.user_speech_end) * 1000
            logger.info(f"[Turn {self.current_turn.turn_id}] Alice speech started (total turn latency: {latency_ms:.0f}ms)")
    
    def on_turn_complete(self, context_preserved: bool = True, overlapping: bool = False) -> None:
        """
        Called when conversation turn is complete.
        
        Args:
            context_preserved: Whether conversation context was maintained
            overlapping: Whether this was an overlapping exchange
        """
        if self.current_turn is None:
            logger.warning("[Turn-Taking Monitor] Turn complete without active turn")
            return
        
        # Set context preservation flags
        self.current_turn.conversation_context_preserved = context_preserved
        self.current_turn.overlapping_exchange = overlapping
        
        # Calculate all latencies
        self.current_turn.calculate_latencies()
        
        # Add to session
        self.session.turns.append(self.current_turn)
        
        # Log turn summary
        self._log_turn_summary(self.current_turn)
        
        # Reset current turn
        self.current_turn = None
    
    def _log_turn_summary(self, turn: TurnTakingMetrics) -> None:
        """Log summary of completed turn"""
        logger.info("=" * 60)
        logger.info(f"Turn {turn.turn_id} Summary")
        logger.info("=" * 60)
        
        if turn.vad_trigger_latency_ms is not None:
            logger.info(f"VAD Trigger Latency: {turn.vad_trigger_latency_ms:.0f}ms")
        
        if turn.llm_response_latency_ms is not None:
            meets_req = turn.meets_requirements()
            status = "✓ PASS" if meets_req else "✗ FAIL"
            logger.info(f"LLM Response Latency: {turn.llm_response_latency_ms:.0f}ms ({status} - requirement: <200ms)")
        
        if turn.total_turn_latency_ms is not None:
            logger.info(f"Total Turn Latency: {turn.total_turn_latency_ms:.0f}ms")
        
        logger.info(f"Context Preserved: {'✓' if turn.conversation_context_preserved else '✗'}")
        logger.info(f"Overlapping Exchange: {'Yes' if turn.overlapping_exchange else 'No'}")
        logger.info("=" * 60)
    
    def get_session_summary(self) -> Dict[str, any]:
        """Get summary of all turns in this session"""
        return self.session.get_summary()
    
    def log_session_summary(self) -> None:
        """Log session summary with aggregated metrics"""
        summary = self.get_session_summary()
        
        logger.info("\n" + "=" * 60)
        logger.info("TURN-TAKING SESSION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Session ID: {summary['session_id']}")
        logger.info(f"Total Turns: {summary['total_turns']}")
        
        if summary['total_turns'] > 0:
            logger.info(f"Turns Meeting Requirements (<200ms): {summary['turns_meeting_requirements']}")
            logger.info(f"Requirement Compliance Rate: {summary['requirement_compliance_rate']:.1%}")
            logger.info(f"Overlapping Exchanges: {summary['overlapping_exchanges']}")
            logger.info(f"Context Preservation Rate: {summary['context_preservation_rate']:.1%}")
            
            if 'avg_response_latency_ms' in summary:
                logger.info(f"\nLLM Response Latency:")
                logger.info(f"  Average: {summary['avg_response_latency_ms']:.0f}ms")
                logger.info(f"  Min: {summary['min_response_latency_ms']:.0f}ms")
                logger.info(f"  Max: {summary['max_response_latency_ms']:.0f}ms")
            
            if 'avg_total_turn_latency_ms' in summary:
                logger.info(f"\nTotal Turn Latency:")
                logger.info(f"  Average: {summary['avg_total_turn_latency_ms']:.0f}ms")
                logger.info(f"  Min: {summary['min_total_turn_latency_ms']:.0f}ms")
                logger.info(f"  Max: {summary['max_total_turn_latency_ms']:.0f}ms")
        
        logger.info("=" * 60 + "\n")


# Global monitor instance
_global_monitor: Optional[VADTurnTakingMonitor] = None


def get_turn_taking_monitor(session_id: str = "default") -> VADTurnTakingMonitor:
    """
    Get or create the global turn-taking monitor.
    
    Args:
        session_id: Session identifier
    
    Returns:
        VADTurnTakingMonitor instance
    """
    global _global_monitor
    
    if _global_monitor is None or _global_monitor.session.session_id != session_id:
        _global_monitor = VADTurnTakingMonitor(session_id=session_id)
    
    return _global_monitor


def reset_turn_taking_monitor() -> None:
    """Reset the global turn-taking monitor"""
    global _global_monitor
    _global_monitor = None
