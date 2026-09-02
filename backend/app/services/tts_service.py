"""
Text-to-Speech (TTS) Service with Multi-Language & Tamil (தமிழ்) Support
"""
import os
import io
import asyncio
import base64
from typing import Optional, Tuple
import edge_tts
from ..config import settings


def contains_tamil(text: str) -> bool:
    """Checks if text contains Tamil Unicode characters."""
    return any('\u0B80' <= char <= '\u0BFF' for char in text)


class TTSService:
    def __init__(self, voice: Optional[str] = None):
        self.voice = voice or settings.EDGE_TTS_VOICE

    def select_voice_for_text(self, text: str, requested_voice: Optional[str] = None) -> str:
        if requested_voice:
            return requested_voice
        if contains_tamil(text):
            return "ta-IN-PallaviNeural"  # High quality Tamil neural voice
        return self.voice

    async def synthesize_to_bytes(self, text: str, voice: Optional[str] = None) -> bytes:
        """
        Synthesize text into MP3 audio bytes using Edge-TTS neural engine.
        Automatically uses Tamil neural voice when Tamil text is provided.
        """
        selected_voice = self.select_voice_for_text(text, voice)
        communicate = edge_tts.Communicate(text, selected_voice)
        audio_stream = io.BytesIO()

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])

        return audio_stream.getvalue()

    async def synthesize_to_base64(self, text: str, voice: Optional[str] = None) -> str:
        """
        Returns base64 encoded audio string ready for WebSocket JSON transmission.
        """
        try:
            audio_bytes = await self.synthesize_to_bytes(text, voice)
            return base64.b64encode(audio_bytes).decode("utf-8")
        except Exception as e:
            print(f"Edge-TTS synthesis error: {e}")
            return ""


tts_service = TTSService()
