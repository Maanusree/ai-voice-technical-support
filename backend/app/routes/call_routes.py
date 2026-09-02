"""
Call Lifecycle, Voice Message, and WebSocket Streaming Routes
"""
import time
import json
import base64
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Response
from pydantic import BaseModel

from ..models.call_session import CallSession, CallStatus, ResolutionStatus
from ..services.session_service import session_service
from ..services.llm_service import llm_service
from ..services.tts_service import tts_service
from ..services.stt_service import stt_service
from ..config import settings

router = APIRouter(prefix="/api/calls", tags=["Call Management"])


class StartCallRequest(BaseModel):
    caller_number: Optional[str] = "+1-800-555-0199"
    caller_name: Optional[str] = "Valued Customer"
    generate_audio: Optional[bool] = True


class MessageRequest(BaseModel):
    session_id: str
    message: str
    generate_audio: Optional[bool] = True
    stt_latency_ms: Optional[float] = 0.0


class SynthesizeRequest(BaseModel):
    text: str
    voice: Optional[str] = None


@router.post("/start")
async def start_call(req: StartCallRequest):
    """
    Initializes a new phone call session and returns agent greeting.
    """
    session = session_service.create_session(
        caller_number=req.caller_number or "+1-800-555-0199",
        caller_name=req.caller_name or "Customer"
    )
    session.call_type = "Website (Browser Voice)"

    greeting_text = (
        f"Thank you for calling {settings.SUPPORT_COMPANY}. "
        f"My name is {settings.AGENT_NAME}, your AI technical support specialist. "
        f"How can I help you today?"
    )

    audio_base64 = ""
    tts_latency = 0.0
    if req.generate_audio:
        tts_start = time.time()
        audio_base64 = await tts_service.synthesize_to_base64(greeting_text)
        tts_latency = (time.time() - tts_start) * 1000

    session.add_turn(
        role="assistant",
        text=greeting_text,
        latency_ms={"tts": tts_latency}
    )
    session_service.save_session(session)

    return {
        "session_id": session.session_id,
        "status": session.status,
        "greeting": greeting_text,
        "audio_base64": audio_base64,
        "caller_name": session.caller_name,
        "caller_number": session.caller_number
    }


@router.post("/message")
async def process_voice_message(req: MessageRequest):
    """
    Processes a caller's spoken input, reasons via AI/LLM, and returns natural voice response.
    """
    session = session_service.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Call session not found")

    if session.status == CallStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Call session has ended")

    # Record User turn
    session.add_turn(
        role="user",
        text=req.message,
        latency_ms={"stt": req.stt_latency_ms or 0.0}
    )

    # Generate AI Response
    ai_result = await llm_service.generate_response(session, req.message)
    response_text = ai_result["text"]

    # Generate TTS audio if requested
    audio_base64 = ""
    tts_latency = 0.0
    if req.generate_audio:
        tts_start = time.time()
        audio_base64 = await tts_service.synthesize_to_base64(response_text)
        tts_latency = (time.time() - tts_start) * 1000

    # Record Assistant turn
    session.add_turn(
        role="assistant",
        text=response_text,
        latency_ms={
            "llm": ai_result.get("latency_ms", 0.0),
            "tts": tts_latency
        },
        intent=ai_result.get("intent")
    )

    session_service.save_session(session)

    return {
        "session_id": session.session_id,
        "text": response_text,
        "audio_base64": audio_base64,
        "intent": ai_result.get("intent"),
        "should_escalate": ai_result.get("should_escalate", False),
        "ticket_id": ai_result.get("ticket_id"),
        "is_resolved": ai_result.get("is_resolved", False),
        "status": session.status,
        "resolution_status": session.resolution_status,
        "latency": {
            "stt_ms": req.stt_latency_ms or 0.0,
            "llm_ms": ai_result.get("latency_ms", 0.0),
            "tts_ms": tts_latency,
            "total_ms": (req.stt_latency_ms or 0.0) + ai_result.get("latency_ms", 0.0) + tts_latency
        }
    }


@router.post("/end")
async def end_call(session_id: str = Form(...), resolution: str = Form("resolved")):
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Call session not found")

    res_enum = ResolutionStatus.RESOLVED if resolution == "resolved" else ResolutionStatus.DROPPED
    session.end_call(resolution=res_enum)
    session_service.save_session(session)
    return {"status": "ended", "duration_seconds": session.duration_seconds, "resolution": session.resolution_status}


@router.post("/transcribe")
async def transcribe_audio_file(file: UploadFile = File(...)):
    """Transcribes an uploaded audio file via STT engine."""
    audio_bytes = await file.read()
    result = await stt_service.transcribe_audio_bytes(audio_bytes, filename=file.filename)
    return result


@router.post("/synthesize")
async def synthesize_text(req: SynthesizeRequest):
    """Directly synthesizes text to MP3 audio bytes."""
    audio_bytes = await tts_service.synthesize_to_bytes(req.text, req.voice)
    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.websocket("/ws/stream")
async def call_websocket_stream(websocket: WebSocket):
    """
    Real-time WebSocket endpoint for continuous voice turn streaming and events.
    """
    await websocket.accept()
    current_session: Optional[CallSession] = None

    try:
        while True:
            raw_data = await websocket.receive_text()
            event = json.loads(raw_data)
            action = event.get("action")

            if action == "init":
                caller_num = event.get("caller_number", "+1-800-555-0199")
                caller_name = event.get("caller_name", "Customer")
                current_session = session_service.create_session(caller_num, caller_name)
                
                greeting = f"Thank you for calling ApexCloud Support. My name is Alex. How may I assist you with your technical issue today?"
                audio_b64 = await tts_service.synthesize_to_base64(greeting)

                current_session.add_turn(role="assistant", text=greeting)
                session_service.save_session(current_session)

                await websocket.send_json({
                    "event": "call_connected",
                    "session_id": current_session.session_id,
                    "text": greeting,
                    "audio_base64": audio_b64
                })

            elif action == "user_utterance":
                session_id = event.get("session_id")
                user_text = event.get("text", "").strip()
                stt_latency = event.get("stt_latency_ms", 0.0)

                session = session_service.get_session(session_id) or current_session
                if not session or not user_text:
                    continue

                # Notify client that agent is thinking
                await websocket.send_json({"event": "agent_thinking"})

                session.add_turn(role="user", text=user_text, latency_ms={"stt": stt_latency})

                ai_res = await llm_service.generate_response(session, user_text)
                resp_text = ai_res["text"]

                tts_start = time.time()
                audio_b64 = await tts_service.synthesize_to_base64(resp_text)
                tts_latency = (time.time() - tts_start) * 1000

                session.add_turn(
                    role="assistant",
                    text=resp_text,
                    latency_ms={"llm": ai_res.get("latency_ms", 0.0), "tts": tts_latency},
                    intent=ai_res.get("intent")
                )
                session_service.save_session(session)

                await websocket.send_json({
                    "event": "agent_response",
                    "text": resp_text,
                    "audio_base64": audio_b64,
                    "intent": ai_res.get("intent"),
                    "should_escalate": ai_res.get("should_escalate", False),
                    "ticket_id": ai_res.get("ticket_id"),
                    "is_resolved": ai_res.get("is_resolved", False),
                    "latency": {
                        "stt_ms": stt_latency,
                        "llm_ms": ai_res.get("latency_ms", 0.0),
                        "tts_ms": tts_latency
                    }
                })

            elif action == "hangup":
                session_id = event.get("session_id")
                session = session_service.get_session(session_id) or current_session
                if session:
                    session.end_call(resolution=ResolutionStatus.DROPPED)
                    session_service.save_session(session)
                await websocket.send_json({"event": "call_ended"})
                break

    except WebSocketDisconnect:
        if current_session and current_session.status != CallStatus.COMPLETED:
            current_session.end_call(resolution=ResolutionStatus.DROPPED)
            session_service.save_session(current_session)
    except Exception as e:
        print(f"WebSocket session error: {e}")
