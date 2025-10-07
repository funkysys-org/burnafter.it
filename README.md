# BurnAfterIt v2.0

Modern full-stack ephemeral content sharing platform with self-destructing messages.

## Features

- **SEC (Share Ephemeral Content)**: Share text, audio, video, or photos that expire after views or time
- **ESC (Ephemeral Secure Chat)**: Temporary chat rooms with auto-expiring messages
- **PostgreSQL Database**: Standalone or containerized PostgreSQL
- **S3-Compatible Storage**: Use Minio, AWS S3, DigitalOcean Spaces, or any S3-compatible provider
- **Docker Support**: Complete containerized deployment with PostgreSQL included
- **Modern UI**: React + Vite frontend with beautiful gradients

## Quick Start with Docker

### 1. Prerequisites

- Docker and Docker Compose
- That's it! PostgreSQL and Minio are included

### 2. Setup

```bash
# Clone and enter directory
cd burnafterit

# Copy environment file
cp .env.example .env

# Edit .env if you want to change defaults (optional)
nano .env
```

### 3. Start Everything

```bash
# Remove the profiles line from docker-compose.yml to enable Minio (line 46)
# Or use external S3

# Start all services
docker-compose up -d
```

This will start:
- PostgreSQL database (port 5432)
- Backend API (port 5000)
- Frontend (port 3000)
- Minio (ports 9000, 9001) - if enabled

### 4. Create Minio Bucket (if using Minio)

- Open http://localhost:9001
- Login: `minioadmin` / `minioadmin`
- Create bucket: `burnafterit`
- Set to Public

### 5. Access

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **PostgreSQL**: localhost:5432 (burnafterit/postgres/postgres)
- **Minio Console**: http://localhost:9001 (if enabled)

## Manual Setup (Development)

### 1. Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- PostgreSQL 12+
- S3-compatible storage (Minio recommended for dev)

### 2. Database Setup

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb burnafterit

# Run migration
sudo -u postgres psql burnafterit < supabase/migrations/001_init_schema.sql
```

### 3. Storage Setup

**Option A: Use Minio (easiest for dev)**
```bash
# Download and run Minio
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
./minio server /data --console-address ":9001"

# Create bucket at http://localhost:9001
```

**Option B: Use AWS S3 or other provider**
See [STORAGE_SETUP.md](STORAGE_SETUP.md)

### 4. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure .env
cp .env.example .env
# Edit .env with your database and storage credentials

# Run backend
python -m backend.app_api
```

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run frontend
npm run dev
```

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
│PostgreSQL│  │ Minio/  │
│ Database │  │ AWS S3  │
└──────────┘  └─────────┘
```

## Technology Stack

- **Frontend**: React, Vite, React Router, Axios
- **Backend**: Flask, psycopg2, boto3
- **Database**: PostgreSQL 12+
- **Storage**: Any S3-compatible (Minio, AWS S3, DigitalOcean Spaces, etc.)
- **Deployment**: Docker, Docker Compose

## Environment Variables

```bash
# PostgreSQL Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=burnafterit
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# S3-Compatible Storage
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

## Database Schema

The database includes:
- `shouts` - Main content table with expiration logic
- `chat_rooms` - Ephemeral chat rooms
- `chat_messages` - Messages in chat rooms
- `hit_logs` - View tracking for analytics

Functions:
- `increment_shout_hit()` - Atomic hit counting with validation
- `cleanup_expired_content()` - Cleanup expired content

## API Endpoints

- `POST /api/shouts/create` - Create ephemeral content
- `GET /api/shouts/:hash` - View content (increments counter)
- `POST /api/chat/create` - Create chat room
- `GET /api/chat/:hash/messages` - Get messages
- `POST /api/chat/:hash/message` - Post message
- `GET /api/utils/qr` - Generate QR code
- `POST /api/admin/cleanup` - Run cleanup

## Documentation

- **[STORAGE_SETUP.md](STORAGE_SETUP.md)** - Storage configuration (Minio/S3/etc)
- **[STORAGE_QUICK_SETUP.md](STORAGE_QUICK_SETUP.md)** - Quick storage setup
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Architecture overview
- **[CHANGELOG.md](CHANGELOG.md)** - Complete changelog

## Security Features

- Input validation and sanitization
- XSS prevention
- CORS configuration
- Automatic content expiration
- Presigned URLs for media access (5-minute expiry)
- Connection pooling for database

## Production Deployment

```bash
# Update docker-compose.yml with production settings
# - Change PostgreSQL password
# - Use external S3 (not Minio)
# - Set FLASK_DEBUG=False

# Start services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Database Backup

```bash
# Backup
docker exec burnafterit-postgres pg_dump -U postgres burnafterit > backup.sql

# Restore
docker exec -i burnafterit-postgres psql -U postgres burnafterit < backup.sql
```

## Cleanup

Run cleanup manually:
```bash
curl -X POST http://localhost:5000/api/admin/cleanup
```

Or schedule with cron:
```bash
# Add to crontab
*/30 * * * * curl -X POST http://localhost:5000/api/admin/cleanup
```

## Troubleshooting

### PostgreSQL connection refused
- Check PostgreSQL is running: `docker ps` or `systemctl status postgresql`
- Verify credentials in `.env`
- Check port 5432 is not in use

### Storage upload fails
- Verify S3 endpoint is accessible
- Check bucket exists
- Confirm credentials are correct

### Database migrations not applied
- Migrations run automatically in Docker
- For manual setup: `psql burnafterit < supabase/migrations/001_init_schema.sql`

## License

See LICENSE file

## Support

Issues? Check:
1. `.env` is configured correctly
2. PostgreSQL is running and accessible
3. Storage bucket exists and is accessible
4. All required ports are available (5432, 5000, 3000, 9000, 9001)

For detailed help, see the documentation files listed above.
