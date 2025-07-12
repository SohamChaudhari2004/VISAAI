import io
from gtts import gTTS
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydub import AudioSegment
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/synthesize")
async def synthesize_speech(text: str, voice_name: str = "en-US-Standard-A"):
    try:
        audio_io = io.BytesIO()
        tts = gTTS(text=text, lang="en", slow=False)
        tts.write_to_fp(audio_io)
        audio_io.seek(0)
        
        return StreamingResponse(audio_io, media_type="audio/mpeg")
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        raise HTTPException(status_code=500, detail="TTS synthesis error")