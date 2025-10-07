#!/bin/bash

echo "🚀 Starting BurnAfterIt Development Environment"
echo "=============================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please copy .env.example to .env and configure your Supabase credentials"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '#' | xargs)

# Start backend
echo -e "\n${YELLOW}📦 Starting Backend...${NC}"
cd backend
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

echo "Starting Flask API on port 5000..."
python -m backend.app_api &
BACKEND_PID=$!
cd ..

# Wait a bit for backend to start
sleep 3

# Start frontend
echo -e "\n${YELLOW}🎨 Starting Frontend...${NC}"
cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing Node dependencies..."
    npm install
fi

echo "Starting Vite dev server on port 5173..."
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "\n${GREEN}✅ Development environment started!${NC}"
echo "=============================================="
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:5000"
echo "=============================================="
echo "Press Ctrl+C to stop all services"

# Handle Ctrl+C
trap "echo -e '\n${YELLOW}Stopping services...${NC}'; kill $BACKEND_PID $FRONTEND_PID; exit" INT

# Wait for processes
wait
