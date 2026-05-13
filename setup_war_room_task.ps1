# Registers a Windows Task Scheduler entry that supervises the War Room
# (claudeclaw) at user logon, with built-in restart-on-failure.
#
# RUN ONCE, as Administrator:
#   powershell -NoProfile -ExecutionPolicy Bypass -File setup_war_room_task.ps1
#
# To remove the task later:
#   Unregister-ScheduledTask -TaskName "WarRoom-AtLogon" -Confirm:$false

$taskName = "WarRoom-AtLogon"
$scriptPath = "C:\Users\mario\.gemini\antigravity\tools\execution\start_claudeclaw_supervised.ps1"

if (-not (Test-Path $scriptPath)) {
    Write-Host "ERROR: $scriptPath not found." -ForegroundColor Red
    exit 1
}

# Unregister any prior version so this script is idempotent.
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing existing task $taskName ..."
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 0)  # 0 = no time limit

# Run interactively as the current user — needed so the Python process inherits
# the user's environment (PATH, %APPDATA%, OneDrive paths, etc.) the way the
# manual `start_claudeclaw.ps1` does.
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Supervises the claudeclaw War Room (127.0.0.1:8787) at logon. Restart-on-crash via start_claudeclaw_supervised.ps1." | Out-Null

Write-Host "Registered Task Scheduler entry: $taskName" -ForegroundColor Green
Write-Host "It will start the War Room supervisor at next logon."
Write-Host ""
Write-Host "To start the supervisor immediately without rebooting:"
Write-Host "  Start-ScheduledTask -TaskName $taskName"
Write-Host ""
Write-Host "To verify it's running afterward:"
Write-Host "  Get-ScheduledTask -TaskName $taskName | Get-ScheduledTaskInfo"
Write-Host "  curl http://127.0.0.1:8787/health"
