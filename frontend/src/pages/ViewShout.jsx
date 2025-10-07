import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { shoutApi } from '../api/shouts';
import './ViewShout.css';

function ViewShout() {
  const { type, hash } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [shout, setShout] = useState(null);
  const [error, setError] = useState(null);
  const [showPreview, setShowPreview] = useState(true);

  useEffect(() => {
    checkShout();
  }, [hash]);

  const checkShout = async () => {
    try {
      const result = await shoutApi.getShout(hash, true);
      if (result.valid) {
        setLoading(false);
      } else {
        setError('Content not found or expired');
        setLoading(false);
      }
    } catch (err) {
      setError('Failed to load content');
      setLoading(false);
    }
  };

  const viewShout = async () => {
    setShowPreview(false);
    setLoading(true);

    try {
      const result = await shoutApi.getShout(hash, false);

      if (result.valid) {
        setShout(result.shout);
      } else {
        setError(`Content ${result.reason === 'expired_hits' ? 'has been viewed too many times' :
                          result.reason === 'expired_time' ? 'has expired' :
                          'not found or expired'}`);
      }
    } catch (err) {
      setError(err.response?.data?.reason || 'Failed to load content');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="view-shout-container">
        <div className="loading-card">
          <div className="spinner"></div>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="view-shout-container">
        <div className="error-card">
          <h2>🔥 Burned!</h2>
          <p>{error}</p>
          <button onClick={() => navigate('/')} className="home-button">
            Go Home
          </button>
        </div>
      </div>
    );
  }

  if (showPreview) {
    return (
      <div className="view-shout-container">
        <div className="preview-card">
          <div className="eye-icon">👁️</div>
          <h2>Ready to View?</h2>
          <p>This content will be visible only once or for a limited time.</p>
          <button onClick={viewShout} className="view-button">
            View Content
          </button>
          <button onClick={() => navigate('/')} className="cancel-button">
            Cancel
          </button>
        </div>
      </div>
    );
  }

  if (!shout) {
    return null;
  }

  return (
    <div className="view-shout-container">
      <div className="shout-card">
        <div className="shout-header">
          <h2>Ephemeral Content</h2>
          <div className="shout-info">
            <span>Views: {shout.current_hits}/{shout.max_hits}</span>
          </div>
        </div>

        <div className="shout-content">
          {type === 'text' && (
            <div className="text-content">
              <p>{shout.content_text}</p>
            </div>
          )}

          {type === 'photo' && shout.media_url && (
            <div className="media-content">
              <img src={shout.media_url} alt="Shout" className="shout-image" />
            </div>
          )}

          {type === 'audio' && shout.media_url && (
            <div className="media-content">
              <audio controls className="shout-audio">
                <source src={shout.media_url} type="audio/wav" />
                Your browser does not support audio playback.
              </audio>
            </div>
          )}

          {type === 'video' && shout.media_url && (
            <div className="media-content">
              <video controls className="shout-video">
                <source src={shout.media_url} type="video/mp4" />
                Your browser does not support video playback.
              </video>
            </div>
          )}
        </div>

        <div className="shout-footer">
          <button onClick={() => navigate('/')} className="home-button">
            Create Your Own
          </button>
        </div>
      </div>
    </div>
  );
}

export default ViewShout;
