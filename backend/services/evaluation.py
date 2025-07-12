import os
import logging
import re
import json
from typing import Dict, Any, Optional
import yaml

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_mistralai import ChatMistralAI

logger = logging.getLogger(__name__)

# Load configuration
try:
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)
except Exception as e:
    logger.error(f"Failed to load config: {e}")
    config = {"mistral": {"api_key": "", "model": "mistral-large-latest"}}

# Define evaluation schema
class AnswerEvaluationSchema(BaseModel):
    fluency_score: int = Field(description="Fluency score from 0 to 100", ge=0, le=100)
    confidence_score: int = Field(description="Confidence score from 0 to 100", ge=0, le=100)
    content_accuracy_score: int = Field(description="Content accuracy score from 0 to 100", ge=0, le=100)
    clarity_score: int = Field(description="Clarity score from 0 to 100", ge=0, le=100)
    response_time_score: int = Field(description="Response time score from 0 to 100", ge=0, le=100)
    overall_score: int = Field(description="Overall score from 0 to 100", ge=0, le=100)
    feedback: str = Field(description="Constructive feedback on the answer")

async def evaluate_answer(question: str, answer: str, visa_type: str, response_time: Optional[float] = None) -> Dict[str, Any]:
    """
    Evaluate a user's answer to a visa interview question using LangChain.

    Args:
        question: The interview question
        answer: User's transcribed answer
        visa_type: Type of visa (tourist or student)
        response_time: Time taken to respond (in seconds)

    Returns:
        Dictionary with evaluation metrics
    """
    logger.info(f"Evaluating answer for question: {question}")

    # If the answer is too short, give low scores
    if not answer or len(answer.strip()) < 10:
        logger.warning("Answer too short, returning low scores")
        return {
            "fluency_score": 30,
            "confidence_score": 30,
            "content_accuracy_score": 20,
            "clarity_score": 25,
            "response_time_score": 40,
            "overall_score": 30,
            "feedback": "Your answer was too short. Try to provide more detailed responses to interview questions."
        }

    # Initialize the LangChain model
    api_key = os.environ.get("MISTRAL_API_KEY", config["mistral"].get("api_key", ""))
    model_name = config["mistral"].get("model", "mistral-large-latest")
    
    if not api_key:
        logger.warning("No Mistral API key, using fallback evaluation")
        return fallback_evaluation()

    try:
        # Create the ChatMistralAI model
        model = ChatMistralAI(
            mistral_api_key=api_key,
            model=model_name,
            temperature=0.2
        )
        
        # Create the parser
        parser = JsonOutputParser(pydantic_object=AnswerEvaluationSchema)
        
        # Prepare prompt for LLM-based evaluation - Fixed the template issues
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful visa interview evaluator assistant."),
            ("human", f"""
            You are evaluating a response to a {visa_type} visa interview question.
            
            Question: "{question}"
            Answer: "{answer}"
            
            Please evaluate this response on the following criteria on a scale of 1-100:
            
            1. Fluency (How smoothly and naturally the response flows)
            2. Confidence (How confident the applicant appears based on word choice)
            3. Content Accuracy (How well the response addresses the question)
            4. Clarity (How clear and understandable the response is)
            5. Response Time (How quickly and effectively the candidate responded)
            
            Also provide brief, constructive feedback on how the answer could be improved.
            
            {parser.get_format_instructions()}
            """)
        ])
        
        # Execute the chain
        chain = prompt | model | parser
        
        # Execute the chain
        evaluation = await chain.ainvoke({})
        
        # Convert to dictionary if needed
        if not isinstance(evaluation, dict):
            evaluation = evaluation.dict()
            
        logger.info(f"Evaluation successful: Overall score {evaluation['overall_score']}")
        return evaluation

    except Exception as e:
        logger.error(f"Error in evaluation: {str(e)}")
        return fallback_evaluation()

def fallback_evaluation() -> Dict[str, Any]:
    """Provide a fallback evaluation when LLM fails."""
    return {
        "fluency_score": 60,
        "confidence_score": 60,
        "content_accuracy_score": 50,
        "clarity_score": 60,
        "response_time_score": 50,
        "overall_score": 55,
        "feedback": "Your answer addressed the question, but try to provide more specific details and speak more confidently."
    }