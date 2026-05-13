@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM  test_pipeline.bat — Full SEO + Mission Control pipeline manual test
REM
REM  Steps covered:
REM    1. Keyword rank scrape  (juan only, ~30s)
REM    2. Push rankings to Supabase
REM    3. SEO optimizer morning phase -- DRY RUN (no real GBP posts)
REM    4. All 5 Mission Control API endpoints (localhost:3001)
REM    5. Verify log files exist
REM
REM  To run headless Chrome test (simulate cron): set CRON_MODE=1 first
REM  To run a REAL post (not dry-run): edit Step 3 to remove --dry-run
REM ============================================================================

set "EXEC_DIR=C:\Users\mario\.gemini\antigravity\tools\execution"
cd /d "%EXEC_DIR%"

REM ── Load env vars ────────────────────────────────────────────────────────────
set "ENV_FILE=C:\Users\mario\missioncontrol\dashboard\.env.local"
if exist "%ENV_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
        set "k=%%a"
        set "v=%%b"
        if not "!k!"=="" if not "!k:~0,1!"=="#" if not "!v!"=="" (
            set "!k!=!v!"
        )
    )
    echo [ENV] Loaded credentials from .env.local
) else (
    echo [WARN] .env.local not found
)

set PYTHONIOENCODING=utf-8

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set TS=%%i
if "!TS!"=="" set TS=unknown-time
if not exist "cron_logs" mkdir "cron_logs"
set LOGFILE=cron_logs\test_pipeline_%TS%.log

set P1=SKIP
set P2=SKIP
set P3=SKIP
set P4=SKIP
set P5=SKIP

echo.
echo ============================================================================
echo   PIPELINE TEST -- %TS%
echo   Log: %LOGFILE%
echo ============================================================================
echo.

REM ── STEP 1: Keyword rank scrape ──────────────────────────────────────────────
echo [STEP 1/5] Keyword rank scrape -- client: juan
echo            scrapes SERPs for Juan Elizondo keywords, about 30 seconds
echo.
echo [STEP 1] keyword_rank_tracker.py --business juan > "%LOGFILE%" 2>&1

python keyword_rank_tracker.py --business juan >> "%LOGFILE%" 2>&1
set RC=%ERRORLEVEL%
echo [STEP 1 exit code: %RC%] >> "%LOGFILE%"
if %RC% EQU 0 (
    set P1=PASS
    echo   PASS -- rankings scraped
) else (
    set P1=FAIL
    echo   FAIL -- see %LOGFILE% for details
)
echo.

REM ── STEP 2: Push rankings to Supabase ────────────────────────────────────────
echo [STEP 2/5] Push rankings to Supabase
echo.
echo [STEP 2] push_rankings_to_supabase.py --business juan >> "%LOGFILE%" 2>&1

python push_rankings_to_supabase.py --business juan >> "%LOGFILE%" 2>&1
set RC=%ERRORLEVEL%
echo [STEP 2 exit code: %RC%] >> "%LOGFILE%"
if %RC% EQU 0 (
    set P2=PASS
    echo   PASS -- rankings pushed to Supabase
) else (
    set P2=FAIL
    echo   FAIL -- see %LOGFILE% for details
)
echo.

REM ── STEP 3: SEO optimizer morning phase DRY-RUN ──────────────────────────────
echo [STEP 3/5] SEO optimizer morning phase dry-run
echo            analyze, generate, execute preview -- no real GBP posts
echo.
echo [STEP 3] nightly_seo_optimizer.py --phase morning --dry-run >> "%LOGFILE%" 2>&1

python seo_optimizer\nightly_seo_optimizer.py --phase morning --dry-run >> "%LOGFILE%" 2>&1
set RC=%ERRORLEVEL%
echo [STEP 3 exit code: %RC%] >> "%LOGFILE%"
if %RC% EQU 0 (
    set P3=PASS
    echo   PASS -- optimizer dry-run completed
) else (
    set P3=FAIL
    echo   FAIL -- see %LOGFILE% for details
)
echo.

REM ── STEP 4: Mission Control API endpoints ────────────────────────────────────
echo [STEP 4/5] Mission Control API endpoints -- localhost:3001
echo.

if "!CRON_SECRET!"=="" (
    echo   SKIP -- CRON_SECRET not in env, start dashboard first
    set P4=SKIP
    goto :step5
)

set BASE=http://localhost:3001
set ALL_OK=1

for /f %%R in ('curl -s -o NUL -w "%%{http_code}" "%BASE%/api/cron/process-approvals" -H "Authorization: Bearer !CRON_SECRET!"') do set CODE=%%R
if "!CODE!"=="200" (echo   PASS process-approvals: 200) else (echo   FAIL process-approvals: !CODE! & set ALL_OK=0)
echo [API] process-approvals: !CODE! >> "%LOGFILE%"

for /f %%R in ('curl -s -o NUL -w "%%{http_code}" "%BASE%/api/cron/gsc-daily" -H "Authorization: Bearer !CRON_SECRET!"') do set CODE=%%R
if "!CODE!"=="200" (echo   PASS gsc-daily: 200) else (echo   FAIL gsc-daily: !CODE! & set ALL_OK=0)
echo [API] gsc-daily: !CODE! >> "%LOGFILE%"

for /f %%R in ('curl -s -o NUL -w "%%{http_code}" "%BASE%/api/cron/process-indexing" -H "Authorization: Bearer !CRON_SECRET!"') do set CODE=%%R
if "!CODE!"=="200" (echo   PASS process-indexing: 200) else (echo   FAIL process-indexing: !CODE! & set ALL_OK=0)
echo [API] process-indexing: !CODE! >> "%LOGFILE%"

for /f %%R in ('curl -s -o NUL -w "%%{http_code}" "%BASE%/api/cron/check-rankings?clients=juan" -H "Authorization: Bearer !CRON_SECRET!"') do set CODE=%%R
if "!CODE!"=="200" (echo   PASS check-rankings: 200) else (echo   FAIL check-rankings: !CODE! & set ALL_OK=0)
echo [API] check-rankings: !CODE! >> "%LOGFILE%"

for /f %%R in ('curl -s -o NUL -w "%%{http_code}" "%BASE%/api/cron/process-scheduled" -H "Authorization: Bearer !CRON_SECRET!"') do set CODE=%%R
if "!CODE!"=="200" (echo   PASS process-scheduled: 200) else (echo   FAIL process-scheduled: !CODE! & set ALL_OK=0)
echo [API] process-scheduled: !CODE! >> "%LOGFILE%"

if "!ALL_OK!"=="1" (set P4=PASS) else (set P4=FAIL)
echo.

:step5
REM ── STEP 5: Verify log files exist ───────────────────────────────────────────
echo [STEP 5/5] Verify cron_logs directory has log files
echo.
set LOGCOUNT=0
for %%F in ("cron_logs\*.log") do set /a LOGCOUNT+=1
if !LOGCOUNT! GTR 0 (
    set P5=PASS
    echo   PASS -- !LOGCOUNT! log files in cron_logs\
) else (
    set P5=FAIL
    echo   FAIL -- cron_logs\ is empty
)
echo.

REM ── SUMMARY ──────────────────────────────────────────────────────────────────
echo.
echo ============================================================================
echo   RESULTS SUMMARY
echo ============================================================================
echo   Step 1 -- Keyword rank scrape:       %P1%
echo   Step 2 -- Push rankings to Supabase: %P2%
echo   Step 3 -- SEO optimizer dry-run:     %P3%
echo   Step 4 -- API endpoints localhost:   %P4%
echo   Step 5 -- Log file creation:         %P5%
echo ============================================================================
echo   Full log: %LOGFILE%
echo ============================================================================
echo.
echo Tips:
echo   - Step 3 PASS = analyzer and generator work. Re-run without --dry-run to
echo     do real Playwright GBP posts.
echo   - Step 4 FAIL = dashboard not running on 3001. Run: npm run dev
echo   - Step 1 FAIL = check Bright Data credentials in .env.local
echo.
pause
