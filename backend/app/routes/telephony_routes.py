"""
Real-Phone Telephony Integration Routes (Twilio / SIP Voice Gateway)
Enables live telephone calls from real mobile numbers / landlines.
"""
from typing import Optional, Dict, Any
import html
import base64
import urllib.request
import urllib.parse
import json
import os
import re
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import JSONResponse

from ..services.session_service import session_service
from ..services.llm_service import llm_service
from ..models.call_session import ResolutionStatus, CallStatus
from ..config import settings

router = APIRouter(prefix="/api/telephony", tags=["Telephony (Real Phone)"])


def xml_clean(text: str) -> str:
    """Strip markdown symbols and properly escape XML characters for TwiML."""
    if not text:
        return ""
    clean = text.replace("**", "").replace("*", "").replace("#", "").replace("`", "").replace("\n", " ").strip()
    return html.escape(clean)


def build_say_tag(text: str, session_lang: str = "en") -> str:
    """Constructs a <Say> tag with appropriate voice and language tag (Tamil or English)."""
    cleaned = xml_clean(text)
    is_tamil = any('\u0B80' <= c <= '\u0BFF' for c in text) or session_lang in ("ta", "ta-IN")
    if is_tamil:
        return f'<Say language="ta-IN">{cleaned}</Say>'
    else:
        return f'<Say voice="alice" language="en-US">{cleaned}</Say>'


def build_gather_twiml(action_url: str, main_message: str, retry_message: str, session_lang: str = "en") -> str:
    """Builds a complete, well-formed TwiML response with speech gathering."""
    say_main = build_say_tag(main_message, session_lang)
    say_retry = build_say_tag(retry_message, session_lang)
    hints = "wifi, router, internet, printer, blinking, red, green, power, cable, password, tamil, human, agent, escalation, slow, freeze, error, yes, no, ok"
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    {say_main}
    <Gather input="speech dtmf" speechModel="phone_call" hints="{hints}" action="{action_url}" method="POST" speechTimeout="auto" timeout="8">
    </Gather>
    {say_retry}
    <Gather input="speech dtmf" speechModel="phone_call" hints="{hints}" action="{action_url}" method="POST" speechTimeout="auto" timeout="6">
    </Gather>
</Response>"""


@router.api_route("/incoming", methods=["GET", "POST"])
@router.api_route("/incoming/", methods=["GET", "POST"])
async def handle_incoming_real_call(request: Request):
    """
    Twilio Voice Webhook: Triggered when a customer calls a real phone number.
    Accepts both GET and POST requests from Twilio.
    """
    try:
        caller_from = "+1-555-000-0000"
        try:
            if request.method == "POST":
                form = await request.form()
                caller_from = form.get("From", caller_from)
            else:
                caller_from = request.query_params.get("From", caller_from)
        except Exception:
            pass

        session = session_service.create_session(
            caller_number=caller_from,
            caller_name="Mobile Caller"
        )
        session.call_type = "Phone (Twilio PSTN)"

        greeting_text = (
            f"Thank you for calling {settings.SUPPORT_COMPANY}. "
            f"My name is {settings.AGENT_NAME}, your AI technical support specialist. "
            f"Please describe your technical issue, and I will help you fix it."
        )

        session.add_turn(role="assistant", text=greeting_text)
        session_service.save_session(session)

        webhook_base = settings.NGROK_PUBLIC_URL.rstrip('/') or "https://snooze-prominent-overvalue.ngrok-free.dev"
        action_url = f"{webhook_base}/api/telephony/voice-webhook/{session.session_id}"

        retry_text = "I did not catch that. Please describe what you are seeing or the issue you are facing."
        twiml_response = build_gather_twiml(action_url, greeting_text, retry_text, session.language)
        return Response(content=twiml_response, media_type="application/xml")

    except Exception as e:
        print(f"Error handling incoming call: {e}")
        fallback_msg = f"Thank you for calling {settings.SUPPORT_COMPANY}. Please describe your technical issue."
        fallback_twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="en-US">{xml_clean(fallback_msg)}</Say>
    <Gather input="speech dtmf" speechModel="phone_call" action="https://snooze-prominent-overvalue.ngrok-free.dev/api/telephony/voice-webhook" method="POST" speechTimeout="auto" timeout="8">
    </Gather>
</Response>"""
        return Response(content=fallback_twiml, media_type="application/xml")


@router.api_route("/voice-webhook", methods=["GET", "POST"])
@router.api_route("/voice-webhook/", methods=["GET", "POST"])
@router.api_route("/voice-webhook/{session_id}", methods=["GET", "POST"])
@router.api_route("/voice-webhook/{session_id}/", methods=["GET", "POST"])
async def handle_speech_from_real_phone(request: Request, session_id: Optional[str] = None):
    """
    Processes speech transcribed from the caller's real phone microphone.
    Applies diagnostic reasoning and responds back through the phone speaker.
    Guaranteed to return valid 200 OK TwiML in all scenarios.
    """
    try:
        caller_text = "Hello, I need technical support."
        call_sid = ""
        form_sid = ""

        try:
            if request.method == "POST":
                form = await request.form()
                caller_text = form.get("SpeechResult", form.get("speech_result", caller_text))
                call_sid = form.get("CallSid", "")
                form_sid = form.get("session_id", "")
            else:
                caller_text = request.query_params.get("SpeechResult", caller_text)
                call_sid = request.query_params.get("CallSid", "")
                form_sid = request.query_params.get("session_id", "")
        except Exception:
            pass

        # Resolve session ID from path, form, query, or CallSid
        query_sid = session_id or request.path_params.get("session_id") or form_sid or request.query_params.get("session_id")
        
        session = None
        if query_sid:
            session = session_service.get_session(query_sid)

        if not session:
            # Create session on the fly for incoming call
            session = session_service.create_session(caller_name="Mobile Customer")
            session.call_type = "Phone (Twilio PSTN)"

        session.add_turn(role="user", text=caller_text, latency_ms={"stt": 150.0})

        # AI Diagnostic Reasoning
        ai_result = await llm_service.generate_response(session, caller_text)
        response_text = ai_result["text"]
        should_escalate = ai_result.get("should_escalate", False)

        session.add_turn(
            role="assistant",
            text=response_text,
            latency_ms={"llm": ai_result.get("latency_ms", 10.0)},
            intent=ai_result.get("intent")
        )
        session_service.save_session(session)

        webhook_base = settings.NGROK_PUBLIC_URL.rstrip('/') or "https://snooze-prominent-overvalue.ngrok-free.dev"
        action_url = f"{webhook_base}/api/telephony/voice-webhook/{session.session_id}"
        lang = getattr(session, "language", "en")

        # 1. If issue is escalated to human support
        if should_escalate:
            ticket_id = ai_result.get("ticket_id", "TICK-LIVE")
            say_response = build_say_tag(response_text, lang)
            if lang in ("ta", "ta-IN") or any('\u0B80' <= c <= '\u0BFF' for c in response_text):
                say_transfer = f'<Say language="ta-IN">உங்கள் டிக்கெட் எண் {ticket_id}. தயவுசெய்து இணைப்பில் காத்திருக்கவும்.</Say>'
                say_hold = '<Say language="ta-IN">எங்கள் சீனியர் தொழில்நுட்ப நிபுணர் இப்போது இணைகிறார்.</Say>'
            else:
                say_transfer = f'<Say voice="alice" language="en-US">Transferring your call to our Tier 2 Support Specialist under reference number {ticket_id}. Please hold.</Say>'
                say_hold = '<Say voice="alice" language="en-US">Thank you for your patience. A live specialist is now connecting.</Say>'

            twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    {say_response}
    {say_transfer}
    <Pause length="2"/>
    {say_hold}
</Response>"""
            return Response(content=twiml_response, media_type="application/xml")

        # 2. If issue is confirmed resolved
        if ai_result.get("is_resolved", False):
            say_response = build_say_tag(response_text, lang)
            if lang in ("ta", "ta-IN") or any('\u0B80' <= c <= '\u0BFF' for c in response_text):
                say_bye = f'<Say language="ta-IN">{settings.SUPPORT_COMPANY} அழைத்தமைக்கு நன்றி. வணக்கம்!</Say>'
            else:
                say_bye = f'<Say voice="alice" language="en-US">Thank you for calling {settings.SUPPORT_COMPANY}. Goodbye!</Say>'

            twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    {say_response}
    {say_bye}
    <Hangup/>
</Response>"""
            return Response(content=twiml_response, media_type="application/xml")

        # 3. Standard conversational diagnostic follow-up turn
        if lang in ("ta", "ta-IN") or any('\u0B80' <= c <= '\u0BFF' for c in response_text):
            retry_text = "இணைப்பில் இருக்கிறீர்களா? உங்கள் திரையில் அல்லது சாதனத்தில் என்ன காண்கிறீர்கள் என்று கூறுங்கள்."
        else:
            retry_text = "Are you still on the line? Please let me know what you see or what happened."

        twiml_response = build_gather_twiml(action_url, response_text, retry_text, lang)
        return Response(content=twiml_response, media_type="application/xml")

    except Exception as e:
        print(f"Error handling voice webhook: {e}")
        safe_msg = "I am listening. Please describe your technical issue, and I will assist you right away."
        fallback_twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="en-US">{xml_clean(safe_msg)}</Say>
    <Gather input="speech dtmf" speechModel="phone_call" action="https://snooze-prominent-overvalue.ngrok-free.dev/api/telephony/voice-webhook" method="POST" speechTimeout="auto" timeout="8">
    </Gather>
</Response>"""
        return Response(content=fallback_twiml, media_type="application/xml")


@router.api_route("/status-callback", methods=["GET", "POST"])
async def telephony_status_callback(request: Request, session_id: Optional[str] = None):
    """Logs real phone call duration and status when caller hangs up."""
    try:
        query_sid = session_id or request.query_params.get("session_id")
        if query_sid:
            session = session_service.get_session(query_sid)
            if session:
                session.end_call(resolution=ResolutionStatus.RESOLVED)
                session_service.save_session(session)
    except Exception:
        pass
    return {"status": "recorded"}




class OutboundCallRequest(BaseModel):
    account_sid: Optional[str] = None
    auth_token: Optional[str] = None
    to_phone: Optional[str] = None
    from_phone: Optional[str] = None
    ngrok_url: Optional[str] = None


@router.post("/trigger-call")
async def trigger_real_phone_call(req: Optional[OutboundCallRequest] = None):
    """
    Triggers an outbound phone call from Twilio to the user's verified phone number.
    When the user answers, Maanu greets them and starts the AI voice technical support.
    """
    from dotenv import dotenv_values
    env_vals = dotenv_values(settings.PROJECT_ROOT / ".env")

    sid = (req and req.account_sid and req.account_sid.strip()) or env_vals.get("TWILIO_ACCOUNT_SID") or settings.TWILIO_ACCOUNT_SID or os.getenv("TWILIO_ACCOUNT_SID", "")
    token = (req and req.auth_token and req.auth_token.strip()) or env_vals.get("TWILIO_AUTH_TOKEN") or settings.TWILIO_AUTH_TOKEN or os.getenv("TWILIO_AUTH_TOKEN", "")
    to_num = (req and req.to_phone and req.to_phone.strip()) or env_vals.get("VERIFIED_DESTINATION_NUMBER") or settings.VERIFIED_DESTINATION_NUMBER or os.getenv("VERIFIED_DESTINATION_NUMBER", "+917418214150")
    from_num = (req and req.from_phone and req.from_phone.strip()) or env_vals.get("TWILIO_PHONE_NUMBER") or settings.TWILIO_PHONE_NUMBER or os.getenv("TWILIO_PHONE_NUMBER", "+19035322035")
    webhook_url = (req and req.ngrok_url and req.ngrok_url.strip()) or env_vals.get("NGROK_PUBLIC_URL") or settings.NGROK_PUBLIC_URL or os.getenv("NGROK_PUBLIC_URL", "https://snooze-prominent-overvalue.ngrok-free.dev")

    if not sid or not token:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Twilio Account SID or Auth Token is missing. Please enter them in the AI Settings tab or in your .env file."
            }
        )

    # Clean strings
    sid = sid.strip()
    token = token.strip()
    to_num = to_num.strip()
    from_num = from_num.strip()
    webhook_url = webhook_url.strip()

    # Save to active settings for future calls
    settings.TWILIO_ACCOUNT_SID = sid
    settings.TWILIO_AUTH_TOKEN = token
    settings.TWILIO_PHONE_NUMBER = from_num
    settings.VERIFIED_DESTINATION_NUMBER = to_num
    settings.NGROK_PUBLIC_URL = webhook_url

    # Create session directly for outbound call
    session = session_service.create_session(
        caller_number=to_num,
        caller_name="Mobile Customer"
    )
    session.call_type = "Phone (Twilio PSTN)"
    greeting_text = (
        f"Thank you for calling {settings.SUPPORT_COMPANY}. "
        f"My name is {settings.AGENT_NAME}, your AI technical support specialist. "
        f"Please describe your technical issue, and I will help you fix it."
    )
    session.add_turn(role="assistant", text=greeting_text)
    session_service.save_session(session)

    action_url = f"{webhook_url.rstrip('/')}/api/telephony/voice-webhook/{session.session_id}"
    retry_text = "I did not catch that. Please describe what you are seeing or the issue you are facing."
    initial_twiml = build_gather_twiml(action_url, greeting_text, retry_text, session.language)

    # Make standard REST call to Twilio API with embedded TwiML
    twilio_api_url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"

    post_data = urllib.parse.urlencode({
        "To": to_num,
        "From": from_num,
        "Twiml": initial_twiml
    }).encode("utf-8")

    auth_str = f"{sid}:{token}"
    b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

    twilio_req = urllib.request.Request(twilio_api_url, data=post_data, headers={
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    })

    try:
        with urllib.request.urlopen(twilio_req) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            return {
                "status": "success",
                "message": f"Calling {to_num} from {from_num}! Your phone will ring in a few seconds.",
                "call_sid": res_json.get("sid"),
                "call_status": res_json.get("status")
            }
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        try:
            err_json = json.loads(err_msg)
            return JSONResponse(status_code=400, content={"status": "error", "message": err_json.get("message", err_msg)})
        except Exception:
            return JSONResponse(status_code=400, content={"status": "error", "message": err_msg})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
