#!/usr/bin/env bash
# Starts Ollama (AI), the API (port 8000), and the React frontend (port 5173).
set -e
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start Ollama if installed (for AI categorization)
if command -v ollama &> /dev/null; then
    ollama serve &> /dev/null &
    OLLAMA_PID=$!
    echo "Ollama started (PID $OLLAMA_PID)"
fi

# Start API
python3 -m uvicorn app.main:app --port 8000 &
API_PID=$!
echo "API started on http://localhost:8000"

# Cleanup on exit
cleanup() {
    kill $API_PID 2>/dev/null
    kill $OLLAMA_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
}
trap cleanup EXIT

# Start React frontend
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi
npm run dev &
FRONTEND_PID=$!
echo "Frontend started on http://localhost:5173"

# Wait for any process to exit
wait
