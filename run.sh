#!/usr/bin/env bash
# Starts the API (port 8000) and the UI (port 8501).
set -e
cd "$(dirname "$0")"
uvicorn app.main:app --port 8000 &
API_PID=$!
trap "kill $API_PID" EXIT
streamlit run ui.py
