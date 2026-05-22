@echo off
:: run_seo_optimizer_morning.bat — fired by Task Scheduler "Antigravity-SEO-Optimizer-Morning" (09:15 AM daily)
:: Phase 1 of the SEO optimizer autoresearch loop: analyze weak keywords -> generate actions -> execute via GBP.
:: Reads keyword_rankings_state.json (populated by the rank tracker cron at 06:30 AM).

set EXEC_DIR=C:\Users\mario\.gemini\antigravity\tools\execution
set LOG_DIR=%EXEC_DIR%\rank_logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

cd /d %EXEC_DIR%
set LOG_FILE=%LOG_DIR%\seo_optimizer_morning_%date:~10,4%%date:~4,2%%date:~7,2%.log

echo === SEO Optimizer Morning run started %date% %time% === >> "%LOG_FILE%"
python -u seo_optimizer\nightly_seo_optimizer.py --phase morning >> "%LOG_FILE%" 2>&1
set EXIT=%ERRORLEVEL%
echo === SEO Optimizer Morning run finished %date% %time% exit=%EXIT% === >> "%LOG_FILE%"

exit /b %EXIT%
