"""
Support Escalation Ticket Models
"""
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TicketPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class EscalationTicket(BaseModel):
    ticket_id: str = Field(default_factory=lambda: f"TICK-{uuid.uuid4().hex[:6].upper()}")
    session_id: str
    caller_number: str = "+1-800-555-0199"
    caller_name: Optional[str] = "Customer"
    created_at: datetime = Field(default_factory=utc_now)
    priority: TicketPriority = TicketPriority.MEDIUM
    status: TicketStatus = TicketStatus.OPEN
    category: str
    issue_summary: str
    attempted_steps: List[str] = Field(default_factory=list)
    reason_for_escalation: str
    customer_sentiment: str = "neutral"
    assigned_tier: str = "Tier 2 - Senior Technical Specialist"
    transcript_turns: List[Dict[str, Any]] = Field(default_factory=list)
