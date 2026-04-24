#!/bin/bash

echo "Stopping Open Nail Printer services..."

# Find the Process ID (PID) of the application listening on port 8000
BACKEND_PID=$(lsof -ti:8000)

if [ -n "$BACKEND_PID" ]; then
  # Kill the process
  kill -9 $BACKEND_PID
  echo "Backend server stopped (PID: $BACKEND_PID)."
else
  echo "No server found running on port 8000."
fi

# Find the Process ID (PID) of the frontend application listening on port 5173
FRONTEND_PID=$(lsof -ti:5173)

if [ -n "$FRONTEND_PID" ]; then
  # Kill the process
  kill -9 $FRONTEND_PID
  echo "Frontend server stopped (PID: $FRONTEND_PID)."
else
  echo "No frontend server found running on port 5173."
fi
