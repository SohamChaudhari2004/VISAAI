import { useState, useEffect, useRef, useCallback } from "react";
import "./AudioRecorder.css";

const AudioRecorder = ({
  isRecording,
  setIsRecording,
  onRecordingComplete,
  sessionId,
  maxDuration = 20,
  disabled = false,
}) => {
  const [hasPermission, setHasPermission] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(maxDuration);
  const [stream, setStream] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const [transcribedText, setTranscribedText] = useState("");
  const [isPersistentConnection, setIsPersistentConnection] = useState(false);

  const websocketRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  const streamRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const recordingCompleteRef = useRef(false);
  const keepAliveIntervalRef = useRef(null);

  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 2000;

  // Get API base URL from environment or default
  const apiBaseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

  // Request microphone permission immediately on component mount
  useEffect(() => {
    async function getPermission() {
      try {
        const audioStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });
        streamRef.current = audioStream;
        setStream(audioStream);
        setHasPermission(true);
        setError(null);
      } catch (err) {
        console.error("Error accessing microphone:", err);
        setHasPermission(false);
        setError(`Microphone access error: ${err.message}`);
      }
    }

    getPermission();

    // Cleanup function
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // Setup WebSocket when the component mounts or sessionId changes
  useEffect(() => {
    if (sessionId) {
      connectWebSocket();

      // Send keep-alive pings every 30 seconds to maintain connection
      keepAliveIntervalRef.current = setInterval(() => {
        if (
          websocketRef.current &&
          websocketRef.current.readyState === WebSocket.OPEN
        ) {
          websocketRef.current.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);
    }

    return () => {
      // Clean up WebSocket and interval on unmount
      if (websocketRef.current) {
        websocketRef.current.close();
      }
      if (keepAliveIntervalRef.current) {
        clearInterval(keepAliveIntervalRef.current);
      }
    };
  }, [sessionId]);

  // Setup timer for recording
  useEffect(() => {
    if (isRecording) {
      console.log("Starting recording timer");
      setTimeRemaining(maxDuration);
      recordingCompleteRef.current = false;

      timerRef.current = setInterval(() => {
        setTimeRemaining((prev) => {
          if (prev <= 1) {
            // Stop recording when timer reaches zero
            console.log("Recording time limit reached");
            setTimeout(() => {
              if (!recordingCompleteRef.current) {
                stopRecording();
              }
            }, 0);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }

    return () => clearInterval(timerRef.current);
  }, [isRecording, maxDuration]);

  // Setup main recording effect
  useEffect(() => {
    if (isRecording && hasPermission && !disabled) {
      startRecording();
    } else if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== "inactive"
    ) {
      stopRecording();
    }
  }, [isRecording, hasPermission, disabled]);

  const connectWebSocket = useCallback(() => {
    try {
      if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
        console.error("Maximum reconnection attempts reached");
        return;
      }

      const wsUrl =
        import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/stream";
      console.log(`Connecting to WebSocket at ${wsUrl}`);

      const ws = new WebSocket(wsUrl);
      websocketRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connection established");
        reconnectAttempts.current = 0; // Reset reconnect attempts on successful connection

        // Send session info once connected
        if (sessionId) {
          ws.send(
            JSON.stringify({
              session_id: sessionId,
              question_index: 0,
            })
          );
          console.log(`Sent session ID: ${sessionId} to WebSocket`);
        }

        // Start keep-alive mechanism
        if (keepAliveIntervalRef.current) {
          clearInterval(keepAliveIntervalRef.current);
        }

        keepAliveIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "ping" }));
          }
        }, 30000); // Send ping every 30 seconds
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === "pong") {
            console.log("Received keep-alive pong");
            return;
          }

          if (data.type === "transcription") {
            setTranscribedText(data.text);
            recordingCompleteRef.current = true;
            setIsRecording(false);
            onRecordingComplete(data.text);
            setStatus("completed");
          } else if (data.type === "status") {
            setStatus(data.recording ? "recording" : "idle");
          } else if (data.type === "error") {
            console.error("WebSocket error:", data.message);
            setError(`Recording error: ${data.message}`);
            setStatus("error");
          } else if (data.type === "next_question") {
            // Handle next question message from server
            console.log("Received next question from WebSocket");
            onRecordingComplete(data.last_evaluation.feedback, {
              nextQuestion: data.question_text,
              audioUrl: data.audio_url,
              questionIndex: data.question_index,
              totalQuestions: data.total_questions,
              evaluation: data.last_evaluation,
            });
          } else if (data.type === "interview_complete") {
            // Handle interview complete message from server
            console.log("Interview complete signal received");
            onRecordingComplete(data.last_evaluation.feedback, {
              isComplete: true,
              evaluation: data.evaluation,
            });
          }
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };

      ws.onclose = (event) => {
        console.log(
          `WebSocket connection closed: ${event.code} ${event.reason}`
        );

        // Clean up the keep-alive interval
        if (keepAliveIntervalRef.current) {
          clearInterval(keepAliveIntervalRef.current);
          keepAliveIntervalRef.current = null;
        }

        // Don't attempt to reconnect if we intentionally closed the connection
        if (
          event.code !== 1000 &&
          reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS
        ) {
          console.log("Attempting to reconnect WebSocket...");
          reconnectAttempts.current += 1;
          setTimeout(connectWebSocket, RECONNECT_DELAY);
        }
      };
    } catch (error) {
      console.error("Failed to connect to WebSocket:", error);
    }
  }, [sessionId]);

  // Clean up WebSocket connection and intervals when component unmounts
  useEffect(() => {
    connectWebSocket();

    return () => {
      if (websocketRef.current) {
        websocketRef.current.close(1000, "Component unmounting");
        websocketRef.current = null;
      }

      if (keepAliveIntervalRef.current) {
        clearInterval(keepAliveIntervalRef.current);
        keepAliveIntervalRef.current = null;
      }
    };
  }, [connectWebSocket, sessionId]);

  const startRecording = async () => {
    try {
      console.log("Starting recording");
      setStatus("recording");
      audioChunksRef.current = [];
      recordingCompleteRef.current = false;

      // Use existing stream if available
      const stream =
        streamRef.current ||
        (await navigator.mediaDevices.getUserMedia({ audio: true }));

      const options = { mimeType: "audio/webm" };
      mediaRecorderRef.current = new MediaRecorder(stream, options);

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);

          // Send audio chunk to server while recording
          if (
            websocketRef.current &&
            websocketRef.current.readyState === WebSocket.OPEN
          ) {
            websocketRef.current.send(event.data);
          }
        }
      };

      mediaRecorderRef.current.onstop = () => {
        console.log("MediaRecorder stopped");
        // Send end signal to WebSocket
        if (
          websocketRef.current &&
          websocketRef.current.readyState === WebSocket.OPEN
        ) {
          websocketRef.current.send(
            JSON.stringify({ type: "recording-complete" })
          );
        }
      };

      // Notify server that we're starting recording
      if (
        websocketRef.current &&
        websocketRef.current.readyState === WebSocket.OPEN
      ) {
        websocketRef.current.send(JSON.stringify({ type: "start_recording" }));
      }

      // Set timeout for max duration
      setTimeout(() => {
        if (
          mediaRecorderRef.current &&
          mediaRecorderRef.current.state !== "inactive"
        ) {
          stopRecording();
        }
      }, maxDuration * 1000);

      mediaRecorderRef.current.start(250); // Collect data in 250ms chunks
      console.log("MediaRecorder started");
    } catch (error) {
      console.error("Error starting recording:", error);
      setError(`Recording error: ${error.message}`);
      setStatus("error");
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    console.log("Stopping recording");
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== "inactive"
    ) {
      try {
        mediaRecorderRef.current.stop();
        setStatus("processing");

        // Don't stop the tracks if we want to reuse the stream
        // Just signal that we're not recording anymore
        setIsRecording(false);
      } catch (error) {
        console.error("Error stopping MediaRecorder:", error);
      }
    }
  };

  // Handle manual stop
  const handleStopClick = () => {
    stopRecording();
  };

  return (
    <div className="audio-recorder">
      <div className="recording-status">
        {isRecording ? (
          <>
            <div className="recording-indicator" />
            <span>Recording... {timeRemaining}s remaining</span>
          </>
        ) : status === "processing" ? (
          <span>Processing your answer...</span>
        ) : isPersistentConnection ? (
          <span>Ready for next question</span>
        ) : (
          <span>Waiting for connection...</span>
        )}
      </div>

      {status === "processing" && (
        <div className="processing-status">
          <div className="processing-spinner"></div>
          <span>Processing your answer...</span>
        </div>
      )}

      {/* Only show stop button when recording */}
      {isRecording && (
        <div className="controls">
          <button className="stop-button" onClick={handleStopClick}>
            Stop Recording
          </button>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {!hasPermission && !error && (
        <div className="permission-error">
          Please allow microphone access to record your answers.
        </div>
      )}

      <style jsx="true">{`
        .audio-recorder {
          margin: 1.5rem 0;
          text-align: center;
          padding: 1rem;
          border-radius: 8px;
          background-color: #f5f5f5;
          border: 1px solid #ddd;
        }

        .recording-status {
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 1rem;
          font-size: 1.1rem;
          font-weight: 500;
        }

        .recording-indicator {
          width: 12px;
          height: 12px;
          background-color: #f44336;
          border-radius: 50%;
          margin-right: 8px;
          animation: pulse 1.5s infinite;
        }

        .processing-status {
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 1rem 0;
        }

        .processing-spinner {
          width: 16px;
          height: 16px;
          border: 2px solid #ddd;
          border-top-color: #0070f3;
          border-radius: 50%;
          margin-right: 8px;
          animation: spin 1s linear infinite;
        }

        @keyframes pulse {
          0% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.3;
            transform: scale(1.2);
          }
          100% {
            opacity: 1;
            transform: scale(1);
          }
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }

        .controls {
          margin: 1rem 0;
        }

        .stop-button {
          padding: 0.75rem 1.5rem;
          font-size: 1rem;
          border-radius: 4px;
          cursor: pointer;
          border: none;
          transition: background-color 0.3s;
          background-color: #f44336;
          color: white;
        }

        .stop-button:hover {
          background-color: #d32f2f;
        }

        .permission-error,
        .error-message {
          color: #f44336;
          margin-top: 1rem;
          font-size: 0.9rem;
          background-color: #ffebee;
          padding: 0.5rem;
          border-radius: 4px;
        }
      `}</style>
    </div>
  );
};

export default AudioRecorder;
