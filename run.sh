#!/bin/bash

# Define colors for pretty output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting OpenShorts...${NC}"

# Function to kill both processes when you press Ctrl+C
cleanup() {
    echo -e "\n${BLUE}🛑 Shutting down OpenShorts...${NC}"
    kill $BACKEND_PID
    kill $FRONTEND_PID
    exit
}

# Trap the specific exit signal (Ctrl+C)
trap cleanup SIGINT

# 1. Start the Backend (Python)
echo -e "${GREEN}--> Launching Backend...${NC}"
source venv/bin/activate
# Run in background (&) and save the Process ID ($!)
uvicorn app:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 2. Start the Frontend (React)
echo -e "${GREEN}--> Launching Dashboard...${NC}"
cd dashboard
# Run in background (&) and save the Process ID ($!)
npm run dev -- --host & 
FRONTEND_PID=$!

# 3. Tell the script to wait until you stop it
echo -e "${GREEN}✅ App is running! Go to: http://localhost:5173${NC}"
wait