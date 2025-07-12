import os
import logging
import yaml
from typing import Dict, Any

from .llm import LLMService
from .tts import TTSService
from .rag import RAGPipeline

logger = logging.getLogger(__name__)

def load_config() -> Dict[str, Any]:
    """Load configuration file from appropriate location."""
    # Try to find config.yaml in various locations
    possible_locations = [
        os.path.join(os.getcwd(), "config.yaml"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.yaml"),
    ]
    
    for location in possible_locations:
        if os.path.exists(location):
            logger.info(f"Found configuration at {location}")
            with open(location) as f:
                return yaml.safe_load(f)
    
    logger.warning("No configuration file found, using defaults")
    return {
        "mistral": {
            "api_key": os.environ.get("MISTRAL_API_KEY", ""),
            "api_url": "https://api.mistral.ai/v1/chat/completions",
            "model": "mistral-large-latest"
        },
        "edge_tts": {
            "output_dir": "audio_output",
            "default_voice": "en-US-AriaNeural",
            "audio_format": "mp3",
            "rate": "+0%",
            "volume": "+0%",
            "voice_options": [
                "en-US-AriaNeural",
                "en-US-GuyNeural",
                "en-GB-SoniaNeural",
                "en-AU-NatashaNeural"
            ]
        },
        "rag": {
            "persist_directory": "data/chroma_db",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "chunk_size": 1000,
            "chunk_overlap": 0
        },
        "answers": {
            "max_duration_sec": 60,
            "silence_threshold": 300,
            "min_answer_length": 10
        },
        "subscription": {
            "free": {"max_questions": 5, "feature_set": "basic"},
            "super": {"max_questions": 10, "feature_set": "standard"},
            "premium": {"max_questions": 15, "feature_set": "advanced"}
        },
        "groq_whisper": {
            "api_key": os.environ.get("GROQ_API_KEY", ""),
            "endpoint": "https://api.groq.com/openai/v1/audio/transcriptions",
            "model": "whisper-large-v3-turbo"
        }
    }

def initialize_services():
    """Initialize and return all required services."""
    config = load_config()
    
    # Create services
    llm_service = LLMService(config["mistral"])
    tts_service = TTSService(config["edge_tts"])
    rag_pipeline = RAGPipeline()
    
    return config, llm_service, tts_service, rag_pipeline
