@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM  Antigravity Digital — Morning SEO Pipeline
REM  Called by: Windows Task Scheduler "Antigravity Morning SEO" daily at 8:00 AM
REM  Chain: keyword_rank_tracker.py → push_rankings_to_supabase.py → SEO optimizer
REM  Created: 2026-05-01
REM ============================================================================

REM ── Working directory ────────────────────────────────────────────────────────
set "EXEC_DIR=C:\Users\mario\.gemini\antigravity\tools\execution"
cd /d "%EXEC_DIR%"
if %ERRORLEVEL% NEQ 0 (
    echo [FATAL] Could not cd to %EXEC_DIR%
    exit /b 1
)

REM ── Load env vars from .env.local ───────────────────────────────────────────
REM    Python sub-scripts (seo_action_generator.py, etc.) use os.environ.get()
REM    and do NOT load .env.local themselves, so we must populate the CMD env.
set "ENV_FILE=C:\Users\mario\missioncontrol\dashboard\.env.local"
if exist "%ENV_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
        set "k=%%a"
        set "v=%%b"
        REM Skip blank lines, comments, and lines without a value
        if not "!k!"=="" if not "!k:~0,1!"=="#" if not "!v!"=="" (
            REM Strip surrounding double-quotes if present
            if "!v:~0,1!"=="""" set "v=!v:~1!"
            if "!v:~-1!"=="""" set "v=!v:~0,-1!"
            set "!k!=!v!"
        )
    )
)

REM ── Mark as cron (non-interactive) so Python scripts run Chrome headless ────
set "CRON_MODE=1"
set "PYTHONIOENCODING=utf-8"

REM ── Logging setup ───────────────────────────────────────────────────────────
if not exist "cron_logs" mkdir "cron_logs"
REM  Use PowerShell for date — wmic is deprecated on Windows 11 and returns blank
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "LOGDATE=%%I"
if "!LOGDATE!"=="" set "LOGDATE=unknown-date"
set "LOGFILE=cron_logs\morning_seo_%LOGDATE%.log"

REM Default overall status (overwritten on success)
set "OVERALL=FAILURE"

echo =========================================================================== > "%LOGFILE%"
echo  Antigravity Morning SEO Pipeline                                       >> "%LOGFILE%"
echo  Date: %LOGDATE%  Time: %time%                                          >> "%LOGFILE%"
echo =========================================================================== >> "%LOGFILE%"

REM ══════════════════════════════════════════════════════════════════════════════
REM  STEP 1 — Keyword Rank Tracker (all 8 clients)
REM  Runs all businesses by default (no --all flag needed).
REM  On failure: FATAL exit (do NOT push stale data).
REM ══════════════════════════════════════════════════════════════════════════════
echo. >> "%LOGFILE%"
echo [STEP 1] keyword_rank_tracker.py — scraping SERPs for all clients...    >> "%LOGFILE%"
echo [%time%] Starting STEP 1...

python keyword_rank_tracker.py >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
if %RC% NEQ 0 (
    echo [FATAL] keyword_rank_tracker.py exited with code %RC%               >> "%LOGFILE%"
    echo [FATAL] Exiting — not pushing stale ranking data.                   >> "%LOGFILE%"
    goto :end
)
echo [OK] keyword_rank_tracker.py completed successfully                     >> "%LOGFILE%"

REM ══════════════════════════════════════════════════════════════════════════════
REM  STEP 2 — Push Rankings to Supabase
REM  Upserts fresh data into keyword_rankings table.
REM  On failure: WARNING but continue (local state is updated).
REM ══════════════════════════════════════════════════════════════════════════════
echo. >> "%LOGFILE%"
echo [STEP 2] push_rankings_to_supabase.py — upserting to Supabase...        >> "%LOGFILE%"
echo [%time%] Starting STEP 2...

python push_rankings_to_supabase.py >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
if %RC% NEQ 0 (
    echo [WARNING] push_rankings_to_supabase.py exited with code %RC%        >> "%LOGFILE%"
    echo [WARNING] Rankings updated locally — push failure is non-fatal.     >> "%LOGFILE%"
    set "OVERALL=PARTIAL FAILURE (step 2 warning)"
) else (
    echo [OK] push_rankings_to_supabase.py completed successfully            >> "%LOGFILE%"
)

REM ══════════════════════════════════════════════════════════════════════════════
REM  STEP 3 — SEO Optimizer (morning phase)
REM  Runs steps 1-3 of the autoresearch loop: analyze → generate → execute.
REM  On failure: WARNING but continue (rankings + DB already updated).
REM ══════════════════════════════════════════════════════════════════════════════
echo. >> "%LOGFILE%"
echo [STEP 3] nightly_seo_optimizer.py --phase morning...                    >> "%LOGFILE%"
echo [%time%] Starting STEP 3...

python seo_optimizer/nightly_seo_optimizer.py --phase morning >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
if %RC% NEQ 0 (
    echo [WARNING] SEO optimizer exited with code %RC%                       >> "%LOGFILE%"
    echo [WARNING] Rankings and DB updated — optimizer failure is non-fatal. >> "%LOGFILE%"
    if not "!OVERALL!"=="PARTIAL FAILURE (step 2 warning)" set "OVERALL=PARTIAL FAILURE (step 3 warning)"
) else (
    echo [OK] nightly_seo_optimizer.py completed successfully                >> "%LOGFILE%"
    if not "!OVERALL!"=="PARTIAL FAILURE (step 2 warning)" set "OVERALL=SUCCESS"
)

REM ══════════════════════════════════════════════════════════════════════════════
:end
echo. >> "%LOGFILE%"
echo =========================================================================== >> "%LOGFILE%"
echo  Pipeline complete: %OVERALL%                                           >> "%LOGFILE%"
echo  End Time: %time%                                                       >> "%LOGFILE%"
echo =========================================================================== >> "%LOGFILE%"

echo.
echo Morning SEO pipeline finished: %OVERALL%
exit /b 0
