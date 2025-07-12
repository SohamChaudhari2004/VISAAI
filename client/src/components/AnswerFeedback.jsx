import React from "react";
import "./AnswerFeedback.css";

const getScoreColor = (score) => {
  if (score >= 80) return "#4CAF50"; // Green for high scores
  if (score >= 50) return "#FFC107"; // Yellow for medium scores
  return "#F44336"; // Red for low scores
};

const formatScore = (score) => {
  return `${Math.round(score)}%`;
};

const AnswerFeedback = ({ answer, evaluation, onContinue }) => {
  return (
    <div className="answer-feedback">
      <div className="answer-text">
        <h3>Your Answer (Transcribed)</h3>
        <p className="transcription">{answer || "No speech detected."}</p>
      </div>

      <div className="feedback-scores">
        <div className="score-item">
          <div className="score-label">Fluency</div>
          <div
            className="score-value"
            style={{ color: getScoreColor(evaluation.fluency_score) }}
          >
            {formatScore(evaluation.fluency_score)}
          </div>
        </div>
        <div className="score-item">
          <div className="score-label">Confidence</div>
          <div
            className="score-value"
            style={{ color: getScoreColor(evaluation.confidence_score) }}
          >
            {formatScore(evaluation.confidence_score)}
          </div>
        </div>
        <div className="score-item">
          <div className="score-label">Content Accuracy</div>
          <div
            className="score-value"
            style={{ color: getScoreColor(evaluation.content_accuracy_score) }}
          >
            {formatScore(evaluation.content_accuracy_score)}
          </div>
        </div>
        <div className="score-item">
          <div className="score-label">Clarity</div>
          <div
            className="score-value"
            style={{ color: getScoreColor(evaluation.clarity_score) }}
          >
            {formatScore(evaluation.clarity_score)}
          </div>
        </div>
        <div className="score-item">
          <div className="score-label">Response Time</div>
          <div
            className="score-value"
            style={{ color: getScoreColor(evaluation.response_time_score) }}
          >
            {formatScore(evaluation.response_time_score)}
          </div>
        </div>
        <div className="score-item overall">
          <div className="score-label">Overall Score</div>
          <div
            className="score-value"
            style={{ color: getScoreColor(evaluation.overall_score) }}
          >
            {formatScore(evaluation.overall_score)}
          </div>
        </div>
      </div>

      <div className="feedback-text">
        <h4>Feedback:</h4>
        <p>{evaluation.feedback || "No feedback available"}</p>
      </div>

      <div className="feedback-actions">
        <button
          type="button"
          className="continue-button"
          onClick={onContinue}
        >
          Continue to Next Question
        </button>
      </div>
    </div>
  );
};

export default AnswerFeedback;
