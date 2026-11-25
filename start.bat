@echo off
setlocal

echo ======================================================================
echo                 TruthLens AI - Starting Application
echo ======================================================================
echo.

:: Check for .env
if not exist ".env" (
    copy .env.example .env >nul
)

:: Start Backend in a new window
echo [1/2] Launching Backend Server on http://localhost:8000 ...
start "TruthLens Backend API" cmd /k "cd backend && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: Wait 3 seconds for backend initialization
timeout /t 3 /nobreak >nul

:: Start Frontend in a new window
echo [2/2] Launching Frontend UI on http://localhost:3000 ...
start "TruthLens Frontend" cmd /k "cd frontend && npm run dev"

:: Wait 2 seconds and open browser
timeout /t 2 /nobreak >nul
start http://localhost:3000

echo.
echo ======================================================================
echo TruthLens AI is running!
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000
echo.
echo Log in with:
echo   - Standard User:  user@truthlens.ai  /  UserPass123!
echo   - Administrator:  admin@truthlens.ai /  AdminPass123!
echo ======================================================================
