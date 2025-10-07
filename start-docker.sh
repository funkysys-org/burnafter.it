#!/bin/bash

echo "🐳 Starting BurnAfterIt with Docker"
echo "====================================="

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "Please copy .env.example to .env and configure your Supabase credentials"
    exit 1
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Please install Docker from https://www.docker.com/get-started"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed"
    echo "Please install Docker Compose"
    exit 1
fi

echo "Building and starting containers..."
docker-compose up -d --build

echo ""
echo "✅ Application started!"
echo "====================================="
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:5000"
echo "====================================="
echo ""
echo "Useful commands:"
echo "  docker-compose logs -f          # View logs"
echo "  docker-compose ps               # Check status"
echo "  docker-compose down             # Stop all services"
echo "  docker-compose restart          # Restart services"
