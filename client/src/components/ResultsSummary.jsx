import React from "react";
import "./ResultsSummary.css";

const ResultsSummary = ({ results, questions, answers, onReset }) => {
  if (
    !results ||
    typeof results !== "object" ||
    results.overall_score === undefined
  ) {
    return (
      <div className="results-summary">
        <h2>Interview Results</h2>
        <div className="error-message">
          <p>Results are not available or incomplete. Please try again.</p>
          <button className="reset-button" onClick={onReset}>
            Start New Interview
          </button>
        </div>
      </div>
    );
  }

  const { overall_score, metrics, feedback } = results;

  // Format score as percentage
  const scorePercentage = Math.round(overall_score * 100);

  // Determine score color class
  const getScoreColorClass = (score) => {
    if (score >= 0.8) return "score-high";
    if (score >= 0.6) return "score-medium";
    return "score-low";
  };

  return (
    <div className="results-summary">
      <h2>Interview Results</h2>

      <div className="overall-score">
        <h3>Overall Score</h3>
        <div className={`score-display ${getScoreColorClass(overall_score)}`}>
          {scorePercentage}%
        </div>
      </div>

      <div className="metrics-section">
        <h3>Performance Metrics</h3>
        <div className="metrics-grid">
          {Object.entries(metrics).map(([metric, score]) => (
            <div key={metric} className="metric-item">
              <div className="metric-name">
                {metric
                  .split("_")
                  .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
                  .join(" ")}
              </div>
              <div className={`metric-score ${getScoreColorClass(score)}`}>
                {Math.round(score * 100)}%
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="feedback-section">
        <h3>Feedback</h3>
        <div className="feedback-content">
          {feedback.map((item, index) => (
            <p key={index}>{item}</p>
          ))}
        </div>
      </div>

      <div className="question-answer-section">
        <h3>Question & Answer Summary</h3>
        {questions.map((question, index) => {
          const answer = answers.find((a) => a.questionId === question.id);
          return (
            <div key={index} className="qa-item">
              <div className="qa-question">
                <strong>Q{index + 1}:</strong> {question.text}
              </div>
              <div className="qa-answer">
                <strong>Your Answer:</strong>{" "}
                {answer ? answer.transcription : "No answer recorded"}
              </div>
            </div>
          );
        })}
      </div>

      <div className="results-actions">
        <button className="reset-button" onClick={onReset}>
          Start New Interview
        </button>
      </div>
    </div>
  );
};

export default ResultsSummary;
