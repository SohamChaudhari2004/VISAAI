import React, { useState, useEffect, useRef } from 'react';
import styles from './AudioRecorder.module.css';

const AudioRecorder = ({
  sessionId,
  onRecordingComplete,
  maxDuration = 30, // Increase to 30 seconds
  isAutoRecord = true,
  disabled = false
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(maxDuration);
  const [isReady, setIsReady] = useState(false);
  const [status, setStatus] = useState('idle'); // idle, recording, processing, completed
  const [error, setError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const wsRef = useRef(null);
  const timerRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Connect WebSocket
  useEffect(() => {
    if (!sessionId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${window.location.host}/ws/stream`;

    console.log(`Connecting to WebSocket: ${wsUrl}`);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      // Initialize the connection with session ID
      ws.send(JSON.stringify({ session_id: sessionId }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);

        switch (data.type) {
          case 'ready':
            setIsReady(true);
            break;

          case 'status':
            setStatus(data.recording ? 'recording' : 'idle');
            break;

          case 'transcription':
            setStatus('completed');
            if (onRecordingComplete) {
              onRecordingComplete(data.text);
            }
            break;

          case 'error':
            setError(data.message);
            setStatus('idle');
            break;
        }
      } catch (error) {
        console.error('Error processing WebSocket message:', error);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed');
      setIsReady(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('Connection error. Please try again.');
      setIsReady(false);
    };

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [sessionId]);

  // Request microphone access
  useEffect(() => {
    const setupMicrophone = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        });

        streamRef.current = stream;
        setError(null);
      } catch (err) {
        console.error('Error accessing microphone:', err);
        setError('Microphone access denied. Please allow microphone access to continue.');
      }
    };

    setupMicrophone();

    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  // Handle recording timer
  useEffect(() => {
    if (isRecording) {
      setTimeRemaining(maxDuration);

      timerRef.current = setInterval(() => {
        setTimeRemaining(prev => {
          if (prev <= 1) {
            stopRecording();
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

  const startRecording = async () => {
    if (!streamRef.current || !wsRef.current || !isReady || disabled) return;

    try {
      setStatus('recording');
      setIsRecording(true);
      audioChunksRef.current = [];

      const mediaRecorder = new MediaRecorder(streamRef.current, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);

          // Send audio chunk to WebSocket
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(event.data);
          }
        }
      };

      mediaRecorder.onstop = () => {
        console.log('MediaRecorder stopped');

        // Signal that recording is complete
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'recording-complete' }));
        }

        setStatus('processing');
      };

      // Tell server we're starting to record
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'start_recording' }));
      }

      // Start recording with 250ms chunks
      mediaRecorder.start(250);
      console.log('Recording started');

    } catch (error) {
      console.error('Error starting recording:', error);
      setError(`Recording error: ${error.message}`);
      setIsRecording(false);
      setStatus('idle');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  return (
    <div className={styles.audioRecorder}>
      <div className={styles.recordingStatus}>
        {status === 'recording' ? (
          <div className={styles.recordingActive}>
            <div className={styles.recordingIndicator} />
            <span>Recording... {timeRemaining}s remaining</span>
          </div>
        ) : status === 'processing' ? (
          <div className={styles.processing}>
            <div className={styles.processingSpinner} />
            <span>Processing your answer...</span>
          </div>
        ) : status === 'completed' ? (
          <div className={styles.completed}>
            <span>Answer recorded</span>
          </div>
        ) : (
          <div className={styles.ready}>
            <span>{isReady ? 'Ready to record' : 'Connecting...'}</span>
          </div>
        )}
      </div>

      {status === 'idle' && isReady && !disabled && (
        <button
          className={styles.recordButton}
          onClick={startRecording}
          disabled={!isReady || disabled}
        >
          Start Speaking
        </button>
      )}

      {isRecording && (
        <button
          className={styles.stopButton}
          onClick={stopRecording}
        >
          Stop Recording
        </button>
      )}

      {error && (
        <div className={styles.errorMessage}>
          {error}
        </div>
      )}
    </div>
  );
};

export default AudioRecorder;
