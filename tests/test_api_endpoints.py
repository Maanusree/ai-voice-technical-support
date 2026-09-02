"""
API Endpoint Integration Tests using FastAPI TestClient
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "active_llm_provider" in data


def test_config_endpoint():
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "agent_name" in data
    assert "hotline" in data


def test_knowledge_endpoints():
    res = client.get("/api/knowledge/articles")
    assert res.status_code == 200
    assert len(res.json()["articles"]) >= 5

    res_search = client.get("/api/knowledge/search?q=password")
    assert res_search.status_code == 200
    assert len(res_search.json()["matched_articles"]) > 0


def test_call_lifecycle_endpoints():
    # 1. Start call
    res_start = client.post("/api/calls/start", json={"caller_number": "+1-800-555-7788", "caller_name": "Bob", "generate_audio": False})
    assert res_start.status_code == 200
    session_id = res_start.json()["session_id"]
    assert session_id.startswith("call_")

    # 2. Send message
    res_msg = client.post("/api/calls/message", json={"session_id": session_id, "message": "My internet is down", "generate_audio": False})
    assert res_msg.status_code == 200
    assert "text" in res_msg.json()

    # 3. Get session transcript in logs
    res_logs = client.get(f"/api/logs/sessions/{session_id}")
    assert res_logs.status_code == 200
    assert len(res_logs.json()["turns"]) >= 2

    # 4. Analytics
    res_analytics = client.get("/api/logs/analytics")
    assert res_analytics.status_code == 200
    assert res_analytics.json()["total_calls"] >= 1


def test_telephony_real_call_endpoints():
    # Test Twilio incoming call webhook
    res_incoming = client.post("/api/telephony/incoming", data={"From": "+1-202-555-0143", "CallSid": "CA12345"})
    assert res_incoming.status_code == 200
    assert "<Response>" in res_incoming.text
    assert "<Gather" in res_incoming.text

    # Test Twilio speech processing webhook
    res_speech = client.post("/api/telephony/voice-webhook?session_id=demo_session", data={"SpeechResult": "My Wi-Fi is broken"})
    assert res_speech.status_code == 200
    assert "<Response>" in res_speech.text
    assert "<Say" in res_speech.text
