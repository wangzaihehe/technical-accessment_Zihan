#!/bin/bash

# Start Backend and Frontend servers

echo "Starting Website Authentication Component Detector..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed"
    exit 1
fi

# Start backend
echo "Starting backend server on port 8000..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1

python main.py &
BACKEND_PID=$!

cd ..

# Start frontend
echo "Starting frontend server on port 5173..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!

cd ..

echo ""
echo "✅ Servers started!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for user interrupt
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait

