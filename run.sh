#!/usr/bin/env bash
# Starts Ollama (AI), the API (port 8000), and the UI (port 8501).
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
echo "API started (PID $API_PID)"

# Cleanup on exit
trap "kill $API_PID 2>/dev/null; kill $OLLAMA_PID 2>/dev/null" EXIT

# Start UI
python3 -m streamlit run ui.py --server.headless true
