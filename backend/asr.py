import os
import tempfile
import uuid
from your_transcription_client import Client  # Adjust this import based on your actual client
import logging

logger = logging.getLogger(__name__)
_client = Client()  # Initialize your client here

async def transcribe_audio(audio_data: bytes):
    temp_file = None
    try:
        # Create a unique temporary file
        temp_filename = f"temp_audio_{uuid.uuid4()}.webm"
        temp_path = os.path.join(tempfile.gettempdir(), temp_filename)
        
        # Write data to file
        with open(temp_path, "wb") as f:
            f.write(audio_data)
        
        # Keep track of the file
        temp_file = temp_path
        
        # Transcribe using your API
        result = await _client.transcribe(temp_path)
        
        # Return the transcription
        return result.text
    except Exception as e:
        logger.error(f"Exception during transcription: {str(e)}")
        return ""
    finally:
        # Ensure file is closed and deleted
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Could not delete temporary file {temp_file}: {str(e)}")