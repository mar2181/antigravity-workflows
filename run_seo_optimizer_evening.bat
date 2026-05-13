@echo off
setlocal enabledelayedexpansion
:: run_seo_optimizer_evening.bat
:: Called by Windows Task Scheduler "Antigravity-SEO-Optimizer-Evening" at 6:30 PM
:: Runs Steps 4-5: track ranking deltas → generate reports + Telegram notification

set WORKSPACE_DIR=C:\Users\mario\.gemini\antigravity\tools\execution
cd /d %WORKSPACE_DIR%
if %ERRORLEVEL% NEQ 0 (
    echo [FATAL] Could not cd to %WORKSPACE_DIR%
    exit /b 1
)

:: Mark as cron so Python scripts run Chrome headless (no display in Task Scheduler)
set CRON_MODE=1
set PYTHONIOENCODING=utf-8

:: Load env vars from .env.local so sub-scripts get Supabase/Anthropic credentials
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

:: Date-stamped log
if not exist "cron_logs" mkdir "cron_logs"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set LOG_DATE=%%i
if "!LOG_DATE!"=="" set LOG_DATE=unknown-date
set LOG_FILE=cron_logs\seo_optimizer_evening_%LOG_DATE%.log

echo =========================================================================== >  "%LOG_FILE%"
echo  SEO Optimizer — Evening Phase (Steps 4-5)                               >> "%LOG_FILE%"
echo  Date: %LOG_DATE%  Time: %time%                                          >> "%LOG_FILE%"
echo  CRON_MODE=1 (headless Chrome)                                           >> "%LOG_FILE%"
echo =========================================================================== >> "%LOG_FILE%"

echo [%date% %time%] SEO Optimizer Evening Phase START >> "%LOG_FILE%"
python seo_optimizer\nightly_seo_optimizer.py --phase evening >> "%LOG_FILE%" 2>&1
set RC=%ERRORLEVEL%
echo [%date% %time%] SEO Optimizer Evening Phase END (exit code: %RC%) >> "%LOG_FILE%"

exit /b %RC%
