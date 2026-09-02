"""
Tests for Escalation Triggers and Support Ticket Generation
"""
import pytest
from backend.app.services.session_service import session_service
from backend.app.services.escalation_service import escalation_service
from backend.app.models.ticket import TicketPriority
from backend.app.models.call_session import ResolutionStatus


def test_safety_hazard_escalation_trigger():
    session = session_service.create_session()
    should_esc, priority, reason = escalation_service.check_escalation_triggers(
        "There is smoke coming out of my computer power supply!", session
    )
    assert should_esc is True
    assert priority == TicketPriority.CRITICAL
    assert "safety" in reason.lower() or "smoke" in reason.lower()


def test_human_agent_request_trigger():
    session = session_service.create_session()
    should_esc, priority, reason = escalation_service.check_escalation_triggers(
        "Please transfer me to a human agent right now", session
    )
    assert should_esc is True
    assert priority == TicketPriority.HIGH
    assert "human" in reason.lower() or "agent" in reason.lower()


def test_ticket_creation_and_persistence():
    session = session_service.create_session(caller_number="+1-800-555-9999", caller_name="Alice Smith")
    session.add_turn("user", "My printer is completely broken and making grinding sounds")
    
    ticket = escalation_service.create_escalation_ticket(
        session=session,
        reason="Hardware grinding noise requires field technician",
        priority=TicketPriority.HIGH,
        issue_category="Hardware & Peripherals"
    )

    assert ticket.ticket_id.startswith("TICK-")
    assert session.escalation_ticket_id == ticket.ticket_id
    assert session.resolution_status == ResolutionStatus.ESCALATED

    # Verify retrieval from disk
    loaded_ticket = escalation_service.get_ticket(ticket.ticket_id)
    assert loaded_ticket is not None
    assert loaded_ticket.caller_name == "Alice Smith"
    assert loaded_ticket.priority == TicketPriority.HIGH


def test_customer_unresolved_request_escalates_to_human():
    session = session_service.create_session()
    user_phrase = "my problem is not resolve by any of your saying please escalte my ticket to human"
    should_esc, priority, reason = escalation_service.check_escalation_triggers(user_phrase, session)
    assert should_esc is True
    assert priority == TicketPriority.HIGH
    assert "human" in reason.lower() or "agent" in reason.lower()


def test_tamil_and_tanglish_escalation_triggers():
    session = session_service.create_session()
    # Tamil
    tamil_phrase = "என் பிரச்சனை சரியாகவில்லை, மனித ஆதரவுக்கு எஸ்கலேட் செய்யவும்"
    should_esc_ta, prio_ta, _ = escalation_service.check_escalation_triggers(tamil_phrase, session)
    assert should_esc_ta is True
    assert prio_ta == TicketPriority.HIGH

    # Tanglish
    tanglish_phrase = "problem solve aagala, human agent kitta escalate pannunga"
    should_esc_tg, prio_tg, _ = escalation_service.check_escalation_triggers(tanglish_phrase, session)
    assert should_esc_tg is True
    assert prio_tg == TicketPriority.HIGH
