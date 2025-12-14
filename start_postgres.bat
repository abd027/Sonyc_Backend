@echo off
echo ========================================
echo Starting PostgreSQL with Docker
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Desktop is not running!
    echo.
    echo Please:
    echo   1. Open Docker Desktop application
    echo   2. Wait for it to fully start
    echo   3. Run this script again
    echo.
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

echo Starting PostgreSQL container...
docker-compose up -d

if %errorlevel% neq 0 (
    echo [ERROR] Failed to start container
    pause
    exit /b 1
)

echo.
echo Waiting for PostgreSQL to be ready...
timeout /t 5 /nobreak >nul

echo.
echo Checking container status...
docker-compose ps

echo.
echo ========================================
echo PostgreSQL should now be running!
echo ========================================
echo.
echo To verify connection, run:
echo   python test_db_connection.py
echo.
pause








