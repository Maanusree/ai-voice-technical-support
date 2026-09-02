"""
Call Session and Dialogue Turn Data Models
"""
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CallStatus(str, Enum):
    IDLE = "idle"
    RINGING = "ringing"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    ESCALATING = "escalating"
    COMPLETED = "completed"
    FAILED = "failed"


class ResolutionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    UNRESOLVED = "unresolved"
    DROPPED = "dropped"


class Turn(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: str  # "user", "assistant", "system"
    text: str
    timestamp: datetime = Field(default_factory=utc_now)
    audio_url: Optional[str] = None
    latency_ms: Optional[Dict[str, float]] = Field(default_factory=dict)
    confidence: Optional[float] = 1.0
    intent: Optional[str] = None
    step_id: Optional[str] = None


class DiagnosticsState(BaseModel):
    scenario_id: Optional[str] = None
    current_step_index: int = 0
    attempted_steps: List[str] = Field(default_factory=list)
    failure_count: int = 0
    is_clarifying: bool = False
    context_data: Dict[str, Any] = Field(default_factory=dict)


class CallSession(BaseModel):
    session_id: str = Field(default_factory=lambda: f"call_{uuid.uuid4().hex[:10]}")
    caller_number: str = "+1-800-555-0199"
    caller_name: Optional[str] = "Customer"
    start_time: datetime = Field(default_factory=utc_now)
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    status: CallStatus = CallStatus.ACTIVE
    issue_category: Optional[str] = "General Inquiries"
    issue_summary: Optional[str] = None
    resolution_status: ResolutionStatus = ResolutionStatus.IN_PROGRESS
    sentiment: str = "neutral"  # "positive", "neutral", "frustrated", "urgent"
    language: str = "en"  # "en" by default, switches to "ta" if caller insists
    call_type: str = "Website"  # "Website" or "Phone"
    diagnostics: DiagnosticsState = Field(default_factory=DiagnosticsState)
    turns: List[Turn] = Field(default_factory=list)
    escalation_ticket_id: Optional[str] = None
    agent_notes: Optional[str] = None

    def add_turn(self, role: str, text: str, latency_ms: Optional[Dict[str, float]] = None, intent: Optional[str] = None) -> Turn:
        turn = Turn(
            role=role,
            text=text,
            latency_ms=latency_ms or {},
            intent=intent
        )
        self.turns.append(turn)
        return turn

    def end_call(self, resolution: ResolutionStatus = ResolutionStatus.RESOLVED) -> None:
        self.end_time = utc_now()
        self.duration_seconds = max(0.0, (self.end_time - self.start_time).total_seconds())
        self.status = CallStatus.COMPLETED
        self.resolution_status = resolution
