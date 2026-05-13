Set-Location "C:\Users\mario\.gemini\antigravity\tools\execution"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path ".\claudeclaw.log" -Value "`n=== START $timestamp ==="
& "C:\Users\mario\AppData\Local\Programs\Python\Python310\python.exe" -m claudeclaw.run 2>&1 | Tee-Object -FilePath ".\claudeclaw.log" -Append
