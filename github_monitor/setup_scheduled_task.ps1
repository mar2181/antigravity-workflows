# setup_scheduled_task.ps1
# Registers a Windows scheduled task that runs github_monitor.py daily at 9:00 AM.
#
# Must be run from an ELEVATED PowerShell (Run as Administrator):
#   powershell -NoProfile -ExecutionPolicy Bypass -File setup_scheduled_task.ps1

$ErrorActionPreference = "Stop"

$Python  = "python"
$Script  = "C:\Users\mario\.gemini\antigravity\tools\execution\github_monitor\github_monitor.py"
$WorkDir = "C:\Users\mario\.gemini\antigravity\tools\execution\github_monitor"
$Name    = "GitHubMonitor-Morning"

if (-not (Test-Path $Script)) { Write-Error "Script not found at $Script"; exit 1 }

$action    = New-ScheduledTaskAction -Execute $Python -Argument ('"' + $Script + '"') -WorkingDirectory $WorkDir
$trigger   = New-ScheduledTaskTrigger -Daily -At "9:00am"
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited

if (Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false
    Write-Host "Removed existing task: $Name"
}

Register-ScheduledTask -TaskName $Name -Description "Daily 9 AM GitHub PR/branch monitor for Mario's repos (Telegram alerts)" -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null

Write-Host "Registered: $Name (daily at 9:00 AM)"
Write-Host "Verify:      Get-ScheduledTask -TaskName $Name"
Write-Host "Trigger now: Start-ScheduledTask -TaskName $Name"
Write-Host "Last report: Get-Content $WorkDir\reports\latest.txt"
