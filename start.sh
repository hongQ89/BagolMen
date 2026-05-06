#!/bin/bash

# Bagol Addon Startup Script
# Runs in development or production mode

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
MODE="${1:-development}"
PORT="${FLASK_PORT:-8008}"
WORKERS="${GUNICORN_WORKERS:-4}"
HOST="${FLASK_HOST:-0.0.0.0}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Bagol Stremio Addon${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Mode:${NC} $MODE"
echo -e "${YELLOW}Host:${NC} $HOST"
echo -e "${YELLOW}Port:${NC} $PORT"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python3 not found${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${YELLOW}Python:${NC} $PYTHON_VERSION"
echo ""

# Check dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"
if ! python3 -c "import flask; import bs4; import requests" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

echo -e "${GREEN}✓ Dependencies OK${NC}"
echo ""

# Create logs directory
mkdir -p logs

# Run in selected mode
if [ "$MODE" = "development" ]; then
    echo -e "${GREEN}Starting in DEVELOPMENT mode${NC}"
    echo -e "${YELLOW}Access addon at:${NC} http://localhost:$PORT/manifest.json"
    echo ""
    
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    python3 addon.py
    
elif [ "$MODE" = "production" ]; then
    echo -e "${GREEN}Starting in PRODUCTION mode${NC}"
    echo -e "${YELLOW}Access addon at:${NC} http://localhost:$PORT/manifest.json"
    echo -e "${YELLOW}Workers:${NC} $WORKERS"
    echo ""
    
    gunicorn \
        --bind "${HOST}:${PORT}" \
        --workers "${WORKERS}" \
        --worker-class sync \
        --timeout 120 \
        --access-logfile logs/access.log \
        --error-logfile logs/error.log \
        --log-level info \
        addon:app
    
else
    echo -e "${RED}ERROR: Unknown mode '$MODE'${NC}"
    echo -e "${YELLOW}Usage: ./start.sh [development|production]${NC}"
    exit 1
fi
