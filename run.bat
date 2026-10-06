@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo          AutoCompliant-ML - Docker Runner
echo =======================================================
echo.

:: Check if Docker is installed and running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running or not installed!
    echo Please make sure Docker Desktop is started and try again.
    echo.
    pause
    exit /b 1
)

echo Select run mode:
echo [1] Start Web Dashboard (Default - Port 8000)
echo [2] Run Multi-Objective Optimization Job (NSGA-II + TOPSIS)
echo [3] Run Model Zoo Benchmark Job
echo [4] Rebuild Docker Images (docker compose build)
echo [5] Stop all running containers
echo.

set /p CHOICE="Enter choice [1-5] (default is 1): "
if "%CHOICE%"=="" set CHOICE=1

if "%CHOICE%"=="1" (
    echo.
    echo [INFO] Starting WebUI Dashboard at http://localhost:8000 ...
    docker compose up web
) else if "%CHOICE%"=="2" (
    echo.
    echo [INFO] Running optimization job in container...
    docker compose run --rm optimizer
) else if "%CHOICE%"=="3" (
    echo.
    echo [INFO] Running benchmark job in container...
    docker compose run --rm benchmark
) else if "%CHOICE%"=="4" (
    echo.
    echo [INFO] Building / Rebuilding Docker images...
    docker compose build
) else if "%CHOICE%"=="5" (
    echo.
    echo [INFO] Stopping containers...
    docker compose down
) else (
    echo [WARNING] Invalid choice. Starting Web Dashboard by default...
    docker compose up web
)

echo.
pause
