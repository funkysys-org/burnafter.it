# Docker Backend Fix

## Problem
The backend container was failing with `ModuleNotFoundError: No module named 'backend'` because the Python path wasn't set up correctly.

## What Was Fixed

1. **Updated `backend/Dockerfile`**:
   - Changed `COPY . .` to `COPY . ./backend` to maintain proper directory structure
   - Set `PYTHONPATH=/app` environment variable
   - Changed CMD to use `python3 -m backend` instead of gunicorn with incorrect path

2. **Created `backend/__main__.py`**:
   - Entry point for running backend as a Python module
   - Handles port and debug settings from environment variables

3. **Updated `backend/run.py`**:
   - Improved path handling
   - Respects environment variables for port and debug mode

## How to Apply the Fix

Run these commands in the project root:

```bash
# Stop existing containers
docker-compose down

# Remove old backend image
docker rmi burnafterit-backend 2>/dev/null || true

# Rebuild and start everything
docker-compose up -d --build

# Check logs
docker-compose logs -f backend
```

## Verification

After starting, you should see:
```
burnafterit-backend  | WARNING: This is a development server. Do not use it in a production deployment.
burnafterit-backend  | * Running on all addresses (0.0.0.0)
burnafterit-backend  | * Running on http://127.0.0.1:5000
burnafterit-backend  | * Running on http://172.x.x.x:5000
```

Test the backend:
```bash
# Should return API info
curl http://localhost:5000/

# Should return health status
curl http://localhost:5000/api/utils/health
```

## Manual Development (Without Docker)

If you want to run locally without Docker:

```bash
# Terminal 1: Start PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_DB=burnafterit \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:16-alpine

# Apply migration
docker exec -i postgres psql -U postgres burnafterit < supabase/migrations/001_init_schema.sql

# Terminal 2: Start Minio
docker run -d --name minio \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# Terminal 3: Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 run.py

# Terminal 4: Frontend
cd frontend
npm install
npm run dev
```

## Structure Explanation

After the fix, inside the Docker container:
```
/app/
├── backend/
│   ├── __init__.py
│   ├── __main__.py       <- Entry point
│   ├── app_api.py
│   ├── config.py
│   ├── run.py
│   ├── api/
│   ├── models/
│   └── services/
└── requirements.txt
```

With `PYTHONPATH=/app`, Python can now properly import `backend.*` modules.

## Production Note

For production, consider using gunicorn with proper WSGI:

```dockerfile
# In Dockerfile, change CMD to:
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "backend.app_api:create_app()"]
```

But the current setup works fine for development and small-scale production.
