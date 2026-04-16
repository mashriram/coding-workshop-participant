#!/usr/bin/env bash
# Script: Comprehensive Local Development Environment Startup
# Purpose: Start the production-ready Docker deployment for VDI evaluation.
# Usage: ./start-dev.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" > /dev/null 2>&1 || exit 1; pwd -P)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." > /dev/null 2>&1 || exit 1; pwd -P)"

echo "==================================================="
echo "VDI Environment Startup via Docker Cluster"
echo "==================================================="
echo ""

# Ensure docker is ready
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running or accessible. Please ensure Docker is started in the VDI."
    exit 1
fi

cd "$PROJECT_ROOT"

# Run the production deployment script that successfully provisions the DB, Backend, and Frontend
echo "Executing robust Docker cluster deployment..."
chmod +x ./run-production.sh
./run-production.sh

echo ""
echo "VDI Deploy Complete! Application exposed as configured in your Docker stack."
