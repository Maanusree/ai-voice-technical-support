"""
Call Session Manager and Storage Service
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from ..config import settings
from ..models.call_session import CallSession, Turn, CallStatus, ResolutionStatus


class SessionService:
    def __init__(self, logs_dir: Optional[Path] = None):
        self.logs_dir = logs_dir or settings.CALL_LOGS_DIR
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._active_sessions: Dict[str, CallSession] = {}

    def create_session(
        self,
        caller_number: str = "+1-800-555-0199",
        caller_name: str = "Customer"
    ) -> CallSession:
        session = CallSession(
            caller_number=caller_number,
            caller_name=caller_name
        )
        self._active_sessions[session.session_id] = session
        self.save_session(session)
        return session

    def get_session(self, session_id: str) -> Optional[CallSession]:
        # 1. Check in-memory active sessions
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]

        # 2. Check disk storage
        file_path = self.logs_dir / f"{session_id}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                session = CallSession(**data)
                self._active_sessions[session_id] = session
                return session
            except Exception as e:
                print(f"Error loading session {session_id}: {e}")
        return None

    def save_session(self, session: CallSession) -> Path:
        file_path = self.logs_dir / f"{session.session_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(session.model_dump_json(indent=2))
        except Exception as e:
            print(f"Error saving session {session.session_id}: {e}")
        return file_path

    def list_sessions(self, limit: int = 50) -> List[CallSession]:
        sessions = []
        for file in self.logs_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                session = CallSession(**data)
                if len(session.turns) > 0:
                    sessions.append(session)
            except Exception as e:
                print(f"Error loading {file}: {e}")

        sessions.sort(key=lambda s: s.start_time.timestamp() if s.start_time else 0.0, reverse=True)
        return sessions[:limit]

    def get_analytics_summary(self) -> Dict[str, Any]:
        all_sessions = self.list_sessions(limit=500)
        total_calls = len(all_sessions)
        if total_calls == 0:
            return {
                "total_calls": 0,
                "resolved_count": 0,
                "escalated_count": 0,
                "resolution_rate": 0.0,
                "avg_duration_seconds": 0.0,
                "categories": {},
                "sentiment_distribution": {"positive": 0, "neutral": 0, "frustrated": 0, "urgent": 0}
            }

        resolved = sum(1 for s in all_sessions if s.resolution_status == ResolutionStatus.RESOLVED)
        escalated = sum(1 for s in all_sessions if s.resolution_status == ResolutionStatus.ESCALATED)
        total_duration = sum(s.duration_seconds for s in all_sessions)

        categories: Dict[str, int] = {}
        sentiments: Dict[str, int] = {"positive": 0, "neutral": 0, "frustrated": 0, "urgent": 0}

        for s in all_sessions:
            cat = s.issue_category or "General Inquiries"
            categories[cat] = categories.get(cat, 0) + 1
            sent = s.sentiment or "neutral"
            sentiments[sent] = sentiments.get(sent, 0) + 1

        return {
            "total_calls": total_calls,
            "resolved_count": resolved,
            "escalated_count": escalated,
            "resolution_rate": round((resolved / total_calls) * 100, 1) if total_calls > 0 else 0.0,
            "avg_duration_seconds": round(total_duration / total_calls, 1) if total_calls > 0 else 0.0,
            "categories": categories,
            "sentiment_distribution": sentiments
        }


session_service = SessionService()
