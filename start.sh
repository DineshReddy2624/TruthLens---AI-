#!/usr/bin/env bash
set -e

echo "======================================================================"
echo "                 TruthLens AI - Starting Application"
echo "======================================================================"
echo ""

if [ ! -f ".env" ]; then
    cp .env.example .env
fi

if [ ! -d "backend/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv backend/.venv
    source backend/.venv/bin/activate
    pip install -r requirements.txt
else
    source backend/.venv/bin/activate
fi

# Launch backend
echo "[1/2] Starting Backend Server (http://localhost:8000)..."
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Launch frontend
echo "[2/2] Starting Frontend UI (http://localhost:3000)..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "======================================================================"
echo "TruthLens AI is running!"
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo ""
echo "Log in with:"
echo "  - Standard User:  user@truthlens.ai  /  UserPass123!"
echo "  - Administrator:  admin@truthlens.ai /  AdminPass123!"
echo "Press Ctrl+C to stop both servers."
echo "======================================================================"

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
