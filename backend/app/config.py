"""
Application Configuration and Settings
"""
import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent
DATA_DIR = BASE_DIR / "data"
CALL_LOGS_DIR = DATA_DIR / "call_logs"
TICKETS_DIR = DATA_DIR / "tickets"
KB_PATH = DATA_DIR / "knowledge_base.json"

# Load environment variables from .env file
load_dotenv(PROJECT_ROOT / ".env", override=True)

# Ensure runtime directories exist
CALL_LOGS_DIR.mkdir(parents=True, exist_ok=True)
TICKETS_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseModel):
    # App Settings
    APP_NAME: str = "AI Voice Technical Support Agent"
    APP_VERSION: str = "1.0.0"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")

    # Storage Paths
    PROJECT_ROOT: Path = PROJECT_ROOT
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = DATA_DIR
    CALL_LOGS_DIR: Path = CALL_LOGS_DIR
    TICKETS_DIR: Path = TICKETS_DIR
    KB_PATH: Path = KB_PATH

    # AI & LLM Providers
    # Provider options: "auto", "offline", "gemini", "openai", "groq"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # TTS Settings
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "edge")  # "edge", "web_speech", "openai"
    EDGE_TTS_VOICE: str = os.getenv("EDGE_TTS_VOICE", "en-US-AriaNeural")  # high quality, natural voice

    # Support Phone Agent Details
    AGENT_NAME: str = "Maanu"
    SUPPORT_COMPANY: str = "InnoAssist"
    SUPPORT_HOTLINE: str = "+1 903 532 2035"

    # Twilio Live Telephony Settings
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "+19035322035")
    VERIFIED_DESTINATION_NUMBER: str = os.getenv("VERIFIED_DESTINATION_NUMBER", "+917418214150")
    NGROK_PUBLIC_URL: str = os.getenv("NGROK_PUBLIC_URL", "https://snooze-prominent-overvalue.ngrok-free.dev")


settings = Settings()
