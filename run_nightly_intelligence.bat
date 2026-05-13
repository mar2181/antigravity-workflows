@echo off
:: run_nightly_intelligence.bat — fired by Task Scheduler "Antigravity-NightlyIntelligence" (02:00 AM daily)
:: Chains the competitor intelligence pipeline: GBP monitor + FB Ad Library + AI analyzer
:: + morning brief synthesis (review miner skipped unless --with-reviews is passed in here).

set EXEC_DIR=C:\Users\mario\.gemini\antigravity\tools\execution
set LOG_DIR=%EXEC_DIR%\rank_logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

cd /d %EXEC_DIR%
set LOG_FILE=%LOG_DIR%\nightly_intelligence_%date:~10,4%%date:~4,2%%date:~7,2%.log

echo === Nightly Intelligence run started %date% %time% === >> "%LOG_FILE%"
python -u nightly_intelligence.py >> "%LOG_FILE%" 2>&1
set EXIT=%ERRORLEVEL%
echo === Nightly Intelligence run finished %date% %time% exit=%EXIT% === >> "%LOG_FILE%"

exit /b %EXIT%
