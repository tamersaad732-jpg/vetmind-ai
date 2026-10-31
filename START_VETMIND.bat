@echo off
title VetMind AI Enterprise Server
color 0A
echo =================================================================
echo         VetMind AI Enterprise - Official Server Runner
echo =================================================================
echo.

cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

echo [1/2] Checking Python Virtual Environment...
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found in venv folder!
    pause
    exit /b
)

echo [2/2] Launching VetMind AI on http://127.0.0.1:8000 ...
echo.
echo =================================================================
echo  * Server is now LIVE! Keep this black window open.
echo  * If you close this window, the server will stop.
echo  * To access VetMind AI: http://127.0.0.1:8000
echo =================================================================
echo.

start "" "http://127.0.0.1:8000"

venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
