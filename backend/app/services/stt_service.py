"""
Speech-to-Text (STT) Service for Audio Ingestion
"""
import io
import os
import time
from typing import Optional, Dict, Any
from ..config import settings


class STTService:
    def __init__(self):
        self.openai_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        self.groq_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")

    async def transcribe_audio_bytes(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Transcribes audio bytes using Groq Whisper or OpenAI Whisper if configured.
        """
        start_time = time.time()

        # 1. Try Groq Whisper (Ultra-fast)
        if self.groq_key:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=self.groq_key, base_url="https://api.groq.com/openai/v1")
                audio_file = io.BytesIO(audio_bytes)
                audio_file.name = filename
                transcription = await client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=audio_file,
                    language=language
                )
                latency_ms = (time.time() - start_time) * 1000
                return {
                    "text": transcription.text.strip(),
                    "confidence": 0.98,
                    "latency_ms": latency_ms,
                    "provider": "groq_whisper"
                }
            except Exception as e:
                print(f"Groq Whisper transcription failed: {e}")

        # 2. Try OpenAI Whisper
        if self.openai_key:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=self.openai_key)
                audio_file = io.BytesIO(audio_bytes)
                audio_file.name = filename
                transcription = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language
                )
                latency_ms = (time.time() - start_time) * 1000
                return {
                    "text": transcription.text.strip(),
                    "confidence": 0.98,
                    "latency_ms": latency_ms,
                    "provider": "openai_whisper"
                }
            except Exception as e:
                print(f"OpenAI Whisper transcription failed: {e}")

        # Fallback response for unconfigured server audio
        latency_ms = (time.time() - start_time) * 1000
        return {
            "text": "",
            "confidence": 0.0,
            "latency_ms": latency_ms,
            "provider": "client_speech_api_recommended",
            "error": "Server STT requires OPENAI_API_KEY or GROQ_API_KEY. Client Web Speech API is active."
        }


stt_service = STTService()
