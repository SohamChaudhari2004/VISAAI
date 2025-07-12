import logging
import json
import re
from typing import Dict, Any, List

from models import AnswerEvaluation, EvaluationResult
from services.llm import LLMService

logger = logging.getLogger(__name__)

class EvaluatorService:
    """Service for evaluating interview answers"""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.confidence_markers = {
            "positive": [
                "certainly", "definitely", "absolutely", "without doubt", 
                "i am confident", "i am sure", "i know", "clearly"
            ],
            "negative": [
                "i think", "maybe", "perhaps", "i guess", "sort of", "kind of",
                "i'm not sure", "possibly", "probably", "i believe", "um", "uh"
            ]
        }

    async def evaluate_answer(self, question: str, answer: str) -> AnswerEvaluation:
        """Evaluate a single answer"""
        try:
            # Create evaluation prompt
            prompt = f"""
            Please evaluate this visa interview answer. The question was: "{question}"
            
            The applicant's answer was: "{answer}"
            
            Evaluate based on the following criteria:
            - Fluency: How smoothly and naturally they speak (0-100)
            - Confidence: How self-assured they appear (0-100)
            - Content Accuracy: How factually correct and appropriate the answer is (0-100)
            - Clarity: How clear and understandable the answer is (0-100)
            - Response Time: How quickly they were able to formulate an answer (0-100)
            
            Also provide an overall score (0-100) and brief feedback with suggestions for improvement.
            
            Return your evaluation as a JSON object with these exact keys: 
            fluency_score, confidence_score, content_accuracy_score, clarity_score, response_time_score, overall_score, feedback
            """
            
            system_message = "You are an expert visa interview evaluator. Provide fair and constructive feedback."
            
            # Get LLM response
            llm_response = await self.llm_service.generate_completion(
                prompt=prompt,
                system_message=system_message,
                temperature=0.3  # Lower temperature for more consistent evaluations
            )
            
            # Parse response as JSON
            try:
                eval_data = json.loads(llm_response)
                
                # Create and return evaluation object
                return AnswerEvaluation(
                    fluency_score=eval_data.get("fluency_score", 50),
                    confidence_score=eval_data.get("confidence_score", 50),
                    content_accuracy_score=eval_data.get("content_accuracy_score", 50),
                    clarity_score=eval_data.get("clarity_score", 50),
                    response_time_score=eval_data.get("response_time_score", 50),
                    overall_score=eval_data.get("overall_score", 50),
                    feedback=eval_data.get("feedback", "No specific feedback available.")
                )
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {llm_response}")
                # Return default evaluation if parsing fails
                return AnswerEvaluation(
                    fluency_score=50,
                    confidence_score=50,
                    content_accuracy_score=50,
                    clarity_score=50,
                    response_time_score=50,
                    overall_score=50,
                    feedback="Unable to generate specific feedback. Please try again."
                )
                
        except Exception as e:
            logger.error(f"Error evaluating answer: {e}")
            # Return default evaluation if any error occurs
            return AnswerEvaluation(
                fluency_score=50,
                confidence_score=50,
                content_accuracy_score=50,
                clarity_score=50,
                response_time_score=50,
                overall_score=50,
                feedback="An error occurred during evaluation."
            )

    async def generate_final_evaluation(
        self, 
        questions: List[str], 
        answers: List[str],
        evaluations: List[AnswerEvaluation]
    ) -> EvaluationResult:
        """Generate a final evaluation for the entire interview"""
        try:
            # Calculate average scores
            avg_scores = {
                "fluency": sum(e.fluency_score for e in evaluations) / len(evaluations),
                "confidence": sum(e.confidence_score for e in evaluations) / len(evaluations),
                "content_accuracy": sum(e.content_accuracy_score for e in evaluations) / len(evaluations),
                "clarity": sum(e.clarity_score for e in evaluations) / len(evaluations),
                "response_time": sum(e.response_time_score for e in evaluations) / len(evaluations)
            }
            
            overall_score = sum(avg_scores.values()) / len(avg_scores)
            
            # Format Q&A for LLM prompt
            qa_text = ""
            for i in range(min(len(questions), len(answers))):
                qa_text += f"Q{i+1}: {questions[i]}\nA{i+1}: {answers[i]}\n\n"
            
            # Create final evaluation prompt
            prompt = f"""
            Please provide a comprehensive evaluation of this visa interview. 
            
            Here are the questions and answers:
            {qa_text}
            
            Average scores in different areas:
            - Fluency: {avg_scores['fluency']:.1f}/100
            - Confidence: {avg_scores['confidence']:.1f}/100
            - Content Accuracy: {avg_scores['content_accuracy']:.1f}/100
            - Clarity: {avg_scores['clarity']:.1f}/100
            - Response Time: {avg_scores['response_time']:.1f}/100
            
            Please provide:
            1. A summary feedback paragraph (3-5 sentences)
            2. 2-3 specific strengths
            3. 2-3 specific areas to improve
            
            Return your evaluation as a JSON object with these exact keys:
            feedback_summary, strengths (array), areas_to_improve (array)
            """
            
            system_message = "You are an expert visa interview evaluator providing a final assessment. Be constructive and specific."
            
            # Get LLM response
            llm_response = await self.llm_service.generate_completion(
                prompt=prompt,
                system_message=system_message,
                temperature=0.4
            )
            
            # Parse response
            try:
                eval_data = json.loads(llm_response)
                
                return EvaluationResult(
                    overall_score=overall_score,
                    feedback_summary=eval_data.get("feedback_summary", ""),
                    detailed_scores=avg_scores,
                    strengths=eval_data.get("strengths", ["Good attempt at the interview."]),
                    areas_to_improve=eval_data.get("areas_to_improve", ["Practice more for improvement."])
                )
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse final evaluation JSON: {llm_response}")
                # Return default final evaluation
                return EvaluationResult(
                    overall_score=overall_score,
                    feedback_summary="Overall, you've completed the interview with some good responses.",
                    detailed_scores=avg_scores,
                    strengths=["Completed all questions"],
                    areas_to_improve=["Continue practicing to improve further"]
                )
                
        except Exception as e:
            logger.error(f"Error generating final evaluation: {e}")
            # Return default evaluation if any error occurs
            return EvaluationResult(
                overall_score=60,
                feedback_summary="Thank you for completing the interview session.",
                detailed_scores={
                    "fluency": 60,
                    "confidence": 60,
                    "content_accuracy": 60,
                    "clarity": 60,
                    "response_time": 60
                },
                strengths=["Completed the interview session"],
                areas_to_improve=["Continue practicing"]
            )

    def evaluate_fluency(self, text: str) -> float:
        """
        Evaluate fluency based on text characteristics.
        
        Args:
            text: The answer text
            
        Returns:
            Fluency score (0-100)
        """
        if not text or len(text) < 10:
            return 30.0
            
        # Count words
        words = text.split()
        word_count = len(words)
        
        # Count fillers
        fillers = ["um", "uh", "like", "you know", "so", "well"]
        filler_count = sum(text.lower().count(filler) for filler in fillers)
        
        # Detect incomplete sentences
        sentences = re.split(r'[.!?]+', text)
        incomplete_sentences = sum(1 for s in sentences if s.strip() and len(s.split()) < 3)
        
        # Calculate base score - longer answers generally indicate better fluency
        base_score = min(80, max(40, 40 + (word_count / 10)))
        
        # Adjust for fillers
        filler_ratio = filler_count / max(1, word_count)
        filler_penalty = filler_ratio * 50
        
        # Adjust for incomplete sentences
        incomplete_ratio = incomplete_sentences / max(1, len(sentences))
        incomplete_penalty = incomplete_ratio * 30
        
        # Calculate final score
        fluency_score = base_score - filler_penalty - incomplete_penalty
        
        return max(10, min(100, fluency_score))
    
    def evaluate_confidence(self, text: str) -> float:
        """
        Evaluate confidence based on word choice and expression.
        
        Args:
            text: The answer text
            
        Returns:
            Confidence score (0-100)
        """
        if not text:
            return 0
        
        text_lower = text.lower()
        
        # Count confidence markers
        positive_markers = sum(text_lower.count(marker) for marker in self.confidence_markers["positive"])
        negative_markers = sum(text_lower.count(marker) for marker in self.confidence_markers["negative"])
        
        # Count words
        word_count = len(text.split())
        if word_count == 0:
            return 50
        
        # Calculate ratios
        positive_ratio = positive_markers / max(1, word_count) * 10
        negative_ratio = negative_markers / max(1, word_count) * 10
        
        # Base confidence score (65 is average)
        confidence_score = 65 + (positive_ratio * 50) - (negative_ratio * 30)
        
        # Adjust for answer length - very short answers suggest low confidence
        if word_count < 10:
            confidence_score -= (10 - word_count) * 3
        
        return max(10, min(100, confidence_score))
    
    def calculate_response_time_score(self, response_time_sec: float) -> float:
        """
        Calculate score based on response time.
        
        Args:
            response_time_sec: Time taken to respond in seconds
            
        Returns:
            Response time score (0-100)
        """
        # Ideal response time is 2-10 seconds
        # Too quick might mean not enough thought
        # Too slow might mean hesitation
        
        if response_time_sec < 1.0:
            return 60  # Too quick
        elif response_time_sec < 2.0:
            return 80  # Fast but acceptable
        elif response_time_sec <= 8.0:
            return 100 - ((response_time_sec - 2.0) * 3)  # Optimal range
        elif response_time_sec <= 15.0:
            return 85 - ((response_time_sec - 8.0) * 5)  # Getting slow
        else:
            return max(30, 50 - ((response_time_sec - 15.0) * 2))  # Too slow
