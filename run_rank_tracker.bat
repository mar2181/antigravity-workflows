@echo off
:: run_rank_tracker.bat — fired by Task Scheduler "Antigravity-RankTracker-Daily" (06:30 AM daily)
:: Step 1: scrape Google SERP ranks for all 8 clients (keyword_rank_tracker.py).
:: Step 2: push the scraped state JSON into the Supabase keyword_rankings table
:: (push_rankings_to_supabase.py) so /api/rankings/keywords serves fresh data.
::
:: Runs at 06:30 AM so morning_brief.py (08:00) and the SEO optimizer (09:15)
:: both see today's snapshot.

set EXEC_DIR=C:\Users\mario\.gemini\antigravity\tools\execution
set LOG_DIR=%EXEC_DIR%\rank_logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

cd /d %EXEC_DIR%
set LOG_FILE=%LOG_DIR%\rank_tracker_%date:~10,4%%date:~4,2%%date:~7,2%.log

echo === Rank Tracker run started %date% %time% === >> "%LOG_FILE%"

python -u keyword_rank_tracker.py >> "%LOG_FILE%" 2>&1
set SCRAPE_EXIT=%ERRORLEVEL%
echo === keyword_rank_tracker.py exit=%SCRAPE_EXIT% at %time% === >> "%LOG_FILE%"

python -u push_rankings_to_supabase.py >> "%LOG_FILE%" 2>&1
set PUSH_EXIT=%ERRORLEVEL%
echo === push_rankings_to_supabase.py exit=%PUSH_EXIT% at %time% === >> "%LOG_FILE%"

echo === Rank Tracker run finished %date% %time% scrape=%SCRAPE_EXIT% push=%PUSH_EXIT% === >> "%LOG_FILE%"

if not "%SCRAPE_EXIT%"=="0" exit /b %SCRAPE_EXIT%
exit /b %PUSH_EXIT%
