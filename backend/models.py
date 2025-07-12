from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field


class VisaType(str, Enum):
    """Visa type enum"""
    TOURIST = "tourist"
    STUDENT = "student"


class SubscriptionLevel(str, Enum):
    """Subscription level enum"""
    FREE = "free"
    SUPER = "super"
    PREMIUM = "premium"


class VoiceOption(BaseModel):
    """Voice option for TTS"""
    voice_id: str
    name: str
    language: str
    gender: Optional[str] = None


class StartInterviewRequest(BaseModel):
    """Request model for starting a new interview"""
    visa_type: VisaType
    subscription_level: SubscriptionLevel
    voice_id: str


class StartInterviewResponse(BaseModel):
    """Response model for starting a new interview"""
    session_id: str
    question_text: str
    audio_url: str
    question_index: int
    total_questions: int


class SubmitAnswerRequest(BaseModel):
    """Request model for submitting an answer"""
    session_id: str
    answer_text: str


class AnswerEvaluation(BaseModel):
    """Model for answer evaluation metrics"""
    fluency_score: int
    confidence_score: int
    content_accuracy_score: int
    clarity_score: int
    response_time_score: int
    feedback: str = ""


class EvaluationResult(BaseModel):
    """Final evaluation results"""
    overall_score: float = Field(..., ge=0, le=100)
    feedback_summary: str
    detailed_scores: Dict[str, float]
    strengths: List[str]
    areas_to_improve: List[str]


class SubmitAnswerResponse(BaseModel):
    """Response model for submitting an answer"""
    session_complete: bool
    question_text: Optional[str] = None
    audio_url: Optional[str] = None
    question_index: Optional[int] = None
    total_questions: Optional[int] = None
    last_evaluation: Optional[AnswerEvaluation] = None
    final_evaluation: Optional[EvaluationResult] = None


class InterviewSession(BaseModel):
    """Model for storing interview session data"""
    session_id: str
    visa_type: VisaType
    subscription_level: SubscriptionLevel
    voice_id: str
    questions: List[str]
    current_question_index: int = 0
    answers: List[str] = Field(default_factory=list)
    evaluations: List[AnswerEvaluation] = Field(default_factory=list)

    async def generate_final_evaluation(self, llm_service) -> EvaluationResult:
        """
        Generate a final evaluation for this session using the LLM service.

        Args:
            llm_service: The LLM service to use for evaluation

        Returns:
            Final evaluation result
        """
        # Call LLM service to generate comprehensive evaluation
        eval_data = await llm_service.generate_final_evaluation(
            questions=self.questions[:len(self.answers)],
            answers=self.answers,
            visa_type=self.visa_type.value
        )

        # Calculate average scores from individual evaluations if available
        if self.evaluations:
            avg_scores = {
                "fluency": sum(e.fluency_score for e in self.evaluations) / len(self.evaluations),
                "confidence": sum(e.confidence_score for e in self.evaluations) / len(self.evaluations),
                "content_accuracy": sum(e.content_accuracy_score for e in self.evaluations) / len(self.evaluations),
                "clarity": sum(e.clarity_score for e in self.evaluations) / len(self.evaluations),
                "response_time": sum(e.response_time_score for e in self.evaluations) / len(self.evaluations),
            }
        else:
            # Use scores from LLM evaluation if no individual evaluations
            avg_scores = eval_data.get("detailed_scores", {})

        # Create evaluation result
        return EvaluationResult(
            overall_score=eval_data.get("overall_score", 70),
            feedback_summary=eval_data.get("feedback_summary", "Thank you for completing the interview."),
            detailed_scores=avg_scores,
            strengths=eval_data.get("strengths", ["Completed the interview session"]),
            areas_to_improve=eval_data.get("areas_to_improve", ["Continue practicing to improve"]),
        )
