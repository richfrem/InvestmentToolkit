#!/bin/bash
# Stop servers on port 3001 (Backend) and 5173 (Frontend)
lsof -ti:3001 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
echo "Servers stopped."
