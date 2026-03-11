@echo off
setlocal

echo Starting Project Management MVP...
docker compose up --build -d
if %errorlevel% neq 0 (
  echo Failed to start containers.
  exit /b %errorlevel%
)

echo App started at http://localhost:8000
