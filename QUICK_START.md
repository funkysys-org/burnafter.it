# Quick Start Guide

Get BurnAfterIt v2.0 running in 5 minutes!

## Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Docker and Docker Compose (for production)
- Supabase account (free tier works)

## 1. Get Supabase Credentials

1. Go to https://supabase.com and create a free account
2. Create a new project
3. Go to Project Settings → API
4. Copy:
   - Project URL
   - `anon` `public` key

## 2. Configure Environment

```bash
# Copy the example file
cp .env.example .env

# Edit .env and paste your Supabase credentials
nano .env  # or use your favorite editor
```

Your `.env` should look like:
```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
VITE_API_URL=http://localhost:5000
VITE_APP_URL=http://localhost:5173
```

## 3. Set Up Supabase Storage

In your Supabase dashboard:

1. Go to **Storage** in the left sidebar
2. Click **New bucket**
3. Name it `shouts`
4. Check **Public bucket**
5. Click **Create bucket**

Or run the SQL from `setup-storage.sql` in the SQL Editor.

## 4. Database Migration (Already Done!)

The database schema has already been applied to your Supabase project during setup.

## 5. Start the Application

### Option A: Development Mode (Recommended for testing)

```bash
chmod +x start-dev.sh
./start-dev.sh
```

This will:
- Install Python dependencies
- Install Node dependencies
- Start the backend on http://localhost:5000
- Start the frontend on http://localhost:5173

### Option B: Docker Mode (Production-ready)

```bash
chmod +x start-docker.sh
./start-docker.sh
```

This will:
- Build Docker images
- Start both containers
- Frontend at http://localhost:3000
- Backend at http://localhost:5000

## 6. Test It Out!

1. Open http://localhost:5173 (dev) or http://localhost:3000 (docker)
2. Click on **SEC** to share ephemeral content
3. Create a text message that expires after 1 view
4. Copy the URL or scan the QR code
5. Open in a new tab and view it
6. Try to view it again - it should be gone!

## Common Issues

### Port Already in Use
```bash
# Check what's using port 5000
lsof -i :5000

# Kill the process or change the port in .env
```

### Supabase Connection Error
- Verify your credentials in `.env`
- Check that the URL doesn't have trailing slash
- Ensure your Supabase project is active

### Storage Upload Fails
- Make sure the `shouts` bucket exists
- Verify it's set to **public**
- Check the policies in Supabase dashboard

### Module Not Found (Python)
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Module Not Found (Node)
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## What's Next?

- Read `README.new.md` for complete documentation
- Check `PROJECT_SUMMARY.md` for architecture details
- See `MIGRATION_GUIDE.md` if migrating from v1
- Explore the API at http://localhost:5000

## Quick Commands

```bash
# Development
./start-dev.sh                    # Start dev servers
Ctrl+C                            # Stop servers

# Docker
./start-docker.sh                 # Start containers
docker-compose logs -f            # View logs
docker-compose ps                 # Check status
docker-compose down               # Stop containers
docker-compose restart            # Restart

# Backend only
cd backend
source venv/bin/activate
python -m backend.app_api

# Frontend only
cd frontend
npm run dev

# Run cleanup manually
curl -X POST http://localhost:5000/api/admin/cleanup
```

## Architecture at a Glance

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       │ HTTP
       ▼
┌─────────────┐      ┌──────────────┐
│   React     │─────▶│  Flask API   │
│  Frontend   │◀─────│   Backend    │
│ (Port 5173) │      │ (Port 5000)  │
└─────────────┘      └───────┬──────┘
                             │
                             │ API Calls
                             ▼
                     ┌───────────────┐
                     │   Supabase    │
                     │ (PostgreSQL + │
                     │    Storage)   │
                     └───────────────┘
```

## Features

- ✅ Share text, audio, video, photos
- ✅ Auto-expire after views or time
- ✅ Ephemeral secure chat rooms
- ✅ QR code generation
- ✅ Mobile responsive
- ✅ Modern, beautiful UI
- ✅ Docker deployment
- ✅ Automatic cleanup

## Support

Having issues? Check:
1. `.env` is configured correctly
2. Supabase storage bucket exists
3. Ports 5000 and 5173/3000 are available
4. Database migration ran successfully
5. Logs: `docker-compose logs -f` (Docker) or check terminal (dev)

Happy burning! 🔥
