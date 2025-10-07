# BurnAfterIt v2.0

Modern full-stack ephemeral content sharing platform with self-destructing messages.

## Features

- **SEC (Share Ephemeral Content)**: Share text, audio, video, or photos that expire after views or time
- **ESC (Ephemeral Secure Chat)**: Temporary chat rooms with auto-expiring messages
- **S3-Compatible Storage**: Use Minio, AWS S3, DigitalOcean Spaces, or any S3-compatible provider
- **Supabase Database**: PostgreSQL with Row Level Security
- **Docker Support**: Complete containerized deployment
- **Modern UI**: React + Vite frontend with beautiful gradients

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose
- Supabase account (free tier: https://supabase.com)
- S3-compatible storage (Minio included, or use AWS S3, etc.)

### 2. Setup

```bash
# Clone and enter directory
cd burnafterit

# Copy environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 3. Configure Storage

**Option A: Use included Minio (easiest)**
1. Edit `docker-compose.yml` - remove `profiles: ["minio"]` from minio service (line 26)
2. In `.env`, use:
```
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=burnafterit
S3_USE_SSL=False
```

**Option B: Use AWS S3 or other provider**
See [STORAGE_SETUP.md](STORAGE_SETUP.md) for detailed instructions.

### 4. Start Application

```bash
# Using Docker (recommended)
./start-docker.sh

# Or for development
./start-dev.sh
```

### 5. Create Minio Bucket (if using Minio)

- Open http://localhost:9001
- Login: `minioadmin` / `minioadmin`
- Create bucket: `burnafterit`
- Set to Public

### 6. Access

- **Frontend**: http://localhost:3000 (Docker) or http://localhost:5173 (dev)
- **Backend API**: http://localhost:5000
- **Minio Console**: http://localhost:9001 (if using Minio)

## Documentation

- **[QUICK_START.md](QUICK_START.md)** - Detailed setup guide
- **[STORAGE_SETUP.md](STORAGE_SETUP.md)** - Storage configuration (Minio/S3/etc)
- **[STORAGE_QUICK_SETUP.md](STORAGE_QUICK_SETUP.md)** - Quick storage setup
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Architecture and changes
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Migrating from v1
- **[FILE_STRUCTURE.txt](FILE_STRUCTURE.txt)** - Complete file structure

## Architecture

```
┌─────────────┐
│   React     │ ← Vite + Modern UI
│  Frontend   │
└──────┬──────┘
       │
       │ REST API
       ▼
┌─────────────┐
│   Flask     │ ← Modular API
│  Backend    │
└──────┬──────┘
       │
       ├──────────┐
       │          │
       ▼          ▼
┌──────────┐  ┌─────────┐
│ Supabase │  │ Minio/  │
│ Database │  │ AWS S3  │
└──────────┘  └─────────┘
```

## Technology Stack

- **Frontend**: React, Vite, React Router, Axios
- **Backend**: Flask, boto3, Supabase client
- **Database**: PostgreSQL (Supabase)
- **Storage**: Any S3-compatible (Minio, AWS S3, DigitalOcean Spaces, etc.)
- **Deployment**: Docker, Docker Compose

## Storage Options

- **Minio** (Self-hosted, included)
- **AWS S3** (Most reliable)
- **DigitalOcean Spaces** (Simple pricing)
- **Backblaze B2** (Cheapest)
- **Any S3-compatible provider**

See [STORAGE_SETUP.md](STORAGE_SETUP.md) for configuration details.

## Environment Variables

```bash
# Database (Supabase)
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Storage (S3-compatible)
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=burnafterit
S3_REGION=us-east-1
S3_USE_SSL=False

# API URLs
VITE_API_URL=http://localhost:5000
VITE_APP_URL=http://localhost:3000
```

## API Endpoints

- `POST /api/shouts/create` - Create ephemeral content
- `GET /api/shouts/:hash` - View content (increments counter)
- `POST /api/chat/create` - Create chat room
- `GET /api/chat/:hash/messages` - Get messages
- `POST /api/chat/:hash/message` - Post message
- `GET /api/utils/qr` - Generate QR code
- `POST /api/admin/cleanup` - Run cleanup

## Security Features

- Input validation and sanitization
- Row Level Security (RLS) on database
- Automatic content expiration
- CORS protection
- XSS prevention
- Presigned URLs for media access

## Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m backend.app_api

# Frontend
cd frontend
npm install
npm run dev
```

## Production Deployment

```bash
# Start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## License

See LICENSE file

## Support

Having issues? Check:
1. `.env` is configured correctly
2. Storage bucket exists and is accessible
3. Supabase database migration ran successfully
4. All required ports are available

For detailed help, see the documentation files listed above.
