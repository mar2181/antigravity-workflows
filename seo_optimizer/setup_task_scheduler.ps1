# Windows Task Scheduler Setup for SEO Optimizer
# ==============================================
#
# Creates two automated tasks:
#   1. Morning Phase (12:00 AM) — Analyze, Generate, Execute
#   2. Evening Phase (6:30 AM) — Track, Report
#
# Usage: Run in PowerShell as Administrator
#   Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
#   .\setup_task_scheduler.ps1

$PythonPath = "python.exe"  # Assumes python.exe is in PATH
$ScriptDir = "C:/Users/mario/.gemini/antigravity/tools/execution/seo_optimizer"
$MasterScript = "$ScriptDir/nightly_seo_optimizer.py"

# Verify script exists
if (-not (Test-Path $MasterScript)) {
    Write-Host "❌ Script not found: $MasterScript"
    exit 1
}

Write-Host "🔧 Setting up Windows Task Scheduler for SEO Optimizer`n"

# ─── Task 1: Morning Phase (12:00 AM) ─────────────────────────────────────

$TaskName1 = "SEO-Optimizer-Morning"
$TaskDescription1 = "Identify weak keywords, generate actions, execute via GBP"
$TaskTime1 = "00:00"  # 12:00 AM

Write-Host "📋 Task 1: Morning Phase"
Write-Host "  Name: $TaskName1"
Write-Host "  Schedule: Daily at $TaskTime1"
Write-Host "  Action: Analyze → Generate → Execute`n"

# Check if task exists
$existingTask = Get-ScheduledTask -TaskName $TaskName1 -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "  Unregistering existing task..."
    Unregister-ScheduledTask -TaskName $TaskName1 -Confirm:$false
}

# Create action
$action1 = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "`"$MasterScript`" --phase morning" `
    -WorkingDirectory $ScriptDir

# Create trigger (daily at 12:00 AM)
$trigger1 = New-ScheduledTaskTrigger `
    -Daily `
    -At $TaskTime1

# Create settings
$settings1 = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Register task
Register-ScheduledTask `
    -TaskName $TaskName1 `
    -Action $action1 `
    -Trigger $trigger1 `
    -Settings $settings1 `
    -Description $TaskDescription1 `
    -User "SYSTEM" `
    -RunLevel Highest `
    -ErrorAction Stop | Out-Null

Write-Host "  ✅ Registered: $TaskName1`n"

# ─── Task 2: Evening Phase (6:30 AM) ───────────────────────────────────────

$TaskName2 = "SEO-Optimizer-Evening"
$TaskDescription2 = "Measure rank changes, generate reports, send Telegram"
$TaskTime2 = "06:30"  # 6:30 AM

Write-Host "📋 Task 2: Evening Phase"
Write-Host "  Name: $TaskName2"
Write-Host "  Schedule: Daily at $TaskTime2"
Write-Host "  Action: Track → Report`n"

# Check if task exists
$existingTask = Get-ScheduledTask -TaskName $TaskName2 -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "  Unregistering existing task..."
    Unregister-ScheduledTask -TaskName $TaskName2 -Confirm:$false
}

# Create action
$action2 = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "`"$MasterScript`" --phase evening" `
    -WorkingDirectory $ScriptDir

# Create trigger (daily at 6:30 AM)
$trigger2 = New-ScheduledTaskTrigger `
    -Daily `
    -At $TaskTime2

# Create settings
$settings2 = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Register task
Register-ScheduledTask `
    -TaskName $TaskName2 `
    -Action $action2 `
    -Trigger $trigger2 `
    -Settings $settings2 `
    -Description $TaskDescription2 `
    -User "SYSTEM" `
    -RunLevel Highest `
    -ErrorAction Stop | Out-Null

Write-Host "  ✅ Registered: $TaskName2`n"

# ─── Verify ───────────────────────────────────────────────────────────────

Write-Host "╔════════════════════════════════════════════════════════╗"
Write-Host "║                    ✅ SETUP COMPLETE                  ║"
Write-Host "╚════════════════════════════════════════════════════════╝`n"

Write-Host "Scheduled Tasks Created:`n"

$task1 = Get-ScheduledTask -TaskName $TaskName1
$task2 = Get-ScheduledTask -TaskName $TaskName2

Write-Host "  1. $TaskName1"
Write-Host "     State: $($task1.State)"
Write-Host "     Next Run: $($task1.Triggers[0].StartBoundary)`n"

Write-Host "  2. $TaskName2"
Write-Host "     State: $($task2.State)"
Write-Host "     Next Run: $($task2.Triggers[0].StartBoundary)`n"

Write-Host "To verify tasks in Windows Task Scheduler:`n"
Write-Host "  1. Open 'Task Scheduler'`n"
Write-Host "  2. Navigate to: Task Scheduler Library → Microsoft → Windows`n"
Write-Host "  3. Look for: SEO-Optimizer-Morning and SEO-Optimizer-Evening`n"

Write-Host "To manually run a task:`n"
Write-Host "  Start-ScheduledTask -TaskName 'SEO-Optimizer-Morning'`n"

Write-Host "To remove a task:`n"
Write-Host "  Unregister-ScheduledTask -TaskName 'SEO-Optimizer-Morning' -Confirm:`$false`n"

Write-Host "Next steps:`n"
Write-Host "  • Verify the tasks appear in Task Scheduler GUI`n"
Write-Host "  • Check logs in: C:/Users/mario/.gemini/antigravity/tools/execution/seo_optimizer_reports/`n"
Write-Host "  • Monitor Telegram for daily summaries`n"
