#!/bin/bash
# Phone mode: open the website on your phone over Wi-Fi, protected by a secret key.
# Use it only while testing, then press Ctrl+C. Stop the normal servers first.
set -euo pipefail
cd "$(dirname "$0")/.."

IP=$(ipconfig getifaddr en0 || true)
[ -z "$IP" ] && { echo "No Wi-Fi address found (en0)."; exit 1; }
if lsof -nP -iTCP:3000 -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Ports 3000/8000 are in use: stop the normal website/API first."; exit 1
fi
KEY=$(openssl rand -hex 12)

PHONE_KEY=$KEY EXTRA_ORIGIN="http://$IP:3000" .venv/bin/uvicorn api.main:app --host "$IP" --port 8000 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT

echo
echo "  Open on your phone (same Wi-Fi):  http://$IP:3000/ko?key=$KEY"
echo "  Anyone without this link gets 401. Press Ctrl+C to stop everything."
echo
cd web && PHONE_KEY=$KEY LAN_HOST=$IP NEXT_PUBLIC_API_URL="http://$IP:8000" npx next dev --hostname "$IP" --port 3000
