from logging import config
import os
import logging
import asyncio
import tempfile
import uuid
from typing import Dict, Any

import edge_tts



logger = logging.getLogger(__name__)

class TTSService:
    """Service for converting text to speech using Microsoft Edge TTS"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the TTS service with configuration"""
        self.output_dir = config.get("output_dir", "audio_output")
        self.default_voice = config.get("default_voice", "en-US-AriaNeural")
        self.audio_format = config.get("audio_format", "mp3")
        self.rate = config.get("rate", "+0%")
        self.volume = config.get("volume", "+0%")
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
    async def synthesize(self, text: str, voice_id: str = None) -> str:
        """
        Convert text to speech using Edge TTS.
        
        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use for synthesis
            
        Returns:
            URL path to the generated audio file
        """
        try:
            # Use provided voice or default
            voice = voice_id or self.default_voice
            
            # Generate unique filename
            filename = f"{uuid.uuid4()}.{self.audio_format}"
            filepath = os.path.join(self.output_dir, filename)
            
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Clean up text for TTS
            text = text.strip()
            if not text:
                text = "No text provided."
            
            # Use Edge TTS to generate audio
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(filepath)
            
            # Return URL path
            url_path = f"/audio/{filename}"
            logger.info(f"Generated audio: {url_path}")
            
            return url_path
            
        except Exception as e:
            logger.error(f"TTS error: {str(e)}")
            
            # Return a default error audio path
            return "/audio/error.mp3"
    
    async def get_available_voices(self) -> list:
        """
        Get list of available TTS voices.
        
        Returns:
            List of voice objects
        """
        try:
            voices = await edge_tts.list_voices()
            logger.info(f"Found {len(voices)} available voices")
            return voices
        except Exception as e:
            logger.error(f"Error listing voices: {str(e)}")
            return []

# Example usage
if __name__ == "__main__":
    async def main():
        service = TTSService(config)
        # List voices
        voices = await service.get_available_voices()
        print(f"Found {len(voices)} voices")
        
        # Generate speech
        output = await service.synthesize(
            "Hello! This is a test of the Edge TTS system.",
            "en-US-AriaNeural"
        )
        print(f"Generated speech: {output[:50]}...")
        
    asyncio.run(main())
                