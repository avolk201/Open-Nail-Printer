#!/bin/bash

echo "Stopping Open Nail Printer backend server..."

# Find the Process ID (PID) of the application listening on port 8000
PID=$(lsof -ti:8000)

if [ -n "$PID" ]; then
  # Kill the process
  kill -9 $PID
  echo "Server stopped (PID: $PID)."
else
  echo "No server found running on port 8000."
fi
