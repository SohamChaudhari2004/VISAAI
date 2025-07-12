import os
import asyncio
import logging
import tempfile
import aiohttp
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class STTService:
    """Service for speech-to-text using Groq's Whisper API"""

    def __init__(self, config: Dict[str, Any]):
        self.api_key = config["api_key"]
        self.endpoint = config["endpoint"]
        self.model = "large-v3-turbo"  # Default Whisper model

    async def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio data to text"""
        try:
            # Save audio data to temporary file
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            # Set up headers for API request
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Prepare the form data with audio file
            form_data = aiohttp.FormData()
            form_data.add_field(
                name="file",
                value=open(temp_path, "rb"),
                filename="audio.webm",
                content_type="audio/webm"
            )
            form_data.add_field(name="model", value=self.model)
            
            # Make API request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.endpoint,
                    headers=headers,
                    data=form_data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"STT API error: {error_text}")
                        return "Sorry, I couldn't transcribe that. Please try again."
                    
                    result = await response.json()
                    
            # Clean up the temporary file
            os.unlink(temp_path)
            
            # Extract and return the transcription
            return result.get("text", "")
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return "An error occurred during transcription."
