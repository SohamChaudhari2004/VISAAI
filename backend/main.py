import asyncio
import json
import logging
import uuid
import os
import time
import io
from typing import Dict, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

from models import (
    VisaType, SubscriptionLevel, VoiceOption, StartInterviewRequest, StartInterviewResponse,
    SubmitAnswerRequest, SubmitAnswerResponse, AnswerEvaluation, InterviewSession
)
from services import initialize_services
from services.asr import transcribe_audio
from services.evaluation import evaluate_answer

# Configure logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
logger = logging.getLogger(__name__)

# Initialize services
config, llm_service, tts_service, rag_pipeline = initialize_services()

# Setup FastAPI
app = FastAPI(title="VISA Interview Training API")

# Create audio output directory
os.makedirs("audio_output", exist_ok=True)
app.mount("/audio", StaticFiles(directory="audio_output"), name="audio")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state
active_sessions: Dict[str, InterviewSession] = {}
active_ws_connections: Dict[str, WebSocket] = {}
session_audio_chunks: Dict[str, List[bytes]] = {}

@app.get("/")
async def root():
    return {"status": "VISA Interview Training API is running"}

@app.get("/api/voices")
async def get_voices() -> List[VoiceOption]:
    try:
        voices = await tts_service.get_available_voices()
        return [
            VoiceOption(
                voice_id=voice.get("ShortName", ""),
                name=voice.get("ShortName", "").split("-")[-1],
                language=voice.get("Locale", "").split("-")[0],
                gender=voice.get("Gender", "")
            ) for voice in voices
        ]
    except Exception as e:
        logger.error(f"Error getting voices: {str(e)}")
        return [
            VoiceOption(
                voice_id=voice,
                name=voice.split("-")[-1],
                language="-".join(voice.split("-")[0:2])
            ) for voice in config["edge_tts"]["voice_options"]
        ]

@app.post("/api/startInterview", response_model=StartInterviewResponse)
async def start_interview(request: StartInterviewRequest):
    try:
        max_questions = config["subscription"][request.subscription_level.value]["max_questions"]
        session_id = str(uuid.uuid4())
        questions = await rag_pipeline.get_questions(visa_type=request.visa_type.value, num_questions=max_questions)
        first_question = questions[0]
        audio_url = await tts_service.synthesize(first_question, request.voice_id)

        active_sessions[session_id] = InterviewSession(
            session_id=session_id,
            visa_type=request.visa_type,
            subscription_level=request.subscription_level,
            voice_id=request.voice_id,
            questions=questions,
            current_question_index=0,
            answers=[],
            evaluations=[]
        )
        session_audio_chunks[session_id] = []

        return StartInterviewResponse(
            session_id=session_id,
            question_text=first_question,
            audio_url=audio_url,
            question_index=1,
            total_questions=max_questions
        )
    except Exception as e:
        logger.error(f"Error starting interview: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start interview")

# Add missing health endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

# Add WebSocket health endpoint
@app.websocket("/ws/health")
async def websocket_health(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()
            await websocket.send_json({"status": "healthy", "timestamp": time.time()})
    except WebSocketDisconnect:
        logger.info("Health WebSocket disconnected")
    except Exception as e:
        logger.error(f"Health WebSocket error: {str(e)}")

# Add missing TTS endpoint
@app.post("/api/tts")
async def text_to_speech(request: dict):
    """Text to speech endpoint"""
    try:
        text = request.get("text", "")
        voice = request.get("voice", config["edge_tts"].get("default_voice", "en-US-AriaNeural"))
        
        audio_url = await tts_service.synthesize(text, voice)
        
        # If synthesize returns a URL path, convert it to a full URL
        if audio_url.startswith("/audio/"):
            return {"audio_url": audio_url}
        else:
            # Return audio data directly
            return StreamingResponse(io.BytesIO(audio_url), media_type="audio/mp3")
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

# Update submit_answer endpoint to handle evaluation results properly
@app.post("/api/submitAnswer", response_model=SubmitAnswerResponse)
async def submit_answer(request: SubmitAnswerRequest):
    if request.session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        session = active_sessions[request.session_id]
        current_idx = session.current_question_index

        # Prevent out-of-range access
        if current_idx >= len(session.questions):
            logger.error(f"Session {request.session_id}: current_question_index {current_idx} out of range for questions length {len(session.questions)}")
            raise HTTPException(status_code=400, detail="No more questions in this session.")

        session.answers.append(request.answer_text)
        current_question = session.questions[current_idx]
        evaluation_result = await evaluate_answer(current_question, request.answer_text, session.visa_type.value)

        # Ensure field names match the AnswerEvaluation model
        if "fluency" in evaluation_result:
            evaluation_result["fluency_score"] = evaluation_result.pop("fluency")
        if "confidence" in evaluation_result:
            evaluation_result["confidence_score"] = evaluation_result.pop("confidence")
        if "content_accuracy" in evaluation_result:
            evaluation_result["content_accuracy_score"] = evaluation_result.pop("content_accuracy")
        if "clarity" in evaluation_result:
            evaluation_result["clarity_score"] = evaluation_result.pop("clarity")
        if "response_time" in evaluation_result:
            evaluation_result["response_time_score"] = evaluation_result.pop("response_time")

        evaluation = AnswerEvaluation(**evaluation_result)
        session.evaluations.append(evaluation)
        session.current_question_index += 1

        # After increment, check if interview is complete
        if session.current_question_index >= len(session.questions):
            final_eval = await session.generate_final_evaluation(llm_service)
            return SubmitAnswerResponse(session_complete=True, last_evaluation=evaluation, final_evaluation=final_eval)

        next_question = session.questions[session.current_question_index]
        audio_url = await tts_service.synthesize(next_question, session.voice_id)
        return SubmitAnswerResponse(
            session_complete=False,
            question_text=next_question,
            audio_url=audio_url,
            question_index=session.current_question_index + 1,
            total_questions=len(session.questions),
            last_evaluation=evaluation
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing answer: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing answer: {str(e)}")

# Update WebSocket stream handling
@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = None
    ping_task = None
    is_recording = False

    try:
        # Ping task to keep connection alive
        async def send_ping():
            try:
                while True:
                    await asyncio.sleep(15)
                    await websocket.send_json({"type": "ping"})
            except Exception:
                pass

        ping_task = asyncio.create_task(send_ping())

        # Wait for initial session_id message
        try:
            msg = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
            session_id = msg.get("session_id")
            if not session_id or session_id not in active_sessions:
                await websocket.send_json({"type": "error", "message": "Invalid session ID"})
                return
            active_ws_connections[session_id] = websocket
            session_audio_chunks[session_id] = []
            await websocket.send_json({"type": "ready", "message": "Connected and ready"})
        except asyncio.TimeoutError:
            await websocket.send_json({"type": "error", "message": "Connection timed out waiting for session ID"})
            return

        # Main message loop
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive(), timeout=60.0)
                if "text" in data:
                    msg = json.loads(data["text"])
                    msg_type = msg.get("type", "")
                    if msg_type == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif msg_type == "end_session":
                        break
                    elif msg_type == "start_recording":
                        session_audio_chunks[session_id] = []
                        is_recording = True
                        await websocket.send_json({"type": "status", "recording": True})
                    elif msg_type == "recording-complete":
                        is_recording = False
                        await websocket.send_json({"type": "status", "recording": False, "processing": True})
                        if session_id in session_audio_chunks and session_audio_chunks[session_id]:
                            full_audio = b"".join(session_audio_chunks[session_id])
                            await process_answer(websocket, session_id, full_audio)
                        else:
                            await websocket.send_json({"type": "error", "message": "No audio received"})
                elif "bytes" in data and is_recording and session_id:
                    session_audio_chunks[session_id].append(data["bytes"])
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket error in message loop: {str(e)}")
                try:
                    await websocket.send_json({"type": "error", "message": "An error occurred processing your request"})
                except:
                    break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.send_json({"type": "error", "message": "An error occurred, please try reconnecting"})
        except:
            pass
    finally:
        if ping_task:
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                pass
        if session_id:
            if session_id in active_ws_connections:
                del active_ws_connections[session_id]
            if session_id in session_audio_chunks:
                session_audio_chunks[session_id] = []

async def process_answer(websocket: WebSocket, session_id: str, audio_data: bytes):
    try:
        session = active_sessions[session_id]
        idx = session.current_question_index
        question = session.questions[idx]
        transcript = await transcribe_audio(audio_data)
        await websocket.send_json({"type": "transcription", "text": transcript})

        # Always pass the transcript to the LLM for evaluation
        eval_result = await evaluate_answer(question, transcript, session.visa_type.value)
        # Ensure field names match
        if "fluency" in eval_result:
            eval_result["fluency_score"] = eval_result.pop("fluency")
        if "confidence" in eval_result:
            eval_result["confidence_score"] = eval_result.pop("confidence")
        if "content_accuracy" in eval_result:
            eval_result["content_accuracy_score"] = eval_result.pop("content_accuracy")
        if "clarity" in eval_result:
            eval_result["clarity_score"] = eval_result.pop("clarity")
        if "response_time" in eval_result:
            eval_result["response_time_score"] = eval_result.pop("response_time")
        evaluation = AnswerEvaluation(**eval_result)
        session.answers.append(transcript)
        session.evaluations.append(evaluation)
        session.current_question_index += 1
        await asyncio.sleep(1)
        if session.current_question_index >= len(session.questions):
            final_eval = await session.generate_final_evaluation(llm_service)
            await websocket.send_json({
                "type": "interview_complete",
                "evaluation": final_eval.dict(),
                "last_evaluation": evaluation.dict()
            })
        else:
            next_q = session.questions[session.current_question_index]
            audio_url = await tts_service.synthesize(next_q, session.voice_id)
            await websocket.send_json({
                "type": "next_question",
                "question_text": next_q,
                "audio_url": audio_url,
                "question_index": session.current_question_index + 1,
                "total_questions": len(session.questions),
                "last_evaluation": evaluation.dict()
            })
    except Exception as e:
        logger.error(f"Error processing answer: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": f"Error processing your answer. Please try again."
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)