#!/bin/bash

# Navigate to the project root directory first
PROJECT_ROOT=$(cd "$(dirname "$0")" && pwd)

# Attempt to load Node.js environment variables (NVM or standard profiles)
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

source ~/.profile 2>/dev/null || true
source ~/.bashrc 2>/dev/null || true

# Activate virtual environment if it exists
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
elif [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Start the frontend server in the background
echo "Starting Open Nail Printer frontend server..."
cd "$PROJECT_ROOT/frontend" || exit
nohup npm run preview -- --host 0.0.0.0 --port 5173 > "$PROJECT_ROOT/frontend.log" 2>&1 &

# Navigate to the backend directory
cd "$PROJECT_ROOT/backend" || exit

echo "Starting Open Nail Printer backend server..."
echo "API will be available at http://localhost:8000"

# Run the FastAPI server using Uvicorn via python -m to ensure it uses the venv
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
