# BurnAfterIt v2.0

Modern full-stack ephemeral content sharing platform with self-destructing messages.

## Features

- **SEC (Share Ephemeral Content)**: Share text, audio, video, or photos that expire after a set number of views or time
- **ESC (Ephemeral Secure Chat)**: Create temporary chat rooms with auto-expiring messages
- **Modern Tech Stack**: React + Flask + Supabase
- **Docker Support**: Complete containerized deployment
- **Secure**: Content automatically expires, proper validation, and security headers

## Architecture

```
├── backend/          # Flask REST API
│   ├── api/         # API routes
│   ├── services/    # Business logic
│   ├── models/      # Data models
│   └── app_api.py   # Application entry point
├── frontend/         # React + Vite application
│   ├── src/
│   │   ├── pages/   # Page components
│   │   ├── api/     # API client
│   │   └── App.jsx
└── docker-compose.yml
```

## Technology Stack

### Backend
- **Flask** - Web framework
- **Supabase** - PostgreSQL database + storage
- **Python 3.11** - Runtime

### Frontend
- **React** - UI framework
- **Vite** - Build tool
- **Axios** - HTTP client
- **React Router** - Routing

### Database
- **PostgreSQL** (via Supabase) - Relational data
- **Supabase Storage** - Media file storage

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Supabase account

### Setup

1. **Clone the repository**
```bash
git clone <repo-url>
cd burnafterit
```

2. **Configure environment variables**
```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your Supabase credentials
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
```

3. **Set up Supabase Storage**

In your Supabase dashboard:
- Go to Storage
- Create a new bucket named `shouts`
- Set it to **public** access

4. **Start the application**
```bash
docker-compose up -d
```

5. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000

## Development Setup

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m backend.app_api
```

Backend will run on http://localhost:5000

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

Frontend will run on http://localhost:5173

## API Endpoints

### Shouts
- `POST /api/shouts/create` - Create a new shout
- `GET /api/shouts/<hash>` - Get a shout (increments view count)
- `GET /api/shouts/check/<hash>` - Check if shout exists

### Chat
- `POST /api/chat/create` - Create a chat room
- `GET /api/chat/<hash>` - Get chat room details
- `GET /api/chat/<hash>/messages` - Get chat messages
- `POST /api/chat/<hash>/message` - Post a message

### Utils
- `GET /api/utils/qr?url=<url>` - Generate QR code
- `GET /api/utils/health` - Health check

## Database Schema

The database includes:
- `shouts` - Main content table
- `chat_rooms` - Ephemeral chat rooms
- `chat_messages` - Messages in chat rooms
- `hit_logs` - View tracking

Row Level Security (RLS) is enabled on all tables.

## Deployment

### Docker Production Deployment

```bash
# Build and start containers
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

### Environment Variables

Backend:
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_ANON_KEY` - Your Supabase anon key
- `FLASK_ENV` - Environment (development/production)
- `CORS_ORIGINS` - Allowed CORS origins

Frontend:
- `VITE_API_URL` - Backend API URL
- `VITE_APP_URL` - Frontend application URL

## Security Features

- Input validation and sanitization
- Row Level Security (RLS) on database
- Automatic content expiration
- CORS protection
- XSS prevention
- Secure file upload handling

## Cleanup

The database includes a function `cleanup_expired_content()` that should be run periodically to:
- Mark expired shouts as inactive
- Delete old hit logs
- Remove expired chat rooms

You can set up a cron job or Supabase function to run this regularly.

## License

See LICENSE file for details.

## Original Version

This is a modernized rewrite of the original BurnAfterIt application. The original version used:
- InfluxDB (time-series database)
- Minio (S3-compatible storage)
- Redis (session storage)
- Monolithic Flask application

The new version uses:
- Supabase (PostgreSQL + Storage)
- Modular architecture
- Modern React frontend
- Docker containerization
