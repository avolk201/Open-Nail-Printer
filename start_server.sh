#!/bin/bash

# Navigate to the project root directory first
PROJECT_ROOT=$(cd "$(dirname "$0")" && pwd)

# Activate virtual environment if it exists
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
elif [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Start the frontend server in the background
echo "Starting Open Nail Printer frontend server..."
cd "$PROJECT_ROOT/frontend" || exit
npm run preview -- --host 0.0.0.0 --port 5173 &

# Navigate to the backend directory
cd "$PROJECT_ROOT/backend" || exit

echo "Starting Open Nail Printer backend server..."
echo "API will be available at http://localhost:8000"

# Run the FastAPI server using Uvicorn via python -m to ensure it uses the venv
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
