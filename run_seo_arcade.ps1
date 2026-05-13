$env:CRON_MODE = '1'
$env:PYTHONIOENCODING = 'utf-8'
Get-Content 'C:\Users\mario\missioncontrol\dashboard\.env.local' | ForEach-Object {
    if ($_ -match '^([^#=][^=]*)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
    }
}
Set-Location 'C:\Users\mario\.gemini\antigravity\tools\execution'
& 'C:\Users\mario\AppData\Local\Programs\Python\Python310\python.exe' 'seo_optimizer/nightly_seo_optimizer.py' '--phase' 'morning' '--client' 'island_arcade' 2>&1 | Tee-Object -FilePath 'C:\Users\mario\.gemini\antigravity\tools\execution\seo_arcade_out.txt'
Write-Output "EXIT_CODE:$LASTEXITCODE" | Out-File -Append 'C:\Users\mario\.gemini\antigravity\tools\execution\seo_arcade_out.txt'
