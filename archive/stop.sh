#!/bin/bash

# Shutdown script for Questrade Portfolio App
# Kills backend and frontend servers

echo "Stopping Questrade Portfolio App..."

set -o errexit
set -o nounset

cleanup_pid_file() {
  if [ -f .server_pids ]; then
    rm -f .server_pids || true
  fi
}

if [ -f .server_pids ]; then
  PIDS=$(cat .server_pids || true)
  BACKEND_PID=$(echo $PIDS | cut -d' ' -f1 || true)
  FRONTEND_PID=$(echo $PIDS | cut -d' ' -f2 || true)

  if [ ! -z "$BACKEND_PID" ]; then
    echo "Killing backend server (PID: $BACKEND_PID)..."
    kill -9 $BACKEND_PID 2>/dev/null || echo "Backend already stopped or PID not found"
  fi

  if [ ! -z "$FRONTEND_PID" ]; then
    echo "Killing frontend server (PID: $FRONTEND_PID)..."
    kill -9 $FRONTEND_PID 2>/dev/null || echo "Frontend already stopped or PID not found"
  fi

  cleanup_pid_file
  echo "Servers stopped (via .server_pids)."
else
  echo "No .server_pids file found. Using aggressive cleanup..."

  # Kill all ts-node-dev processes (backend)
  TS_NODE_PROCS=$(pgrep -f "ts-node-dev" 2>/dev/null || true)
  if [ ! -z "$TS_NODE_PROCS" ]; then
    echo "Killing ts-node-dev processes..."
    echo $TS_NODE_PROCS | xargs kill -9 2>/dev/null || true
  fi

  # Kill all vite processes (frontend)
  VITE_PROCS=$(pgrep -f "vite" 2>/dev/null || true)
  if [ ! -z "$VITE_PROCS" ]; then
    echo "Killing vite processes..."
    echo $VITE_PROCS | xargs kill -9 2>/dev/null || true
  fi

  # Kill processes on backend port
  BACKEND_PORT=${BACKEND_PORT:-3001}
  BACKEND_PROC=$(lsof -ti:$BACKEND_PORT 2>/dev/null || true)
  if [ ! -z "$BACKEND_PROC" ]; then
    echo "Killing process on port $BACKEND_PORT (PID: $BACKEND_PROC)..."
    kill -9 $BACKEND_PROC 2>/dev/null || true
  fi

  # Kill processes on any Vite port range (default 5173-5200 or env override)
  START_PORT=${VITE_START_PORT:-5173}
  END_PORT=${VITE_END_PORT:-5200}
  echo "Killing processes on ports $START_PORT-$END_PORT if present..."
  for port in $(seq $START_PORT $END_PORT); do
    PROC=$(lsof -ti:$port 2>/dev/null || true)
    if [ ! -z "$PROC" ]; then
      echo "Killing process on port $port (PID: $PROC)..."
      kill -9 $PROC 2>/dev/null || true
    fi
  done

  cleanup_pid_file
  echo "Aggressive cleanup complete."
fi

echo "Done. If ports are still occupied, run: pkill -9 -f ts-node-dev ; pkill -9 -f vite ; lsof -ti:3001 | xargs kill -9"