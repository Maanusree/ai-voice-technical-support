"""
Call History, Conversation Transcripts, and Analytics Routes
"""
import io
import csv
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Response
from ..services.session_service import session_service

router = APIRouter(prefix="/api/logs", tags=["Logs & Analytics"])


@router.get("/sessions")
async def get_call_sessions(limit: int = Query(50, ge=1, le=200)):
    """List recent call sessions with overview metadata."""
    sessions = session_service.list_sessions(limit=limit)
    return {"sessions": sessions}


@router.get("/latest")
async def get_latest_session():
    """Returns the most recent call session and turns for live HUD sync."""
    sessions = session_service.list_sessions(limit=1)
    if not sessions:
        return {"session": None}
    return {"session": sessions[0]}


@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str):
    """Get complete call details including turn-by-turn multi-turn transcript and metrics."""
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Call session not found")
    return session


@router.get("/analytics")
async def get_analytics_metrics():
    """Returns aggregated call analytics (resolution rate, average duration, sentiment breakdown)."""
    return session_service.get_analytics_summary()


@router.get("/export/csv")
async def export_logs_csv():
    """Exports all call detail records (CDR) as a CSV file."""
    sessions = session_service.list_sessions(limit=500)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Session ID", "Caller Number", "Caller Name", "Start Time", "Duration (s)",
        "Category", "Resolution Status", "Sentiment", "Turns Count", "Escalation Ticket ID"
    ])

    for s in sessions:
        writer.writerow([
            s.session_id,
            s.caller_number,
            s.caller_name or "Customer",
            s.start_time.isoformat() if s.start_time else "",
            s.duration_seconds,
            s.issue_category or "General",
            s.resolution_status.value if s.resolution_status else "in_progress",
            s.sentiment or "neutral",
            len(s.turns),
            s.escalation_ticket_id or ""
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=call_records.csv"}
    )
