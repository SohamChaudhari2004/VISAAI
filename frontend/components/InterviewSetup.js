import React, { useState, useEffect } from 'react';

const InterviewSetup = ({ onSubmit }) => {
  const [formData, setFormData] = useState({
    visa_type: 'TOURIST',
    subscription_level: 'free',
    voice_id: 'en-US-AriaNeural',
  });

  const [voiceOptions, setVoiceOptions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch available voices on component mount
  useEffect(() => {
    const fetchVoices = async () => {
      try {
        const response = await fetch('/api/voices');
        const data = await response.json();
        setVoiceOptions(data);

        // Set default voice if available
        if (data.length > 0) {
          setFormData(prev => ({ ...prev, voice_id: data[0].voice_id }));
        }
      } catch (error) {
        console.error('Error fetching voices:', error);
      }
    };

    fetchVoices();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await onSubmit(formData);
    } catch (error) {
      console.error('Error submitting form:', error);
      alert('An error occurred. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="setup-container">
      <h1>VISA Interview Practice</h1>
      <div className="setup-card">
        <h2>Setup Your Interview</h2>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Visa Type</label>
            <div className="radio-group">
              <label>
                <input
                  type="radio"
                  name="visa_type"
                  value="TOURIST"
                  checked={formData.visa_type === 'TOURIST'}
                  onChange={handleChange}
                />
                Tourist Visa
              </label>
              <label>
                <input
                  type="radio"
                  name="visa_type"
                  value="STUDENT"
                  checked={formData.visa_type === 'STUDENT'}
                  onChange={handleChange}
                />
                Student Visa
              </label>
            </div>
          </div>

          <div className="form-group">
            <label>Subscription Level</label>
            <div className="radio-group subscription">
              <label className={formData.subscription_level === 'free' ? 'selected' : ''}>
                <input
                  type="radio"
                  name="subscription_level"
                  value="free"
                  checked={formData.subscription_level === 'free'}
                  onChange={handleChange}
                />
                <div className="subscription-info">
                  <span className="subscription-title">Free</span>
                  <span className="subscription-detail">5 questions</span>
                </div>
              </label>
              <label className={formData.subscription_level === 'super' ? 'selected' : ''}>
                <input
                  type="radio"
                  name="subscription_level"
                  value="super"
                  checked={formData.subscription_level === 'super'}
                  onChange={handleChange}
                />
                <div className="subscription-info">
                  <span className="subscription-title">Super</span>
                  <span className="subscription-detail">10 questions</span>
                </div>
              </label>
              <label className={formData.subscription_level === 'premium' ? 'selected' : ''}>
                <input
                  type="radio"
                  name="subscription_level"
                  value="premium"
                  checked={formData.subscription_level === 'premium'}
                  onChange={handleChange}
                />
                <div className="subscription-info">
                  <span className="subscription-title">Premium</span>
                  <span className="subscription-detail">15 questions</span>
                </div>
              </label>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="voice_id">Voice Selection</label>
            <select
              id="voice_id"
              name="voice_id"
              value={formData.voice_id}
              onChange={handleChange}
              className="voice-selector"
            >
              {voiceOptions.map(voice => (
                <option key={voice.voice_id} value={voice.voice_id}>
                  {voice.name} ({voice.language})
                </option>
              ))}
            </select>
            <div className="voice-preview">
              <button
                type="button"
                className="voice-preview-button"
                onClick={() => {
                  // Play a sample of the selected voice
                  const audio = new Audio(`/api/sample-voice?voice_id=${formData.voice_id}`);
                  audio.play();
                }}
              >
                Preview Voice
              </button>
            </div>
          </div>

          <div className="form-footer">
            <button
              type="submit"
              className="start-button"
              disabled={isLoading}
            >
              {isLoading ? 'Setting Up...' : 'Start Interview'}
            </button>
          </div>
        </form>
      </div>

      <div className="setup-info">
        <h3>How it works</h3>
        <ol>
          <li>Select your visa type and interview configuration</li>
          <li>Listen to each question asked by the virtual interviewer</li>
          <li>Respond naturally by speaking into your microphone</li>
          <li>Receive immediate feedback on your responses</li>
          <li>Get a comprehensive evaluation at the end of the interview</li>
        </ol>
      </div>
    </div>
  );
};

export default InterviewSetup;
