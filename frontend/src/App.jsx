import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import CreateShout from './pages/CreateShout';
import ViewShout from './pages/ViewShout';
import ChatRoom from './pages/ChatRoom';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/create/:type" element={<CreateShout />} />
          <Route path="/stream/:type/:hash" element={<ViewShout />} />
          <Route path="/chat" element={<ChatRoom />} />
          <Route path="/chat/:hash" element={<ChatRoom />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
