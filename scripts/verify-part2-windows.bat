@echo off
setlocal enabledelayedexpansion

set "BASE_URL=http://localhost:8000"
if "%PART2_STRICT_ROOT%"=="" set "PART2_STRICT_ROOT=0"

echo [1/5] Checking containers...
docker compose ps >nul 2>&1
if %errorlevel% neq 0 (
  echo Docker compose is not available or stack is not initialized.
  exit /b %errorlevel%
)

echo [2/5] Checking health endpoint...
for /f "delims=" %%i in ('powershell -NoProfile -Command "try { $o=(Invoke-WebRequest -Uri '%BASE_URL%/api/health' -UseBasicParsing).Content | ConvertFrom-Json; if($o.status -eq 'ok'){ 'ok' } else { exit 1 } } catch { exit 1 }"') do set "HEALTH_OK=%%i"
if %errorlevel% neq 0 (
  echo Health endpoint check failed.
  exit /b 1
)
if /i not "!HEALTH_OK!"=="ok" (
  echo Unexpected health payload.
  exit /b 1
)

echo [3/5] Checking root endpoint status...
for /f "delims=" %%i in ('powershell -NoProfile -Command "try {(Invoke-WebRequest -Uri '%BASE_URL%/' -UseBasicParsing).StatusCode} catch { exit 1 }"') do set "STATUS=%%i"
if %errorlevel% neq 0 (
  echo Root endpoint status check failed.
  exit /b 1
)
if not "!STATUS!"=="200" (
  echo Unexpected root status: !STATUS!
  exit /b 1
)

echo [4/5] Checking root page content markers...
for /f "delims=" %%i in ('powershell -NoProfile -Command "try { $c=(Invoke-WebRequest -Uri '%BASE_URL%/' -UseBasicParsing).Content; $isPart2=($c -match 'Hello world from FastAPI inside Docker\.' -and $c -match 'fetch\(''/api/health''\)'); $isPart3=($c -match '<html' -and $c -match '/_next/static/'); if('%PART2_STRICT_ROOT%' -eq '1'){ if($isPart2){ 'ok' } else { exit 1 } } else { if($isPart2 -or $isPart3){ 'ok' } else { exit 1 } } } catch { exit 1 }"') do set "HTML_OK=%%i"
if %errorlevel% neq 0 (
  echo Root content validation failed.
  if "%PART2_STRICT_ROOT%"=="1" echo Expected strict Part 2 hello page markers.
  if not "%PART2_STRICT_ROOT%"=="1" echo Expected either Part 2 hello page markers or Part 3 Next.js markers.
  exit /b 1
)
if /i not "!HTML_OK!"=="ok" (
  echo Root content validation failed.
  exit /b 1
)

echo [5/5] Running backend tests with coverage gate...
docker compose exec app uv run python -m pytest
if %errorlevel% neq 0 (
  echo Test run failed.
  exit /b %errorlevel%
)

echo Part 2 verification PASSED.
