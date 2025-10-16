#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

ENVFILE="$DIR/app/scripts/.env.local"
STREAMLIT_PORT=8501
API_PORT=8000

# Read ports from .env.local if present
if [[ -f "$ENVFILE" ]]; then
  while IFS='=' read -r k v; do
    [[ -z "${k:-}" || "${k:0:1}" == "#" ]] && continue
    if [[ "$k" == "STREAMLIT_PORT" ]]; then STREAMLIT_PORT="$v"; fi
    if [[ "$k" == "API_PORT" ]]; then API_PORT="$v"; fi
  done < "$ENVFILE"
fi

mkdir -p "$DIR/logs"

if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display dialog "Python 3 is not installed. Install it first." buttons {"OK"} default button 1'
  exit 1
fi

# Start FastAPI if exists
if [[ -f "$DIR/app/api/main.py" ]]; then
  nohup python3 -m uvicorn app.api.main:app --host 127.0.0.1 --port "$API_PORT" --reload \
    > "$DIR/logs/api.log" 2>&1 &
fi

# Start Streamlit UI
if [[ -f "$DIR/app/ui_app.py" ]]; then
  nohup python3 -m streamlit run "app/ui_app.py" --server.port "$STREAMLIT_PORT" --server.headless true \
    > "$DIR/logs/ui.log" 2>&1 &
else
  osascript -e 'display dialog "app/ui_app.py not found." buttons {"OK"} default button 1'
  exit 1
fi

# Open browser
open "http://localhost:${STREAMLIT_PORT}"

osascript -e 'display notification "App started on localhost" with title "Hudson’s App"'
read -p "🚀 Launched. Close this window; app keeps running. Use “Stop App (mac).command” to stop. Press Return... "
