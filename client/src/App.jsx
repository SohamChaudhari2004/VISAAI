import React, { useState, useEffect, useRef } from "react";
import "./App.css";
import InterviewForm from "./components/InterviewForm";
import AudioRecorder from "./components/AudioRecorder";
import QuestionDisplay from "./components/QuestionDisplay";
import AnswerFeedback from "./components/AnswerFeedback";
import ResultsSummary from "./components/ResultsSummary";

const App = () => {
  // State for the application
  const [voices, setVoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [lastAnswer, setLastAnswer] = useState("");
  const [lastEvaluation, setLastEvaluation] = useState(null);
  const [finalEvaluation, setFinalEvaluation] = useState(null);
  const [audioPlaying, setAudioPlaying] = useState(false);
  const [processingAnswer, setProcessingAnswer] = useState(false);
  const [interviewState, setInterviewState] = useState("setup"); // setup, interview, results
  const [interviewConfig, setInterviewConfig] = useState({
    visaType: "",
    voiceType: "",
    questionCount: 5, // Default to free tier
  });
  const [results, setResults] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [ws, setWs] = useState(null);

  const audioRef = useRef(null);
  const apiBaseUrl = "http://localhost:8000";
  const wsUrl = "ws://localhost:8000/ws"; // WebSocket URL

  // Fetch available voices on component mount
  useEffect(() => {
    const fetchVoices = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${apiBaseUrl}/api/voices`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setVoices(data);
      } catch (error) {
        setError(`Failed to fetch voices: ${error.message}`);
      } finally {
        setLoading(false);
      }
    };
    fetchVoices();
  }, [apiBaseUrl]);

  // Play audio when audioUrl changes
  useEffect(() => {
    if (audioUrl && audioRef.current) {
      const playAudio = async () => {
        try {
          setAudioPlaying(true);
          // Clear any previous recording state
          setIsRecording(false);

          // Set the audio source
          if (audioUrl.startsWith("data:")) {
            audioRef.current.src = audioUrl;
          } else {
            audioRef.current.src = `${apiBaseUrl}${audioUrl}`;
          }

          // Play the audio
          await audioRef.current.play();

          // After audio plays, wait 2 seconds and then start recording automatically
          audioRef.current.onended = () => {
            setAudioPlaying(false);
            console.log("Question audio finished playing");

            // Add a delay before starting recording
            setTimeout(() => {
              if (!processingAnswer) {
                console.log("Starting recording");
                setIsRecording(true);
              }
            }, 2000);
          };
        } catch (err) {
          console.error("Error playing audio:", err);
          setAudioPlaying(false);
          setError(`Failed to play question audio: ${err.message}`);
        }
      };
      playAudio();
    }
  }, [audioUrl, processingAnswer]);

  // Only connect WebSocket once per session
  useEffect(() => {
    if (!sessionId) return;
    if (ws) return; // Prevent multiple connections

    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log("WebSocket connected");
      // Send session ID immediately
      socket.send(JSON.stringify({ session_id: sessionId }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Handle WebSocket messages here
    };

    socket.onclose = () => {
      console.log("WebSocket disconnected");
      setWs(null);
    };

    setWs(socket);

    return () => {
      socket.close();
    };
  }, [wsUrl, sessionId]);

  // Start a new interview session
  const startInterview = async (formData) => {
    try {
      setLoading(true);
      const response = await fetch(`${apiBaseUrl}/api/startInterview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Update state with interview data
      setSessionId(data.session_id);
      setCurrentQuestion(data.question_text);
      setAudioUrl(data.audio_url);
      setQuestionIndex(data.question_index);
      setTotalQuestions(data.total_questions);
      setFinalEvaluation(null);

      // Reset previous interview data
      setLastAnswer("");
      setLastEvaluation(null);
      setProcessingAnswer(false);
      setInterviewState("interview"); // Move to interview state
    } catch (error) {
      setError(`Failed to start interview: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Handle answer submission (from recording or text)
  const handleAnswerSubmit = async (answerText) => {
    try {
      setProcessingAnswer(true);
      setLoading(true);
      setLastAnswer(answerText);

      console.log(`Submitting answer: "${answerText.substring(0, 30)}..."`);

      // Submit the answer to the API
      const response = await fetch(`${apiBaseUrl}/api/submitAnswer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          answer_text: answerText,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `HTTP error! status: ${response.status}, message: ${errorText}`
        );
      }

      const data = await response.json();

      if (data.session_complete) {
        // Interview is complete
        setFinalEvaluation(data.final_evaluation);
        setCurrentQuestion(null);
        setInterviewState("results"); // Move to results state
      } else {
        // Move to next question
        setCurrentQuestion(data.question_text);
        setAudioUrl(data.audio_url);
        setQuestionIndex(data.question_index);
        setLastEvaluation(data.last_evaluation);
      }
    } catch (error) {
      console.error("API Error:", error);
      setError(`Failed to submit answer: ${error.message}`);
    } finally {
      setProcessingAnswer(false);
      setLoading(false);
    }
  };

  // Handle recording complete
  const handleRecordingComplete = (transcribedText) => {
    console.log("Recording complete, transcribed text received");
    // Use the transcribed text to submit the answer
    handleAnswerSubmit(transcribedText);
  };

  // Handle interview restart
  const handleRestart = () => {
    // Stop any ongoing audio or recording
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
    }

    // Reset all state
    setSessionId(null);
    setCurrentQuestion(null);
    setAudioUrl(null);
    setQuestionIndex(0);
    setTotalQuestions(0);
    setIsRecording(false);
    setLastAnswer("");
    setLastEvaluation(null);
    setFinalEvaluation(null);
    setAudioPlaying(false);
    setProcessingAnswer(false);
    setInterviewState("setup"); // Reset to setup state
  };

  return (
    <div className="app-container">
      <h1>AI Visa Interview Training</h1>
      {error && (
        <div className="error-message">
          <p>{error}</p>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {loading && <div className="loader">Loading...</div>}

      {!loading && (
        <div className="content-area">
          {interviewState === "setup" && (
            <InterviewForm voices={voices} onSubmit={startInterview} />
          )}

          {interviewState === "interview" && sessionId && !finalEvaluation && (
            <div className="interview-session">
              <div className="status-indicators">
                <div
                  className={`status-dot ${audioPlaying ? "active" : ""}`}
                  title="Audio Playing"
                >
                  {audioPlaying ? "Speaking..." : "Waiting"}
                </div>
                <div
                  className={`status-dot ${
                    isRecording ? "active recording" : ""
                  }`}
                  title="Recording"
                >
                  {isRecording ? "Recording..." : "Mic Off"}
                </div>
                <div
                  className={`status-dot ${
                    processingAnswer ? "active processing" : ""
                  }`}
                  title="Processing"
                >
                  {processingAnswer ? "Processing..." : "Ready"}
                </div>
              </div>

              <QuestionDisplay
                question={currentQuestion}
                questionIndex={questionIndex}
                totalQuestions={totalQuestions}
              />

              <AudioRecorder
                isRecording={isRecording}
                setIsRecording={setIsRecording}
                onRecordingComplete={handleRecordingComplete}
                sessionId={sessionId}
                maxDuration={20}
                disabled={audioPlaying || processingAnswer}
              />

              {lastEvaluation && (
                <AnswerFeedback
                  evaluation={lastEvaluation}
                  answer={lastAnswer}
                />
              )}
            </div>
          )}

          {interviewState === "results" && finalEvaluation && (
            <ResultsSummary
              evaluation={finalEvaluation}
              onRestart={handleRestart}
            />
          )}
        </div>
      )}

      <audio ref={audioRef} style={{ display: "none" }} />
    </div>
  );
};

export default App;
