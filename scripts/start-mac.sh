#!/usr/bin/env bash
set -euo pipefail

echo "Starting Project Management MVP..."
docker compose up --build -d

echo "App started at http://localhost:8000"
