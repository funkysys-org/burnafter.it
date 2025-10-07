#!/bin/bash

echo "🔥 Starting BurnAfterIt with Docker..."
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found, creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file"
fi

# Stop and remove old containers
echo "📦 Cleaning up old containers..."
docker-compose down 2>/dev/null

# Remove old backend image to ensure rebuild
echo "🗑️  Removing old backend image..."
docker rmi burnafterit-backend 2>/dev/null || true

# Build and start all services
echo "🏗️  Building and starting services..."
docker-compose up -d --build

# Wait for services to start
echo ""
echo "⏳ Waiting for services to start..."
sleep 5

# Check status
echo ""
echo "📊 Service Status:"
docker-compose ps

# Show backend logs
echo ""
echo "📋 Backend logs (last 20 lines):"
docker-compose logs --tail=20 backend

echo ""
echo "✅ Setup complete!"
echo ""
echo "📍 Access points:"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:5000"
echo "   - PostgreSQL: localhost:5432 (user: postgres, pass: postgres, db: burnafterit)"
echo "   - Minio Console: http://localhost:9001 (if enabled)"
echo ""
echo "⚠️  Remember to:"
echo "   1. Enable Minio by removing 'profiles: [\"minio\"]' from docker-compose.yml line 46"
echo "   2. Create 'burnafterit' bucket at http://localhost:9001 (minioadmin/minioadmin)"
echo ""
echo "📖 View logs: docker-compose logs -f"
echo "🛑 Stop all: docker-compose down"
