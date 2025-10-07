import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { shoutApi } from '../api/shouts';
import { utilsApi } from '../api/utils';
import './CreateShout.css';

function CreateShout() {
  const { type: initialType } = useParams();
  const navigate = useNavigate();

  const [type, setType] = useState(initialType || 'text');
  const [maxHits, setMaxHits] = useState(1);
  const [maxTime, setMaxTime] = useState(240);
  const [content, setContent] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const data = {
        type,
        maxhits: maxHits,
        maxtime: maxTime,
      };

      if (type === 'text') {
        if (!content.trim()) {
          setError('Please enter some text');
          setLoading(false);
          return;
        }
        data.content = content;
      } else {
        if (!file) {
          setError('Please select a file');
          setLoading(false);
          return;
        }
        data.file = file;
      }

      const response = await shoutApi.createShout(data);

      if (response.success) {
        const fullUrl = utilsApi.getShoutUrl(type, response.hash);
        setResult({
          hash: response.hash,
          url: fullUrl,
          qrUrl: utilsApi.getQRCodeUrl(fullUrl),
        });
      } else {
        setError('Failed to create shout');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create shout');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(result.url);
    alert('URL copied to clipboard!');
  };

  if (result) {
    return (
      <div className="create-shout-container">
        <div className="result-card">
          <h2>Shout Created!</h2>
          <div className="result-content">
            <div className="qr-code">
              <img src={result.qrUrl} alt="QR Code" />
            </div>
            <div className="url-container">
              <input
                type="text"
                value={result.url}
                readOnly
                className="url-input"
              />
              <button onClick={copyToClipboard} className="copy-button">
                Copy URL
              </button>
            </div>
            <button
              onClick={() => navigate(result.url.replace(window.location.origin, ''))}
              className="view-button"
            >
              View Shout
            </button>
            <button onClick={() => navigate('/')} className="home-button">
              Create Another
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="create-shout-container">
      <div className="create-shout-card">
        <h1>Create Ephemeral Content</h1>

        <form onSubmit={handleSubmit} className="shout-form">
          <div className="form-group">
            <label>Content Type</label>
            <select value={type} onChange={(e) => setType(e.target.value)} className="form-select">
              <option value="text">Text</option>
              <option value="audio">Audio</option>
              <option value="video">Video</option>
              <option value="photo">Photo</option>
            </select>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Max Views</label>
              <input
                type="number"
                value={maxHits}
                onChange={(e) => setMaxHits(parseInt(e.target.value))}
                min="1"
                max="100"
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label>Max Time (minutes)</label>
              <input
                type="number"
                value={maxTime}
                onChange={(e) => setMaxTime(parseInt(e.target.value))}
                min="1"
                max="1440"
                className="form-input"
              />
            </div>
          </div>

          {type === 'text' ? (
            <div className="form-group">
              <label>Your Message</label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Enter your message..."
                rows="6"
                className="form-textarea"
              />
            </div>
          ) : (
            <div className="form-group">
              <label>Select File</label>
              <input
                type="file"
                onChange={handleFileChange}
                accept={
                  type === 'audio'
                    ? 'audio/*'
                    : type === 'video'
                    ? 'video/*'
                    : 'image/*'
                }
                className="form-file"
              />
              {file && <p className="file-name">{file.name}</p>}
            </div>
          )}

          {error && <div className="error-message">{error}</div>}

          <div className="button-group">
            <button
              type="submit"
              disabled={loading}
              className="submit-button"
            >
              {loading ? 'Creating...' : 'Create Shout'}
            </button>
            <button
              type="button"
              onClick={() => navigate('/')}
              className="cancel-button"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CreateShout;
