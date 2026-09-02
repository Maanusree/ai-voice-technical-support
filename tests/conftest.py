"""
Pytest configuration and fixtures.
Ensures test runs use isolated temporary directories so they do not pollute live call logs.
"""
import pytest
from pathlib import Path
from backend.app.config import settings
from backend.app.services.session_service import session_service
from backend.app.services.escalation_service import escalation_service


@pytest.fixture(autouse=True)
def isolate_test_storage(tmp_path: Path):
    """Isolates session and ticket storage during unit test runs."""
    test_logs_dir = tmp_path / "call_logs"
    test_tickets_dir = tmp_path / "tickets"
    test_logs_dir.mkdir(parents=True, exist_ok=True)
    test_tickets_dir.mkdir(parents=True, exist_ok=True)

    original_logs_dir = settings.CALL_LOGS_DIR
    original_tickets_dir = settings.TICKETS_DIR

    settings.CALL_LOGS_DIR = test_logs_dir
    settings.TICKETS_DIR = test_tickets_dir
    session_service.logs_dir = test_logs_dir
    escalation_service.tickets_dir = test_tickets_dir

    yield

    # Restore
    settings.CALL_LOGS_DIR = original_logs_dir
    settings.TICKETS_DIR = original_tickets_dir
    session_service.logs_dir = original_logs_dir
    escalation_service.tickets_dir = original_tickets_dir
