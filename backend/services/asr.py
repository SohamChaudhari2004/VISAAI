import logging
import os
import tempfile
from typing import Dict, Any, Optional
import asyncio
import httpx
import yaml

logger = logging.getLogger(__name__)

# Load configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
if os.path.exists(config_path):
    with open(config_path) as f:
        config = yaml.safe_load(f)
else:
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.yaml")
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        config = {"groq_whisper": {"api_key": "", "endpoint": "https://api.groq.com/openai/v1/audio/transcriptions"}}

# Get the API key and endpoint from config
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", config["groq_whisper"].get("api_key", ""))
GROQ_ENDPOINT = config["groq_whisper"].get("endpoint", "https://api.groq.com/openai/v1/audio/transcriptions")


async def transcribe_audio(audio_data: bytes, model: str = "whisper-large-v3", language: Optional[str] = None) -> str:
    """
    Transcribe audio data using Groq's Whisper API.
    
    Args:
        audio_data: Raw audio bytes to transcribe
        model: Model name to use
        language: Optional language code
        
    Returns:
        Transcribed text
    """
    logger.info(f"Transcribing audio of size {len(audio_data)} bytes")
    temp_file_path = None
    
    try:
        # Check for valid audio data
        if not audio_data or len(audio_data) < 1000:  # Minimum meaningful audio size
            logger.warning("Audio data too small to transcribe")
            return "Audio too short to transcribe."
        
        # Create a unique temporary file name
        temp_file_path = os.path.join(tempfile.gettempdir(), f"{os.urandom(8).hex()}.webm")
        
        # Write audio data to the temporary file
        with open(temp_file_path, "wb") as f:
            f.write(audio_data)
        
        # Prepare the headers with authentication
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}"
        }
        
        # Make the API request with retry mechanism
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Open the file in a new context for each request attempt
                with open(temp_file_path, 'rb') as audio_file:
                    files = {
                        'file': ('audio.webm', audio_file, 'audio/webm')
                    }
                    
                    # Additional parameters
                    data = {
                        'model': model, 
                        'response_format': 'json'
                    }
                    
                    if language:
                        data['language'] = language
                    
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            GROQ_ENDPOINT,
                            headers=headers,
                            files=files,
                            data=data
                        )
                
                # Break the loop if successful
                break
            except Exception as e:
                retry_count += 1
                logger.warning(f"Transcription retry {retry_count}/{max_retries}: {str(e)}")
                if retry_count >= max_retries:
                    raise
                await asyncio.sleep(1)  # Wait before retry
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            transcript = result.get('text', '')
            
            # Trim and clean up transcript
            transcript = transcript.strip()
            
            logger.info(f"Transcription successful: {transcript[:50]}...")
            return transcript
        else:
            logger.error(f"Error in transcription API: {response.status_code} - {response.text}")
            return f"Error transcribing audio (HTTP {response.status_code})."
    
    except Exception as e:
        logger.error(f"Exception during transcription: {str(e)}")
        return "Error processing audio."
    finally:
        # Clean up the temporary file in the finally block
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {str(e)}")


async def transcribe_file(
    audio_path: str,
    model: str = "large-v3-turbo",
    language: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transcribe audio file using Groq's Whisper API.
    
    Args:
        audio_path: Path to audio file
        model: Whisper model to use
        language: Optional language code
    
    Returns:
        Dict containing transcription and metadata
    """
    try:
        # Read audio file
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        
        # Transcribe audio
        transcription = await transcribe_audio(audio_data, model, language)
        
        return {
            "text": transcription,
            "model": model,
            "success": bool(transcription),
        }
        
    except Exception as e:
        logger.error(f"Error transcribing file: {e}")
        return {
            "text": "",
            "error": str(e),
            "success": False,
        }

