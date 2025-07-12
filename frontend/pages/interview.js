import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';

import InterviewSetup from '../components/InterviewSetup';
import QuestionDisplay from '../components/QuestionDisplay';
import EvaluationDisplay from '../components/EvaluationDisplay';

const InterviewPage = () => {
  const router = useRouter();
  const [sessionState, setSessionState] = useState({
    isSetup: true,
    isActive: false,
    isComplete: false,
    sessionId: null,
    currentQuestion: '',
    audioUrl: '',
    questionIndex: 0,
    totalQuestions: 0,
    transcription: '',
    isRecording: false,
    evaluation: null,
    finalEvaluation: null,
    isProcessingAnswer: false,
  });

  const wsRef = useRef(null);
  const audioRef = useRef(null);

  // Start a new interview session
  const startInterview = async (formData) => {
    try {
      const response = await fetch('/api/startInterview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      setSessionState({
        ...sessionState,
        isSetup: false,
        isActive: true,
        sessionId: data.session_id,
        currentQuestion: data.question_text,
        audioUrl: data.audio_url,
        questionIndex: data.question_index,
        totalQuestions: data.total_questions,
      });

      // Setup WebSocket connection after session is started
      setupWebSocket(data.session_id);
    } catch (error) {
      console.error('Error starting interview:', error);
      alert('Failed to start interview. Please try again.');
    }
  };

  // Setup WebSocket connection for audio streaming
  const setupWebSocket = (sessionId) => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${window.location.host}/ws/stream`;

    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      console.log('WebSocket connected');
      // Send session ID to initialize connection
      wsRef.current.send(JSON.stringify({
        session_id: sessionId,
        question_index: sessionState.questionIndex
      }));
    };

    // Handle answer completion
    const handleAnswerComplete = (answerText) => {
      // Update state with transcription
      setSessionState(prevState => ({
        ...prevState,
        transcription: answerText,
        isProcessingAnswer: true
      }));

      // No need to manually submit - the WebSocket will handle the processing flow
    };

    // Handle next question from WebSocket
    const handleNextQuestion = (data) => {
      // Play audio after a short delay
      setTimeout(() => {
        setSessionState(prevState => ({
          ...prevState,
          currentQuestion: data.question_text,
          audioUrl: data.audio_url,
          questionIndex: data.question_index,
          totalQuestions: data.total_questions,
          transcription: '',
          evaluation: data.last_evaluation,
          isProcessingAnswer: false
        }));

        // Play the question audio
        if (audioRef.current) {
          audioRef.current.src = data.audio_url;
          audioRef.current.play();
        }
      }, 2000); // Wait 2 seconds before playing next question
    };

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('WebSocket message:', data);

      switch (data.type) {
        case 'status':
          // Update recording status
          setSessionState(prevState => ({
            ...prevState,
            isRecording: data.recording
          }));
          break;

        case 'transcription':
          // Update with transcribed text
          setSessionState(prevState => ({
            ...prevState,
            transcription: data.text,
            isRecording: false,
            isProcessingAnswer: true
          }));
          break;

        case 'next_question':
          // Handle next question with delay
          handleNextQuestion(data);
          break;

        case 'interview_complete':
          // Handle completion of interview
          setSessionState(prevState => ({
            ...prevState,
            isActive: false,
            isComplete: true,
            evaluation: data.last_evaluation,
            finalEvaluation: data.evaluation,
          }));
          break;

        case 'error':
          console.error('WebSocket error:', data.message);
          alert(`Error: ${data.message}`);
          break;
      }
    };

    wsRef.current.onclose = () => {
      console.log('WebSocket disconnected');
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  };

  // Start recording the answer
  const startRecording = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'start_recording' }));
      setSessionState(prevState => ({
        ...prevState,
        isRecording: true,
        transcription: ''
      }));
    } else {
      console.error('WebSocket not connected');
      alert('Connection error. Please refresh and try again.');
    }
  };

  // Send audio data through WebSocket
  const sendAudioData = (audioBlob) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(audioBlob);
    }
  };

  // Stop recording and finalize the answer
  const stopRecording = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // Send signal to indicate recording is complete
      wsRef.current.send(JSON.stringify({ type: 'recording-complete' }));

      setSessionState(prevState => ({
        ...prevState,
        isRecording: false
      }));
    }
  };

  // Clean up WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Render different views based on session state
  if (sessionState.isSetup) {
    return <InterviewSetup onSubmit={startInterview} />;
  }

  if (sessionState.isComplete) {
    return <EvaluationDisplay
      lastEvaluation={sessionState.evaluation}
      finalEvaluation={sessionState.finalEvaluation}
      onRestart={() => router.reload()}
    />;
  }

  return (
    <>
      <Head>
        <title>VISA Interview Practice</title>
        <meta name="description" content="Practice your visa interview skills" />
      </Head>

      <div className="interview-container">
        <audio ref={audioRef} style={{ display: 'none' }} controls />

        <QuestionDisplay
          question={sessionState.currentQuestion}
          questionNumber={sessionState.questionIndex}
          totalQuestions={sessionState.totalQuestions}
          audioUrl={sessionState.audioUrl}
          sessionId={sessionState.sessionId}
          onAnswerComplete={handleAnswerComplete}
          transcription={sessionState.transcription}
          evaluation={sessionState.evaluation}
          isProcessingAnswer={sessionState.isProcessingAnswer}
        />

        <div className="interview-progress">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${(sessionState.questionIndex / sessionState.totalQuestions) * 100}%` }}
            ></div>
          </div>
          <p>Question {sessionState.questionIndex} of {sessionState.totalQuestions}</p>
        </div>
      </div>
    </>
  );
};

export default InterviewPage;
