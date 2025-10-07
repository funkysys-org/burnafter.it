import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { chatApi } from '../api/chat';
import { utilsApi } from '../api/utils';
import './ChatRoom.css';

function ChatRoom() {
  const { hash } = useParams();
  const navigate = useNavigate();

  const [chatHash, setChatHash] = useState(hash || null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showQR, setShowQR] = useState(false);

  const [messageText, setMessageText] = useState('');
  const [sending, setSending] = useState(false);

  const messagesEndRef = useRef(null);
  const pollIntervalRef = useRef(null);

  useEffect(() => {
    if (chatHash) {
      loadChatRoom();
      startPolling();
    } else {
      setLoading(false);
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [chatHash]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadChatRoom = async () => {
    try {
      const result = await chatApi.getChatRoom(chatHash);
      if (result.success) {
        loadMessages();
      } else {
        setError('Chat room not found or expired');
        setLoading(false);
      }
    } catch (err) {
      setError('Failed to load chat room');
      setLoading(false);
    }
  };

  const loadMessages = async () => {
    try {
      const result = await chatApi.getChatMessages(chatHash);
      if (result.success) {
        setMessages(result.messages);
        setLoading(false);
      }
    } catch (err) {
      console.error('Failed to load messages:', err);
    }
  };

  const startPolling = () => {
    pollIntervalRef.current = setInterval(() => {
      loadMessages();
    }, 3000);
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();

    if (!messageText.trim()) return;

    setSending(true);

    try {
      await chatApi.postChatMessage(chatHash, {
        type: 'text',
        content: messageText,
        maxhits: 10,
        maxtime: 5,
      });

      setMessageText('');
      loadMessages();
    } catch (err) {
      alert('Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const copyRoomUrl = () => {
    const url = utilsApi.getChatUrl(chatHash);
    navigator.clipboard.writeText(url);
    alert('Chat room URL copied!');
  };

  if (!chatHash) {
    return (
      <div className="chat-container">
        <div className="chat-card">
          <h1>Ephemeral Secure Chat</h1>
          <p>Chat room not found. Would you like to create one?</p>
          <button onClick={() => navigate('/')} className="create-button">
            Go Home
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="chat-container">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Loading chat room...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="chat-container">
        <div className="chat-card">
          <h2>Error</h2>
          <p>{error}</p>
          <button onClick={() => navigate('/')} className="create-button">
            Go Home
          </button>
        </div>
      </div>
    );
  }

  const chatUrl = utilsApi.getChatUrl(chatHash);
  const qrUrl = utilsApi.getQRCodeUrl(chatUrl);

  return (
    <div className="chat-container">
      <div className="chat-room">
        <div className="chat-header">
          <h2>Secure Chat</h2>
          <div className="header-buttons">
            <button onClick={() => setShowQR(!showQR)} className="qr-button">
              {showQR ? 'Hide' : 'Share'} QR
            </button>
            <button onClick={copyRoomUrl} className="copy-button">
              Copy URL
            </button>
          </div>
        </div>

        {showQR && (
          <div className="qr-display">
            <img src={qrUrl} alt="QR Code" />
          </div>
        )}

        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <p>No messages yet. Start the conversation!</p>
            </div>
          ) : (
            messages.map((message) => (
              <div key={message.id} className="message">
                <div className="message-content">
                  {message.shouts?.type === 'text' && (
                    <p>{message.shouts.content_text}</p>
                  )}
                  {message.shouts?.type === 'audio' && message.shouts.media_url && (
                    <audio controls>
                      <source src={message.shouts.media_url} type="audio/wav" />
                    </audio>
                  )}
                  {message.shouts?.type === 'photo' && message.shouts.media_url && (
                    <img src={message.shouts.media_url} alt="Message" />
                  )}
                </div>
                <div className="message-time">
                  {new Date(message.created_at).toLocaleTimeString()}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSendMessage} className="message-input-form">
          <input
            type="text"
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
            placeholder="Type a message..."
            className="message-input"
            disabled={sending}
          />
          <button type="submit" disabled={sending || !messageText.trim()} className="send-button">
            {sending ? '...' : 'Send'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default ChatRoom;
