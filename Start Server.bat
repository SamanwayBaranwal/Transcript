@echo off
title ReelScript Server
echo ============================================
echo   ReelScript - starting local server
echo   Keep this window OPEN while you use the app
echo ============================================
echo.

REM Set your free Groq key here (from https://console.groq.com/keys)
REM Replace the line below with your real key, e.g. set "GROQ_API_KEY=gsk_abc123..."
if "%GROQ_API_KEY%"=="" set "GROQ_API_KEY="
if "%GROQ_API_KEY%"=="" echo [!] No GROQ_API_KEY set - transcription will fail until you add your gsk_ key.

REM open the app in your browser
start "" http://localhost:5050

"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%~dp0server.py"
pause
