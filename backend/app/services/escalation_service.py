"""
Escalation & Support Ticketing Service
"""
import json
import re
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from ..config import settings
from ..models.ticket import EscalationTicket, TicketPriority, TicketStatus
from ..models.call_session import CallSession, Turn, ResolutionStatus, CallStatus


class EscalationService:
    def __init__(self, tickets_dir: Optional[Path] = None):
        self.tickets_dir = tickets_dir or settings.TICKETS_DIR
        self.tickets_dir.mkdir(parents=True, exist_ok=True)
        self.critical_hazard_keywords = {
            "smoke", "burning", "burnt", "fire", "spark", "sparking",
            "explosion", "shock", "electrocuted", "water damage", "liquid spill",
            "spilled water", "spilled coffee", "hacked", "ransomware",
            "புகை", "நெருப்பு", "தீ விபத்து", "வெடிப்பு", "puga", "eriyudhu"
        }
        self.human_request_keywords = {
            "human", "representative", "agent", "person", "supervisor",
            "manager", "operator", "real person", "escalate", "escalation",
            "transfer me", "speak to someone", "talk to someone", "live person",
            "live agent", "real human", "not resolve", "not resolved", "unresolved",
            "not fixed", "didn't resolve", "did not resolve", "tried everything",
            "escalate my ticket", "escalate to human", "transfer to human", "connect to human",
            "மனிதர்", "மனித", "மேலாளர்", "அதிகாரி", "சரியாகவில்லை", "தீரவில்லை", "எஸ்கலேட்", "டிக்கெட்",
            "manushan", "manithar", "solve aagala", "seriyagala", "theerala", "escalate pannunga", "human kitta"
        }
        self.frustration_keywords = {
            "ridiculous", "angry", "furious", "unacceptable", "terrible",
            "waste of time", "useless", "stupid", "hate this", "horrible"
        }

    def check_escalation_triggers(
        self,
        user_message: str,
        session: CallSession
    ) -> Tuple[bool, Optional[TicketPriority], Optional[str]]:
        """
        Analyzes message and call session context to decide if call must escalate.
        Returns: (should_escalate, priority, reason)
        """
        msg_lower = user_message.lower()
        tokens = set(re.findall(r"\w+", msg_lower))

        # 1. Critical safety hazard check (English, Tamil, Tanglish)
        for kw in self.critical_hazard_keywords:
            clean_kw = kw.strip().lower()
            if not clean_kw:
                continue
            if " " in clean_kw:
                if clean_kw in msg_lower:
                    return True, TicketPriority.CRITICAL, f"Physical safety or critical security hazard detected: '{clean_kw}'"
            else:
                if clean_kw in tokens or re.search(r'\b' + re.escape(clean_kw) + r'\b', msg_lower):
                    return True, TicketPriority.CRITICAL, f"Physical safety or critical security hazard detected: '{clean_kw}'"

        # 2. Explicit human agent request (English, Tamil, Tanglish)
        for kw in self.human_request_keywords:
            clean_kw = kw.strip().lower()
            if not clean_kw:
                continue
            if " " in clean_kw:
                if clean_kw in msg_lower:
                    return True, TicketPriority.HIGH, f"Customer requested human agent transfer: '{clean_kw}'"
            else:
                if clean_kw in tokens or clean_kw in msg_lower:
                    return True, TicketPriority.HIGH, f"Customer requested human agent transfer: '{clean_kw}'"

        # 3. High frustration sentiment
        frustration_count = sum(1 for kw in self.frustration_keywords if kw in msg_lower)
        if frustration_count >= 1 or session.sentiment == "frustrated":
            if session.diagnostics.failure_count >= 2:
                return True, TicketPriority.HIGH, "Customer frustration coupled with multiple troubleshooting failures."

        # 4. Step exhaustion (failure count threshold reached)
        if session.diagnostics.failure_count >= 3:
            return True, TicketPriority.MEDIUM, "Standard troubleshooting steps exhausted without resolution."

        return False, None, None

    def analyze_sentiment(self, text: str) -> str:
        """Simple sentiment heuristic."""
        text_lower = text.lower()
        if any(w in text_lower for w in self.critical_hazard_keywords):
            return "urgent"
        if any(w in text_lower for w in self.frustration_keywords) or "angry" in text_lower:
            return "frustrated"
        if any(w in text_lower for w in ["thank", "great", "awesome", "perfect", "fixed", "appreciate", "helpful", "good"]):
            return "positive"
        return "neutral"

    def create_escalation_ticket(
        self,
        session: CallSession,
        reason: str,
        priority: TicketPriority = TicketPriority.MEDIUM,
        issue_category: Optional[str] = None
    ) -> EscalationTicket:
        """
        Creates and persists a support ticket and links it to the session.
        """
        ticket = EscalationTicket(
            session_id=session.session_id,
            caller_number=session.caller_number,
            caller_name=session.caller_name or "Customer",
            priority=priority,
            category=issue_category or session.issue_category or "Technical Support",
            issue_summary=session.issue_summary or f"Issue reported in session {session.session_id}",
            attempted_steps=list(session.diagnostics.attempted_steps),
            reason_for_escalation=reason,
            customer_sentiment=session.sentiment,
            transcript_turns=[turn.model_dump() for turn in session.turns]
        )

        session.escalation_ticket_id = ticket.ticket_id
        session.status = CallStatus.ESCALATING
        session.resolution_status = ResolutionStatus.ESCALATED

        self.save_ticket(ticket)
        return ticket

    def save_ticket(self, ticket: EscalationTicket) -> Path:
        file_path = self.tickets_dir / f"{ticket.ticket_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(ticket.model_dump_json(indent=2))
        return file_path

    def get_ticket(self, ticket_id: str) -> Optional[EscalationTicket]:
        file_path = self.tickets_dir / f"{ticket_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return EscalationTicket(**data)
        except Exception as e:
            print(f"Error loading ticket {ticket_id}: {e}")
            return None

    def list_tickets(self) -> List[EscalationTicket]:
        tickets = []
        for file in self.tickets_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                tickets.append(EscalationTicket(**data))
            except Exception as e:
                print(f"Error reading ticket {file}: {e}")
        tickets.sort(key=lambda t: t.created_at.timestamp() if t.created_at else 0.0, reverse=True)
        return tickets


escalation_service = EscalationService()
