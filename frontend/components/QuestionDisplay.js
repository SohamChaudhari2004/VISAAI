import React, { useState, useEffect, useRef } from 'react';
import AudioRecorder from './AudioRecorder';
import styles from './QuestionDisplay.module.css';

const QuestionDisplay = ({
  question,
  questionNumber,
  totalQuestions,
  audioUrl,
  sessionId,
  onAnswerComplete,
  transcription,
  evaluation
}) => {
  const [interviewState, setInterviewState] = useState('waiting'); // waiting, playing, answering, evaluating, complete
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef(null);
  const autoStartTimerRef = useRef(null);

  // Handle audio playback and state transitions
  useEffect(() => {
    if (!audioUrl) return;

    const playAudio = async () => {
      try {
        // Reset state for new question
        setInterviewState('waiting');

        // Wait 1.5 seconds before playing audio
        await new Promise(resolve => setTimeout(resolve, 1500));

        // Play the question audio
        setInterviewState('playing');
        setIsPlaying(true);

        if (audioRef.current) {
          audioRef.current.src = audioUrl;
          audioRef.current.play();
        }
      } catch (err) {
        console.error('Error playing audio:', err);
      }
    };

    playAudio();
  }, [audioUrl]);

  // Set up audio element event handlers
  useEffect(() => {
    const audioElement = audioRef.current;
    if (!audioElement) return;

    const handleAudioEnded = () => {
      setIsPlaying(false);

      // Wait 2 seconds after audio finishes before starting recording
      autoStartTimerRef.current = setTimeout(() => {
        setInterviewState('answering');
      }, 2000);
    };

    audioElement.addEventListener('ended', handleAudioEnded);

    return () => {
      audioElement.removeEventListener('ended', handleAudioEnded);
      if (autoStartTimerRef.current) {
        clearTimeout(autoStartTimerRef.current);
      }
    };
  }, []);

  // Handle answer completion
  const handleAnswerComplete = (answerText) => {
    setInterviewState('evaluating');
    if (onAnswerComplete) {
      onAnswerComplete(answerText);
    }
  };

  return (
    <div className={styles.questionDisplay}>
      <div className={styles.progressBar}>
        <div className={styles.progressFill} style={{ width: `${(questionNumber / totalQuestions) * 100}%` }} />
        <span className={styles.progressText}>
          Question {questionNumber} of {totalQuestions}
        </span>
      </div>

      <div className={styles.questionCard}>
        <h3>Question:</h3>
        <p className={styles.questionText}>{question}</p>
      </div>

      <div className={styles.statusIndicator}>
        {interviewState === 'waiting' && <p>Preparing question...</p>}
        {interviewState === 'playing' && <p>Listening to question...</p>}
        {interviewState === 'answering' && <p>Please answer the question now</p>}
        {interviewState === 'evaluating' && <p>Processing your answer...</p>}
      </div>

      <audio ref={audioRef} style={{ display: 'none' }} />

      {interviewState === 'answering' && (
        <AudioRecorder
          sessionId={sessionId}
          onRecordingComplete={handleAnswerComplete}
          maxDuration={30}
          disabled={interviewState !== 'answering'}
        />
      )}

      {transcription && (
        <div className={styles.transcription}>
          <h4>Your Answer:</h4>
          <p>{transcription}</p>
        </div>
      )}

      {evaluation && (
        <div className={styles.evaluation}>
          <h4>Feedback:</h4>
          <p>{evaluation.feedback}</p>
          <div className={styles.scores}>
            <div className={styles.scoreItem}>
              <span>Fluency:</span>
              <span>{evaluation.fluency_score}%</span>
            </div>
            <div className={styles.scoreItem}>
              <span>Content:</span>
              <span>{evaluation.content_accuracy_score}%</span>
            </div>
            <div className={styles.scoreItem}>
              <span>Overall:</span>
              <span>{evaluation.overall_score}%</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuestionDisplay;
