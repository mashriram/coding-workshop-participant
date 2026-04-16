#!/bin/bash
set -e

echo "🚀 Starting ACME Performance Production Deployment..."

# 1. Clean up existing containers
echo "🧹 Cleaning up old containers..."
docker compose down -v --remove-orphans

# 2. Build and Start
echo "🏗️ Building and starting services..."
docker compose up -d --build

# 3. Wait for Backend/DB to be ready
echo "⏳ Waiting for services to initialize..."
until [ "$(docker inspect -f '{{.State.Health.Status}}' acme-db)" == "healthy" ]; do
    echo "  - Waiting for Database..."
    sleep 3
done

# Wait for backend to be ready
echo "  - Waiting for Backend..."
sleep 5

# 4. Seed the Database
echo "🌱 Seeding sample data..."
docker exec acme-backend python seed_all.py

echo ""
echo "✨ SUCCESSFULLY DEPLOYED!"
echo "------------------------------------------------"
echo "URL:      http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo "Admin:    admin@acme.com / Admin@1234"
echo "HR:       hr@acme.com / HR@1234"
echo "Manager:  manager@acme.com / Manager@1234"
echo "------------------------------------------------"
