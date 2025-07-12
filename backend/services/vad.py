# import logging
# import asyncio
# import io
# from typing import Tuple, Optional, List
# import numpy as np
# import webrtcvad

# logger = logging.getLogger(__name__)

# # Initialize WebRTC VAD
# vad = webrtcvad.Vad(3)  # Aggressiveness level 3 (most aggressive)

# # Keep track of silence frames
# silence_counter = 0
# speech_detected = False

# async def process_audio_with_vad(
#     audio_chunk: bytes, 
#     silence_threshold: int = 300  # Number of silent frames to consider end of speech
# ) -> Tuple[Optional[bytes], bool]:
#     """
#     Process audio chunk with Voice Activity Detection.
    
#     Args:
#         audio_chunk: Raw audio bytes
#         silence_threshold: Number of silent frames to consider end of speech
        
#     Returns:
#         Tuple of (processed audio chunk, is_speech_ended)
#     """
#     global silence_counter, speech_detected
    
#     try:
#         # WebRTC VAD requires:
#         # - 16-bit PCM audio
#         # - Sample rate must be 8000, 16000, 32000 or 48000 Hz
#         # - Frame duration must be 10, 20 or 30 ms
#         # 
#         # For simplicity, we'll assume the incoming audio is already in the right format
#         # In a production app, we'd convert the audio to the correct format
        
#         # Check if this is speech
#         frame_duration_ms = 30  # We'll use 30ms frames
#         is_speech = False
        
#         # WebRTC VAD only accepts specific frame sizes
#         samples_per_frame = int(16000 * (frame_duration_ms / 1000.0))
        
#         # If the chunk is of sufficient length, check for speech
#         if len(audio_chunk) >= samples_per_frame * 2:  # 2 bytes per sample for 16-bit audio
#             try:
#                 is_speech = vad.is_speech(audio_chunk[:samples_per_frame*2], 16000)
#             except Exception as e:
#                 logger.warning(f"VAD error: {str(e)}")
#                 is_speech = True  # Default to assuming speech on error
#         else:
#             # If the chunk is too small, we'll just pass it through
#             is_speech = True
        
#         # Update counters
#         if is_speech:
#             silence_counter = 0
#             speech_detected = True
#         else:
#             silence_counter += 1
        
#         # Determine if speech has ended
#         speech_ended = speech_detected and silence_counter >= silence_threshold
        
#         if speech_ended:
#             # Reset for next detection
#             silence_counter = 0
#             speech_detected = False
            
#         return audio_chunk, speech_ended
        
#     except Exception as e:
#         logger.error(f"VAD processing error: {str(e)}")
#         return audio_chunk, False

# async def detect_speech_end(audio_chunks: List[bytes], frame_duration_ms: int = 30) -> bool:
#     """
#     Detect end of speech in a sequence of audio chunks.
    
#     Args:
#         audio_chunks: List of audio chunks
#         frame_duration_ms: Frame duration in milliseconds
        
#     Returns:
#         True if speech has ended, False otherwise
#     """
#     if not audio_chunks:
#         return False
    
#     silence_count = 0
#     samples_per_frame = int(16000 * (frame_duration_ms / 1000.0))
    
#     # Check the last few chunks for silence
#     check_chunks = audio_chunks[-10:] if len(audio_chunks) > 10 else audio_chunks
    
#     for chunk in check_chunks:
#         if len(chunk) >= samples_per_frame * 2:
#             try:
#                 is_speech = vad.is_speech(chunk[:samples_per_frame*2], 16000)
#                 if not is_speech:
#                     silence_count += 1
#             except:
#                 # On error, assume it's speech
#                 pass
    
#     # If we have several consecutive silent chunks, speech has ended
#     return silence_count >= 5  # Adjust threshold as needed

import logging
import numpy as np
import webrtcvad
from typing import Tuple

logger = logging.getLogger(__name__)

# Initialize WebRTC VAD
vad = webrtcvad.Vad(3)  # Aggressiveness level 3 (most aggressive)

# Global state variables
silence_counter = 0
speech_detected = False

async def process_audio_with_vad(
    audio_chunk: bytes, 
    silence_threshold: int = 300
) -> Tuple[bytes, bool]:
    """
    Process audio chunk with Voice Activity Detection.
    
    Args:
        audio_chunk: Raw audio bytes
        silence_threshold: Number of silent frames to consider end of speech
        
    Returns:
        Tuple of (processed audio chunk, is_speech_ended)
    """
    global silence_counter, speech_detected
    
    try:
        # WebRTC VAD requires specific frame sizes
        frame_duration_ms = 30  # We'll use 30ms frames
        is_speech = False
        
        # Calculate samples per frame (16kHz * 30ms = 480 samples)
        # 16-bit audio means 2 bytes per sample = 960 bytes per frame
        samples_per_frame = int(16000 * (frame_duration_ms / 1000.0))
        bytes_per_frame = samples_per_frame * 2
        
        if len(audio_chunk) >= bytes_per_frame:
            try:
                # Just check first frame for speech
                is_speech = vad.is_speech(audio_chunk[:bytes_per_frame], 16000)
            except Exception as e:
                logger.warning(f"VAD error: {str(e)}")
                is_speech = True  # Default to assuming speech on error
        else:
            # If chunk is too small, assume it's not speech
            is_speech = False
        
        # Update counters
        if is_speech:
            silence_counter = 0
            speech_detected = True
        else:
            silence_counter += 1
        
        # Speech ends after some silence following detected speech
        speech_ended = speech_detected and silence_counter >= silence_threshold
        
        if speech_ended:
            # Reset for next detection
            silence_counter = 0
            speech_detected = False
        
        return audio_chunk, speech_ended
        
    except Exception as e:
        logger.error(f"VAD processing error: {str(e)}")
        return audio_chunk, False  # Return original chunk with no speech end