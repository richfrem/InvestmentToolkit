#!/bin/bash

# Startup script for Questrade Portfolio App
# Starts backend and frontend servers in background

echo "Starting Questrade Portfolio App..."

# Load environment variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | sed 's/#.*//' | xargs)
fi

# Default ports if not set
: ${BACKEND_PORT:=3001}
: ${FRONTEND_PORT:=5173}

# Prevent duplicate starts: kill any existing processes on target ports
echo "Ensuring ports $BACKEND_PORT and $FRONTEND_PORT are free..."
for p in $BACKEND_PORT $FRONTEND_PORT; do
  PROC=$(lsof -ti:$p 2>/dev/null)
  if [ ! -z "$PROC" ]; then
    echo "Killing process on port $p (PID: $PROC)..."
    kill -9 $PROC 2>/dev/null || true
  fi
done

# Start backend server
echo "Starting backend server on port $BACKEND_PORT..."
cd backend || exit 1
npm run dev &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend port to be bound (with timeout)
cd ..
timeout=10
count=0
while ! lsof -i :$BACKEND_PORT >/dev/null 2>&1; do
  sleep 1
  count=$((count+1))
  if [ $count -ge $timeout ]; then
    echo "Warning: backend did not bind to port $BACKEND_PORT after $timeout seconds"
    break
  fi
done

# Start frontend server
echo "Starting frontend server on port $FRONTEND_PORT..."
cd frontend || exit 1
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"
cd ..

# Save PIDs to file for shutdown script (atomic write)
printf "%s %s" "$BACKEND_PID" "$FRONTEND_PID" > .server_pids.tmp && mv .server_pids.tmp .server_pids

echo "Servers started!"
echo "Backend: http://localhost:$BACKEND_PORT"
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo "To stop servers, run: ./stop.sh"