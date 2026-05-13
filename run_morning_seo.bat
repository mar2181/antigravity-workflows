@echo off
:: run_morning_seo.bat — fired by Task Scheduler "Antigravity Morning SEO" (08:00 AM daily)
:: Generates the morning brief HTML synthesizing overnight competitor intel + rank state.
:: Mario opens this before any posting session.

set EXEC_DIR=C:\Users\mario\.gemini\antigravity\tools\execution
set LOG_DIR=%EXEC_DIR%\rank_logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

cd /d %EXEC_DIR%
set LOG_FILE=%LOG_DIR%\morning_seo_%date:~10,4%%date:~4,2%%date:~7,2%.log

echo === Morning SEO run started %date% %time% === >> "%LOG_FILE%"
python -u morning_brief.py >> "%LOG_FILE%" 2>&1
set EXIT=%ERRORLEVEL%
echo === Morning SEO run finished %date% %time% exit=%EXIT% === >> "%LOG_FILE%"

exit /b %EXIT%
