@echo off
cd backend
call venv\Scripts\activate
start "GyanVriksh Workers" cmd /k python workers\run_workers.py --all
uvicorn app.main:app --reload --port 8000
