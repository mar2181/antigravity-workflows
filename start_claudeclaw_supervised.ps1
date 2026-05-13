# Supervised War Room launcher — keeps `python -m claudeclaw.run` alive.
#
# Restart-on-crash with backoff. Logs every start / crash / restart so you
# can see in claudeclaw.log when (and why) the process died.
#
# Designed to be run from Windows Task Scheduler "At Logon" by setup_war_room_task.ps1.
# Run manually for a single foreground supervised session:
#   powershell -NoProfile -ExecutionPolicy Bypass -File start_claudeclaw_supervised.ps1

$ErrorActionPreference = "Continue"

Set-Location "C:\Users\mario\.gemini\antigravity\tools\execution"

$python = "C:\Users\mario\AppData\Local\Programs\Python\Python310\python.exe"
$logPath = ".\claudeclaw.log"
$minRunSeconds = 30      # if process dies before this, treat as a fast-crash → longer backoff
$backoffSeconds = 3      # initial restart delay after a normal exit
$fastCrashBackoff = 30   # restart delay after a fast crash
$maxBackoff = 300        # cap on backoff growth

$consecutiveFastCrashes = 0
$currentBackoff = $backoffSeconds

function Write-WarLog {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [supervisor] $Message"
    Add-Content -Path $logPath -Value $line
    Write-Host $line
}

Write-WarLog "Supervisor started — pid $PID"

while ($true) {
    $startedAt = Get-Date
    Write-WarLog "Launching: $python -m claudeclaw.run"
    try {
        & $python -m claudeclaw.run 2>&1 | Tee-Object -FilePath $logPath -Append
        $exitCode = $LASTEXITCODE
    } catch {
        $exitCode = -1
        Write-WarLog "Launch threw: $_"
    }
    $runSeconds = ((Get-Date) - $startedAt).TotalSeconds
    Write-WarLog "claudeclaw exited (code=$exitCode) after $([int]$runSeconds)s"

    if ($runSeconds -lt $minRunSeconds) {
        $consecutiveFastCrashes++
        $currentBackoff = [Math]::Min($maxBackoff, $fastCrashBackoff * [Math]::Pow(2, [Math]::Min($consecutiveFastCrashes - 1, 4)))
        Write-WarLog "Fast crash (#$consecutiveFastCrashes). Sleeping $currentBackoff s before restart."
    } else {
        $consecutiveFastCrashes = 0
        $currentBackoff = $backoffSeconds
        Write-WarLog "Normal exit. Sleeping $currentBackoff s before restart."
    }
    Start-Sleep -Seconds $currentBackoff
}
