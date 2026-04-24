#!/bin/bash
cd "$(dirname "$0")/frontend"

pio run &

# Navigate to the backend directory
cd "$(dirname "$0")/../backend" || exit

# Activate virtual environment if you have one (uncomment and modify if needed)
# source ../venv/bin/activate

echo "Starting Open Nail Printer backend server..."
echo "API will be available at http://localhost:8000"

# Run the FastAPI server using Uvicorn
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
