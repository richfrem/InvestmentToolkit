#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Launching Investment Screener...${NC}"

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed.${NC}"
    exit 1
fi

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed.${NC}"
    exit 1
fi

# Environment Check
if [ ! -f .env ] && [ -z "$QUESTRADE_REFRESH_TOKEN" ]; then
    echo -e "${YELLOW}Warning: No .env file found and QUESTRADE_REFRESH_TOKEN not set.${NC}"
    echo -e "${YELLOW}Please copy .env.example to .env and configure it.${NC}"
    # Not blocking for now as we use yfinance primarily
fi

# Portfolio Configuration Check
if [ ! -f frontend/src/data/portfolio.json ]; then
    echo -e "${YELLOW}Creating initial portfolio from example...${NC}"
    cp frontend/src/data/portfolio.json.example frontend/src/data/portfolio.json
fi

# Setup Python Virtual Environment
if [ ! -d "venv" ]; then
    echo -e "${GREEN}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

echo -e "${GREEN}Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install yfinance pandas uvicorn fastapi

# Install Node dependencies
echo -e "${GREEN}Installing Node dependencies...${NC}"
npm install

# Build Backend
echo -e "${GREEN}Building Backend...${NC}"
npm run build -w backend

# Start Services
echo -e "${GREEN}Starting Services...${NC}"

# Trap SIGINT to kill child processes
trap 'kill $(jobs -p)' SIGINT

# Start Backend
npm run start -w backend &
BACKEND_PID=$!

# Start Frontend (Dev Mode)
npm run dev -w frontend &
FRONTEND_PID=$!

echo -e "${GREEN}✅ Services Running!${NC}"
echo -e "Backend: http://localhost:3001"
echo -e "Frontend: http://localhost:5173"

wait $BACKEND_PID $FRONTEND_PID
