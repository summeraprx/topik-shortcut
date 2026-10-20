#!/bin/bash
# Start the website + AI API on this Mac only. Free and local: no paid API, nothing reachable
# from other devices (127.0.0.1), Next.js telemetry off. Press Ctrl+C once to stop both.
set -euo pipefail
cd "$(dirname "$0")/.."
export NEXT_TELEMETRY_DISABLED=1

if lsof -nP -iTCP:3000 -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Ports 3000/8000 are already in use (website or phone mode already running?). Stop it first."; exit 1
fi
if ! curl -s -m 2 http://127.0.0.1:11434/api/version >/dev/null; then
  echo "Note: Ollama is not running -> Ask TOPIK and the AI spelling check will not work."
  echo "      Open the Ollama app, then start this again. (Analysis pages work without it.)"
fi
[ -f data/web/grammar.json ] || .venv/bin/python -m pipeline.export_web

.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000 --log-level warning &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT

echo
echo "  Website: http://127.0.0.1:3000/ko   (this Mac only)"
echo "  Press Ctrl+C to stop everything."
echo
cd web && npx next dev --hostname 127.0.0.1 --port 3000
