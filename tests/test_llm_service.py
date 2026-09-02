"""
Tests for LLM Service and Built-in Diagnostic Reasoning Engine
"""
import pytest
from backend.app.services.session_service import session_service
from backend.app.services.llm_service import llm_service
from backend.app.models.call_session import ResolutionStatus


@pytest.mark.asyncio
async def test_offline_engine_scenario_initiation():
    session = session_service.create_session()
    
    # User reports Wi-Fi issue
    res = await llm_service.generate_response(session, "My Wi-Fi is not connecting to the internet")
    assert res["scenario_id"] == "kb_network_wifi"
    assert "router" in res["text"].lower() or "light" in res["text"].lower()
    assert res["should_escalate"] is False


@pytest.mark.asyncio
async def test_offline_engine_clarification_on_vague_input():
    session = session_service.create_session()
    
    res = await llm_service.generate_response(session, "hello, something weird happened")
    assert res["intent"] == "clarification_needed"
    assert "understand" in res["text"].lower() or "device" in res["text"].lower()


@pytest.mark.asyncio
async def test_offline_engine_hazard_escalation():
    session = session_service.create_session()
    
    res = await llm_service.generate_response(session, "I see sparks and burning smell coming from the outlet!")
    assert res["should_escalate"] is True
    assert res["ticket_id"] is not None
    assert "ticket" in res["text"].lower() or "transfer" in res["text"].lower()
