"""
End-to-End Multi-Turn Scenario Test Suite
Covers all 5 core technical support conversational flows.
"""
import pytest
from backend.app.services.session_service import session_service
from backend.app.services.llm_service import llm_service
from backend.app.models.call_session import ResolutionStatus, CallStatus


@pytest.mark.asyncio
async def test_scenario_1_wifi_successful_resolution():
    """
    Scenario 1: Customer calls about Wi-Fi -> Agent guides through router lights ->
    Power cycle -> DNS flush -> Issue resolved.
    """
    session = session_service.create_session(caller_number="+1-800-555-0101")
    
    # Turn 1: Problem statement
    turn1 = await llm_service.generate_response(session, "Hi, my wifi is connected but web pages say no internet.")
    session.add_turn("assistant", turn1["text"])
    assert session.diagnostics.scenario_id == "kb_network_wifi"
    assert "router" in turn1["text"].lower() or "light" in turn1["text"].lower()

    # Turn 2: User says light is solid green
    turn2 = await llm_service.generate_response(session, "Yes, the router lights are solid green.")
    session.add_turn("assistant", turn2["text"])
    assert session.diagnostics.current_step_index >= 1

    # Turn 3: User says DNS flush worked and website opened
    turn3 = await llm_service.generate_response(session, "I flushed DNS and the website opened successfully, it's working now!")
    assert turn3["is_resolved"] is True or session.resolution_status == ResolutionStatus.RESOLVED


@pytest.mark.asyncio
async def test_scenario_2_printer_diagnostic_follow_up():
    """
    Scenario 2: Customer calls with printer offline -> Agent asks diagnostic questions ->
    Restarts Print Spooler -> Test page prints -> Resolved.
    """
    session = session_service.create_session(caller_number="+1-800-555-0102")

    # Turn 1: Caller reports printer issue
    turn1 = await llm_service.generate_response(session, "My office printer is offline and print jobs are stuck in queue.")
    session.add_turn("assistant", turn1["text"])
    assert session.diagnostics.scenario_id == "kb_hardware_printer"

    # Turn 2: Caller confirms printer screen is on
    turn2 = await llm_service.generate_response(session, "Yes, the screen is on and shows ready.")
    session.add_turn("assistant", turn2["text"])
    assert "spooler" in turn2["text"].lower() or "services" in turn2["text"].lower()

    # Turn 3: Caller restarted spooler and printed test page
    turn3 = await llm_service.generate_response(session, "Yes, the test page just printed out! Thank you.")
    assert turn3["is_resolved"] is True or session.resolution_status == ResolutionStatus.RESOLVED


@pytest.mark.asyncio
async def test_scenario_3_unclear_noisy_input():
    """
    Scenario 3: Caller provides noisy or unclear input -> Agent asks for clarification
    before proceeding to targeted diagnostic flow.
    """
    session = session_service.create_session(caller_number="+1-800-555-0103")

    # Turn 1: Vague statement
    turn1 = await llm_service.generate_response(session, "uhhh... static noise... it won't work")
    session.add_turn("assistant", turn1["text"])
    assert turn1["intent"] == "clarification_needed"
    assert "understand" in turn1["text"].lower() or "device" in turn1["text"].lower()

    # Turn 2: Caller clarifies they are locked out of their account
    turn2 = await llm_service.generate_response(session, "I mean I am locked out of my corporate account and need a password reset.")
    session.add_turn("assistant", turn2["text"])
    assert session.diagnostics.scenario_id == "kb_account_password"


@pytest.mark.asyncio
async def test_scenario_4_unsupported_out_of_scope():
    """
    Scenario 4: Caller asks completely unsupported out-of-scope question (e.g. cooking recipe)
    -> Agent politely redirects back to technical support domains.
    """
    session = session_service.create_session(caller_number="+1-800-555-0104")

    turn1 = await llm_service.generate_response(session, "Can you tell me how to bake a chocolate cake?")
    session.add_turn("assistant", turn1["text"])
    assert turn1["intent"] == "clarification_needed"
    assert "technical" in turn1["text"].lower() or "trouble" in turn1["text"].lower()


@pytest.mark.asyncio
async def test_scenario_5_critical_hazard_and_supervisor_escalation():
    """
    Scenario 5: Caller reports smoke and burning smell -> Agent immediately issues safety instructions,
    creates CRITICAL tier-2 ticket, and initiates transfer.
    """
    session = session_service.create_session(caller_number="+1-800-555-0105")

    turn1 = await llm_service.generate_response(session, "Help! My computer power unit has smoke and burning smell coming out!")
    assert turn1["should_escalate"] is True
    assert turn1["ticket_id"] is not None
    assert session.status == CallStatus.ESCALATING
    assert session.resolution_status == ResolutionStatus.ESCALATED
