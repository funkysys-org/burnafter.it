import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import './Home.css';

function Home() {
  const navigate = useNavigate();
  const [iconIndex, setIconIndex] = useState(0);
  const [chatIconIndex, setChatIconIndex] = useState(0);

  const icons = ['🎥', '🎤', '📤', '📝', '🕵️', '📷'];
  const chatIcons = ['📤', '💬', '🕵️', '🎤'];

  useEffect(() => {
    const interval1 = setInterval(() => {
      setIconIndex((prev) => (prev + 1) % icons.length);
    }, 2500);

    const interval2 = setInterval(() => {
      setChatIconIndex((prev) => (prev + 1) % chatIcons.length);
    }, 2800);

    return () => {
      clearInterval(interval1);
      clearInterval(interval2);
    };
  }, []);

  const handleSECClick = () => {
    navigate('/create/text');
  };

  const handleESCClick = async () => {
    try {
      const { chatApi } = await import('../api/chat');
      const result = await chatApi.createChatRoom();
      if (result.success) {
        navigate(`/chat/${result.hash}`);
      }
    } catch (error) {
      console.error('Failed to create chat room:', error);
      alert('Failed to create chat room. Please try again.');
    }
  };

  return (
    <div className="home-container">
      <div className="home-content">
        <h1 className="home-title">BurnAfterIt</h1>
        <p className="home-subtitle">Ephemeral Content Sharing</p>

        <div className="options-container">
          <div className="option-card" onClick={handleSECClick}>
            <div className="option-icon-container">
              <span className="option-icon">{icons[iconIndex]}</span>
            </div>
            <h2 className="option-title">SEC</h2>
            <p className="option-description">Share Ephemeral Content</p>
            <p className="option-details">
              Share text, audio, video, or photos that self-destruct after viewing
            </p>
          </div>

          <div className="option-card" onClick={handleESCClick}>
            <div className="option-icon-container">
              <span className="option-icon">{chatIcons[chatIconIndex]}</span>
            </div>
            <h2 className="option-title">ESC</h2>
            <p className="option-description">Ephemeral Secure Chat</p>
            <p className="option-details">
              Create temporary chat rooms with self-destructing messages
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Home;
