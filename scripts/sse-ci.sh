#!/usr/bin/env bash
set -euo pipefail

PORT=${PORT:-8000}

echo "Starting server on port ${PORT}..."
python webapp/app.py &
SERVER_PID=$!

cleanup() {
  echo "Stopping server (PID: ${SERVER_PID})..."
  kill ${SERVER_PID} || true
}
trap cleanup EXIT

echo "Waiting for http://localhost:${PORT} ..."
for i in {1..60}; do
  if curl -sf "http://localhost:${PORT}/" >/dev/null; then
    echo "Server is up."
    break
  fi
  sleep 1
done

echo "Installing Playwright browsers (chromium) if needed..."
npx --yes playwright install chromium

echo "Running E2E tests..."
npx --yes playwright test webapp/e2e

