@echo off
:: run_seo_optimizer_evening.bat — fired by Task Scheduler "Antigravity-SEO-Optimizer-Evening" (18:30 daily)
:: Phase 2: measure rank deltas vs. morning baseline, generate report, Telegram notify.

set EXEC_DIR=C:\Users\mario\.gemini\antigravity\tools\execution
set LOG_DIR=%EXEC_DIR%\rank_logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

cd /d %EXEC_DIR%
set LOG_FILE=%LOG_DIR%\seo_optimizer_evening_%date:~10,4%%date:~4,2%%date:~7,2%.log

echo === SEO Optimizer Evening run started %date% %time% === >> "%LOG_FILE%"
python -u seo_optimizer\nightly_seo_optimizer.py --phase evening >> "%LOG_FILE%" 2>&1
set EXIT=%ERRORLEVEL%
echo === SEO Optimizer Evening run finished %date% %time% exit=%EXIT% === >> "%LOG_FILE%"

exit /b %EXIT%
