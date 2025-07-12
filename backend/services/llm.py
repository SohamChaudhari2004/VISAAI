import logging
import os
from typing import List, Dict, Any, Optional
import yaml
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_mistralai import ChatMistralAI
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field  # Changed from langchain_core.pydantic_v1

logger = logging.getLogger(__name__)

class EvaluationSchema(BaseModel):
    overall_score: int = Field(description="Overall score from 0 to 100")
    feedback_summary: str = Field(description="General feedback paragraph")
    detailed_scores: Dict[str, int] = Field(description="Scores for fluency, confidence, content_accuracy, clarity, and response_time")
    strengths: List[str] = Field(description="2-3 specific strengths")
    areas_to_improve: List[str] = Field(description="2-3 specific improvement areas")

class LLMService:
    """Service for interacting with LLM APIs (Mistral) using LangChain"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the LLM service with configuration"""
        self.api_key = os.environ.get("MISTRAL_API_KEY", config.get("api_key", ""))
        self.api_url = config.get("api_url", "https://api.mistral.ai/v1/chat/completions")
        self.model = config.get("model", "mistral-large-latest")
        self.max_tokens = config.get("max_tokens", 1024)

        # Initialize LangChain chat model
        if self.api_key:
            self.chat_model = ChatMistralAI(
                model=self.model,
                mistral_api_key=self.api_key,
                max_tokens=self.max_tokens
            )
        else:
            logger.warning("No Mistral API key provided. LLM functionality will be limited.")
            self.chat_model = None

    async def generate_completion(
        self,
        prompt: str,
        system_message: str = "You are a helpful assistant.",
        temperature: float = 0.7
    ) -> str:
        """
        Generate a completion using the Mistral API via LangChain.

        Args:
            prompt: The user prompt text
            system_message: The system message to guide the model's behavior
            temperature: Temperature for generation (0.0 - 1.0)

        Returns:
            Generated text response
        """
        if not self.chat_model:
            logger.error("Cannot generate completion: No API key provided")
            return "API key not configured. Please check configuration."

        try:
            # Create chat template
            chat_template = ChatPromptTemplate.from_messages([
                ("system", system_message),
                ("human", prompt)
            ])

            # Create chain
            chain = chat_template | self.chat_model

            # Invoke the chain
            response = await chain.ainvoke({})

            if isinstance(response, str):
                return response
            else:
                # Handle potential dictionary output
                return response.content if hasattr(response, 'content') else str(response)

        except Exception as e:
            logger.error(f"LLM completion error: {str(e)}")
            return f"Error generating response: {str(e)}"

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7
    ) -> str:
        """
        Generate a response using a list of messages.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Temperature for generation (0.0 - 1.0)

        Returns:
            Generated text response
        """
        if not self.chat_model:
            logger.error("Cannot generate response: No API key provided")
            return "API key not configured. Please check configuration."

        try:
            # Format messages for LangChain
            formatted_messages = []
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                if role == "system":
                    formatted_messages.append(("system", content))
                elif role == "user":
                    formatted_messages.append(("human", content))
                elif role == "assistant":
                    formatted_messages.append(("ai", content))
                else:
                    formatted_messages.append(("human", content))

            # Create chat template
            chat_template = ChatPromptTemplate.from_messages(formatted_messages)

            # Create and invoke chain
            chain = chat_template | self.chat_model.with_temperature(temperature)
            response = await chain.ainvoke({})

            return response.content

        except Exception as e:
            logger.error(f"LLM response error: {str(e)}")
            return f"Error generating response: {str(e)}"

    async def generate_final_evaluation(
        self,
        questions: List[str],
        answers: List[str],
        visa_type: str
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive final evaluation of the interview using LangChain.

        Args:
            questions: List of all questions asked
            answers: List of all transcribed answers
            visa_type: Type of visa (tourist or student)

        Returns:
            Dictionary containing evaluation metrics and feedback
        """
        # Format the Q&A for the prompt
        qa_pairs = ""
        for i, (q, a) in enumerate(zip(questions, answers)):
            qa_pairs += f"Question {i+1}: {q}\n"
            qa_pairs += f"Answer {i+1}: {a}\n\n"

        prompt = f"""
        You are an expert visa interview evaluator. Please provide a comprehensive evaluation
        of this {visa_type} visa interview:

        {qa_pairs}

        Evaluate the interview on the following aspects:
        1. Overall performance
        2. Communication skills (fluency, clarity)
        3. Content accuracy and relevance
        4. Confidence and presentation
        5. Areas of strength
        6. Areas needing improvement
        """

        system_message = "You are an expert visa interview evaluator providing detailed, constructive feedback."

        try:
            # Setup the parser
            parser = JsonOutputParser(pydantic_object=EvaluationSchema)

            # Build the chain
            chain = (
                ChatPromptTemplate.from_messages([
                    ("system", system_message),
                    ("human", prompt + "\n\n" + parser.get_format_instructions())
                ])
                | self.chat_model.with_temperature(0.4)
                | parser
            )

            # Execute the chain
            result = await chain.ainvoke({})

            # Ensure all required fields are present and properly formatted
            if not isinstance(result, dict):
                result = result.dict()

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse final evaluation JSON: {str(e)}")
            # Return default evaluation
            return {
                "overall_score": 70,
                "feedback_summary": "Thank you for completing the visa interview practice session.",
                "detailed_scores": {
                    "fluency": 70,
                    "confidence": 70,
                    "content_accuracy": 70,
                    "clarity": 70,
                    "response_time": 70
                },
                "strengths": ["Completed all questions in the interview"],
                "areas_to_improve": ["Continue practicing to improve your responses"]
            }

        except Exception as e:
            logger.error(f"Error generating final evaluation: {str(e)}")
            # Return default evaluation
            return {
                "overall_score": 65,
                "feedback_summary": "An error occurred during evaluation. Thank you for your participation.",
                "detailed_scores": {
                    "fluency": 65,
                    "confidence": 65,
                    "content_accuracy": 65,
                    "clarity": 65,
                    "response_time": 65
                },
                "strengths": ["Completed the interview session"],
                "areas_to_improve": ["Technical issues prevented detailed feedback"]
            }
