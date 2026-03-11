#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://localhost:8000"

echo "[1/5] Checking containers..."
docker compose ps >/dev/null

echo "[2/5] Checking health endpoint..."
HEALTH="$(curl -fsS "$BASE_URL/api/health")"
if [[ "$HEALTH" != '{"status":"ok"}' ]]; then
  echo "Unexpected health payload: $HEALTH"
  exit 1
fi

echo "[3/5] Checking root endpoint status..."
STATUS="$(curl -o /dev/null -s -w "%{http_code}" "$BASE_URL/")"
if [[ "$STATUS" != "200" ]]; then
  echo "Unexpected root status: $STATUS"
  exit 1
fi

echo "[4/5] Checking root page content markers..."
ROOT_CONTENT="$(curl -fsS "$BASE_URL/")"
if [[ "$ROOT_CONTENT" != *"Project Management MVP"* ]] || [[ "$ROOT_CONTENT" != *"Kanban board preview"* ]]; then
  echo "Root content validation failed"
  exit 1
fi

echo "[5/5] Running backend tests with coverage gate..."
docker compose exec app uv run python -m pytest

echo "Part 3 verification PASSED."