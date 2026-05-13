@echo off
setlocal enabledelayedexpansion
cd /d "C:\Users\mario\.gemini\antigravity\tools\execution"
set CRON_MODE=1
set PYTHONIOENCODING=utf-8
set "ENV_FILE=C:\Users\mario\missioncontrol\dashboard\.env.local"
if exist "%ENV_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
        set "k=%%a"
        set "v=%%b"
        if not "!k!"=="" if not "!k:~0,1!"=="#" if not "!v!"=="" (
            set "!k!=!v!"
        )
    )
)
"C:\Users\mario\AppData\Local\Programs\Python\Python310\python.exe" keyword_rank_tracker.py --business %1 > "%2" 2>&1
echo EXIT_CODE:%ERRORLEVEL% >> "%2"
