# Quick Start Guide

Get BurnAfterIt running locally in 5 minutes!

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 12+ (or use Docker)
- Minio (optional, or use Docker)

## Option 1: Docker (Easiest!)

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Enable Minio (remove line 46 in docker-compose.yml that says "profiles: ["minio"]")
nano docker-compose.yml

# 3. Start everything
docker-compose up -d

# 4. Create Minio bucket
# Open http://localhost:9001
# Login: minioadmin / minioadmin
# Create bucket: burnafterit (set to Public)

# 5. Done! Access at http://localhost:3000
```

## Option 2: Manual Setup

### Step 1: Database Setup

**Option A: Use Docker for PostgreSQL**
```bash
docker run -d \
  --name postgres \
  -e POSTGRES_DB=burnafterit \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:16-alpine

# Run migration
docker exec -i postgres psql -U postgres burnafterit < supabase/migrations/001_init_schema.sql
```

**Option B: Install PostgreSQL locally**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql@16
brew services start postgresql@16

# Create database
sudo -u postgres createdb burnafterit

# Run migration
sudo -u postgres psql burnafterit < supabase/migrations/001_init_schema.sql
```

### Step 2: Storage Setup

**Option A: Use Docker for Minio**
```bash
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# Create bucket at http://localhost:9001
```

**Option B: Download Minio**
```bash
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
./minio server /data --console-address ":9001"

# Create bucket at http://localhost:9001
```

### Step 3: Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env .env.local  # It's already configured for localhost
# OR edit .env if needed

# Start backend
python3 run.py
```

Backend should now be running on http://localhost:5000

### Step 4: Frontend Setup

Open a NEW terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend should now be running on http://localhost:5173

## Verification

1. **Backend**: http://localhost:5000 should show API info
2. **Frontend**: http://localhost:5173 should show the app
3. **Database**: `psql -U postgres -d burnafterit -c "\dt"` should list tables
4. **Minio**: http://localhost:9001 should show Minio console

## Common Issues

### Backend won't start

**Error: "No module named 'flask'"**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

**Error: "could not connect to server"**
```bash
# Check PostgreSQL is running
docker ps  # If using Docker
# OR
sudo systemctl status postgresql  # If installed locally

# Verify credentials in backend/.env
cat backend/.env | grep POSTGRES
```

**Error: "Missing required database environment variables"**
```bash
# Make sure backend/.env exists and has PostgreSQL credentials
cp .env.example backend/.env
nano backend/.env  # Edit if needed
```

### Frontend shows CORS error

This means the backend isn't running. Check:
```bash
# Test if backend is accessible
curl http://localhost:5000/api/utils/health

# If it fails, backend isn't running
# Go back to terminal running backend and check for errors
```

### Database connection error

```bash
# Test PostgreSQL connection
psql -h localhost -U postgres -d burnafterit -c "SELECT 1"

# If it asks for password, use: postgres
# If connection refused:
docker ps  # Check if postgres container is running
# OR
sudo systemctl start postgresql
```

### Storage upload fails

```bash
# Check Minio is running
curl http://localhost:9000/minio/health/live

# Check bucket exists
# Open http://localhost:9001 and verify 'burnafterit' bucket exists
```

## Environment Variables

Default configuration in `.env`:

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=burnafterit
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Storage
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=burnafterit
S3_USE_SSL=False

# Frontend (in frontend/.env)
VITE_API_URL=http://localhost:5000
VITE_APP_URL=http://localhost:5173
```

## Next Steps

1. **Create a shout**: Click "SEC" on homepage
2. **Test text shout**: Create with 1 max view
3. **Test media shout**: Upload a photo
4. **Create chat**: Click "ESC" on homepage
5. **Share the chat link**: Copy URL and open in new tab

## Stopping Services

**Docker:**
```bash
docker-compose down
```

**Manual:**
- Press Ctrl+C in backend terminal
- Press Ctrl+C in frontend terminal
- Stop PostgreSQL: `docker stop postgres` or `sudo systemctl stop postgresql`
- Stop Minio: `docker stop minio`

## Development Workflow

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
python3 run.py

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Database (optional)
psql -U postgres burnafterit
```

## Production Deployment

Use Docker Compose for production:

```bash
# Edit docker-compose.yml:
# - Change PostgreSQL password
# - Set FLASK_DEBUG=False
# - Use external S3 (not Minio)

docker-compose up -d --build
```

## Getting Help

- Check logs: `docker-compose logs -f backend`
- Database logs: `docker logs postgres`
- Test API: `curl http://localhost:5000`
- Check all services: `docker-compose ps`

Happy burning! 🔥
