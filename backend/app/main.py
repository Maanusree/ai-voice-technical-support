"""
Main FastAPI Application Entrypoint
"""
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from .config import settings
from .routes import call_router, knowledge_router, logs_router, ticket_router, telephony_router
from .services import llm_service

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="End-to-end AI Voice Technical Support Agent with Diagnostic Decision Trees, STT, LLM, TTS, and Escalation Routing."
)

# Enable CORS for local testing and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(call_router)
app.include_router(knowledge_router)
app.include_router(logs_router)
app.include_router(ticket_router)
app.include_router(telephony_router)


class SettingsUpdateRequest(BaseModel):
    llm_provider: str
    gemini_key: str = ""
    openai_key: str = ""
    groq_key: str = ""
    edge_voice: str = "en-US-AriaNeural"


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "active_llm_provider": llm_service.provider
    }


@app.get("/api/config")
async def get_config():
    return {
        "agent_name": settings.AGENT_NAME,
        "company": settings.SUPPORT_COMPANY,
        "hotline": settings.SUPPORT_HOTLINE,
        "current_provider": llm_service.provider,
        "edge_voice": settings.EDGE_TTS_VOICE,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "groq_configured": bool(settings.GROQ_API_KEY)
    }


@app.post("/api/config")
async def update_config(req: SettingsUpdateRequest):
    llm_service.set_provider(req.llm_provider)
    if req.gemini_key:
        settings.GEMINI_API_KEY = req.gemini_key
    if req.openai_key:
        settings.OPENAI_API_KEY = req.openai_key
    if req.groq_key:
        settings.GROQ_API_KEY = req.groq_key
    if req.edge_voice:
        settings.EDGE_TTS_VOICE = req.edge_voice

    return {"status": "updated", "provider": llm_service.provider}


# Universal Fallback Route for Telephony Webhooks (Catches any variant)
from .routes.telephony_routes import handle_speech_from_real_phone, handle_incoming_real_call

@app.api_route("/api/telephony/voice-webhook/{session_id}", methods=["GET", "POST"])
@app.api_route("/api/telephony/voice-webhook/{session_id}/", methods=["GET", "POST"])
@app.api_route("/api/telephony/voice-webhook", methods=["GET", "POST"])
@app.api_route("/api/telephony/voice-webhook/", methods=["GET", "POST"])
@app.api_route("/voice-webhook/{session_id}", methods=["GET", "POST"])
@app.api_route("/voice-webhook/{session_id}/", methods=["GET", "POST"])
@app.api_route("/voice-webhook", methods=["GET", "POST"])
@app.api_route("/voice-webhook/", methods=["GET", "POST"])
@app.api_route("/api/voice-webhook/{session_id}", methods=["GET", "POST"])
@app.api_route("/api/voice-webhook", methods=["GET", "POST"])
async def universal_voice_webhook(request: Request, session_id: str = ""):
    return await handle_speech_from_real_phone(request, session_id=session_id)

@app.api_route("/api/telephony/incoming", methods=["GET", "POST"])
@app.api_route("/api/telephony/incoming/", methods=["GET", "POST"])
@app.api_route("/incoming", methods=["GET", "POST"])
@app.api_route("/incoming/", methods=["GET", "POST"])
@app.api_route("/api/incoming", methods=["GET", "POST"])
async def universal_incoming_webhook(request: Request):
    return await handle_incoming_real_call(request)


# Mount Static Frontend
FRONTEND_DIR = settings.PROJECT_ROOT / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🎧</text></svg>"""
        return Response(content=svg_content, media_type="image/svg+xml")
