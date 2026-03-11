@echo off
setlocal

echo Stopping Project Management MVP...
docker compose down
if %errorlevel% neq 0 (
  echo Failed to stop containers.
  exit /b %errorlevel%
)

echo App stopped.
