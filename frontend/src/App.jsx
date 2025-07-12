import { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [visaType, setVisaType] = useState("tourist");
  const [voice, setVoice] = useState("en-US-JennyNeural");
  const [questions, setQuestions] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [ws, setWs] = useState(null);

  // Replace with your API and WebSocket URLs
  const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const wsUrl = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/stream";

  useEffect(() => {
    // Connect to WebSocket
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log("WebSocket connected");
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Handle incoming messages
    };

    socket.onclose = () => {
      console.log("WebSocket disconnected");
    };

    setWs(socket);

    return () => {
      socket.close();
    };
  }, [wsUrl]);

  const startInterview = async () => {
    // Fetch questions from the server
    const response = await fetch(`${apiUrl}/generate-questions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ visaType, numQuestions: 5 }),
    });

    const data = await response.json();
    setQuestions(data.questions);
    setCurrentQuestion(0);
    setAnswers([]);
  };

  const handleAnswer = (answer) => {
    // Send answer to the server
    ws.send(JSON.stringify({ answer }));

    setAnswers([...answers, answer]);

    // Move to the next question
    setCurrentQuestion(currentQuestion + 1);
  };

  return (
    <div className="App">
      <h1>Visa Interview Training</h1>
      <div>
        <label>
          Visa Type:
          <select
            value={visaType}
            onChange={(e) => setVisaType(e.target.value)}
          >
            <option value="tourist">Tourist</option>
            <option value="student">Student</option>
          </select>
        </label>
      </div>
      <div>
        <label>
          Voice:
          <select value={voice} onChange={(e) => setVoice(e.target.value)}>
            <option value="en-US-JennyNeural">Jenny (US English)</option>
            <option value="en-GB-RachelNeural">Rachel (UK English)</option>
            <option value="es-ES-AlvaroNeural">Alvaro (Spanish)</option>
          </select>
        </label>
      </div>
      <button onClick={startInterview}>Start Interview</button>
      <div>
        {questions.length > 0 && currentQuestion < questions.length && (
          <div>
            <h2>Question {currentQuestion + 1}</h2>
            <p>{questions[currentQuestion]}</p>
            <button onClick={() => handleAnswer("Sample answer")}>
              Submit Answer
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
