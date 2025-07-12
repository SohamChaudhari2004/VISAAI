import React, { useState } from "react";
import "./InterviewForm.css";

const InterviewForm = ({ voices, onSubmit }) => {
  const [visaType, setVisaType] = useState("tourist");
  const [voiceId, setVoiceId] = useState("");
  const [subscriptionLevel, setSubscriptionLevel] = useState("free"); // free, super, premium

  // Set default voice when voices are loaded
  React.useEffect(() => {
    if (voices && voices.length > 0 && !voiceId) {
      setVoiceId(voices[0].voice_id);
    }
  }, [voices, voiceId]);

  const handleSubmit = (e) => {
    e.preventDefault();

    // Validate form
    if (!visaType || !voiceId) {
      alert("Please select both visa type and voice");
      return;
    }

    // Create the request payload
    const formData = {
      visa_type: visaType,
      voice_id: voiceId,
      subscription_level: subscriptionLevel,
    };

    // Call the onSubmit prop instead of onStart
    onSubmit(formData);
  };

  return (
    <div className="interview-form-container">
      <h2>Interview Setup</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="visaType">Visa Type:</label>
          <div className="select-wrapper">
            <select
              id="visaType"
              value={visaType}
              onChange={(e) => setVisaType(e.target.value)}
              required
            >
              <option value="tourist">Tourist Visa</option>
              <option value="student">Student Visa</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="voiceType">Interviewer Voice:</label>
          <div className="select-wrapper">
            <select
              id="voiceType"
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
              required
            >
              {voices &&
                voices.map((voice) => (
                  <option key={voice.voice_id} value={voice.voice_id}>
                    {voice.name} ({voice.language})
                  </option>
                ))}
            </select>
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="subscriptionLevel">Subscription Level:</label>
          <div className="select-wrapper">
            <select
              id="subscriptionLevel"
              value={subscriptionLevel}
              onChange={(e) => setSubscriptionLevel(e.target.value)}
            >
              <option value="free">Free (5 questions)</option>
              <option value="super">Super (10 questions)</option>
              <option value="premium">Premium (15 questions)</option>
            </select>
          </div>
        </div>

        <button type="submit" className="start-button">
          Start Interview
        </button>
      </form>
    </div>
  );
};

export default InterviewForm;

