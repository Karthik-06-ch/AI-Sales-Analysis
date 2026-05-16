@echo off
echo Starting Smart Sales Forecasting System...

start cmd /k "cd api && .\venv\Scripts\activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
start cmd /k "npm run dev"

echo Both frontend and backend servers have been started in separate windows.
echo Frontend: http://localhost:5173
echo Backend API: http://localhost:8000
