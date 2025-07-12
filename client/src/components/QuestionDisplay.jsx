import React, { useState, useEffect } from "react";
import AudioRecorder from "./AudioRecorder";
import AnswerFeedback from "./AnswerFeedback";
// import { FaVolumeUp } from "react-icons/fa";
import "./QuestionDisplay.css";

const QuestionDisplay = ({
  question,
  questionNumber,
  totalQuestions,
  voiceType,
  onAnswerSubmit,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioUrl, setAudioUrl] = useState("");
  const [audioElement, setAudioElement] = useState(null);
  const [currentAnswer, setCurrentAnswer] = useState(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [audioError, setAudioError] = useState(false);

  // Generate audio for the question when component mounts
  useEffect(() => {
    generateQuestionAudio();

    return () => {
      // Clean up audio URL object when component unmounts
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }

      // Stop audio playback if component unmounts
      if (audioElement) {
        audioElement.pause();
      }
    };
  }, [question, voiceType]);

  useEffect(() => {
    if (audioElement) {
      audioElement.onerror = () => {
        setAudioError(true);
        setIsPlaying(false);
        console.error("Error playing audio");
      };
    }
  }, [audioUrl, voiceType]);

  const generateQuestionAudio = async () => {
    try {
      setIsLoading(true);

      // Request TTS audio from backend
      const response = await fetch("/api/tts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text: question.text,
          voice: voiceType,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to generate speech");
      }

      // Convert response to blob and create URL
      const audioBlob = await response.blob();
      const url = URL.createObjectURL(audioBlob);
      setAudioUrl(url);

      // Create and configure audio element
      const audio = new Audio(url);
      audio.onplay = () => setIsPlaying(true);
      audio.onended = () => setIsPlaying(false);
      audio.onerror = () => {
        setIsPlaying(false);
        console.error("Error playing audio");
      };

      setAudioElement(audio);

      // Automatically play the question when loaded
      audio.play();
    } catch (error) {
      console.error("Error generating question audio:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const playQuestionAudio = () => {
    if (audioElement) {
      audioElement.play();
    }
  };

  const handleAnswerRecorded = (answerData) => {
    setCurrentAnswer(answerData);
    setShowFeedback(true);
  };

  const handleContinue = () => {
    // Send answer data to parent component
    onAnswerSubmit({
      questionId: question.id,
      transcription: currentAnswer.transcription,
      duration: currentAnswer.duration,
      confidence: currentAnswer.confidence,
    });

    // Reset state for next question
    setCurrentAnswer(null);
    setShowFeedback(false);
  };

  return (
    <div className="question-display">
      <div className="progress-indicator">
        <span>
          Question {questionNumber} of {totalQuestions}
        </span>
        <div className="progress-bar">
          <div
            className="progress-bar-fill"
            style={{ width: `${(questionNumber / totalQuestions) * 100}%` }}
          />
        </div>
      </div>

      <div className="question-card">
        <h3>Interview Question:</h3>
        <p className="question-text">{question.text}</p>

        <button
          type="button"
          className="play-audio-button"
          onClick={playQuestionAudio}
          disabled={isLoading || isPlaying}
        >
          {/* <FaVolumeUp /> */}
          {" volume up"}
          {isLoading
            ? "Loading..."
            : isPlaying
            ? "Playing..."
            : "Replay Question"}
        </button>
      </div>

      {audioError && (
        <div className="audio-error">
          <p>
            Could not play question audio. Please check your connection or try
            again.
          </p>
        </div>
      )}

      {!showFeedback ? (
        <>
          <div className="answer-section">
            <h3>Your Answer</h3>
            <p className="instructions">
              Record your answer within 20 seconds. Try to be clear and concise.
            </p>
            <AudioRecorder onAudioSubmit={handleAnswerRecorded} />
          </div>
        </>
      ) : (
        <AnswerFeedback
          answer={currentAnswer.transcription}
          onContinue={handleContinue}
        />
      )}
    </div>
  );
};

export default QuestionDisplay;
