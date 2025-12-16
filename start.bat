@echo off
echo Starting Website Authentication Component Detector...

REM Start backend
echo Starting backend server on port 8000...
cd backend
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt >nul 2>&1
start "Backend Server" cmd /k "python main.py"
cd ..

REM Start frontend
echo Starting frontend server on port 5173...
cd frontend
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
)
start "Frontend Server" cmd /k "npm run dev"
cd ..

echo.
echo Servers started!
echo    Backend:  http://localhost:8000
echo    Frontend: http://localhost:5173
echo.
echo Close the command windows to stop the servers.
pause

