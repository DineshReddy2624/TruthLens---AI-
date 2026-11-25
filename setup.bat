@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo           TruthLens AI - Automated Setup and Dependency Installer
echo ======================================================================
echo.

:: 1. Copy .env if not exists
if not exist ".env" (
    echo [1/4] Creating .env file from .env.example...
    copy .env.example .env >nul
) else (
    echo [1/4] .env already exists.
)

:: 2. Setup Python virtual environment
echo.
echo [2/4] Setting up Python virtual environment...
if not exist "backend\.venv" (
    python -m venv backend\.venv
)

:: 3. Install Python dependencies from requirements.txt
echo.
echo [3/4] Installing all Python dependencies from requirements.txt...
call backend\.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

:: 4. Install Frontend dependencies
echo.
echo [4/4] Installing Frontend dependencies (npm install)...
cd frontend
call npm install
cd ..

echo.
echo ======================================================================
echo        Setup Complete! Everything is ready without data loss.
echo        To start TruthLens AI, double-click: start.bat
echo ======================================================================
echo.
pause
