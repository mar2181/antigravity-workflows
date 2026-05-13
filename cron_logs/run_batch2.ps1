Set-Location "C:\Users\mario\.gemini\antigravity\tools\execution"
$envFile = "C:\Users\mario\missioncontrol\dashboard\.env.local"
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^([^#=][^=]*)=(.+)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}
$env:CRON_MODE = "1"
$env:PYTHONIOENCODING = "utf-8"

function Run-Step {
    param($label, $script_args)
    $ts = Get-Date -Format "HH:mm:ss"
    Add-Content -Path "C:\Users\mario\.gemini\antigravity\tools\execution\cron_logs\batch2_pipeline.log" -Value "[$ts] START: $label"
    $out = & python @script_args 2>&1
    $rc = $LASTEXITCODE
    $ts2 = Get-Date -Format "HH:mm:ss"
    $outStr = ($out -join "`n")
    if ($outStr.Length -gt 2000) { $outStr = $outStr.Substring($outStr.Length - 2000) }
    Add-Content -Path "C:\Users\mario\.gemini\antigravity\tools\execution\cron_logs\batch2_pipeline.log" -Value "[$ts2] END: $label | exit=$rc"
    Add-Content -Path "C:\Users\mario\.gemini\antigravity\tools\execution\cron_logs\batch2_pipeline.log" -Value "OUTPUT: $outStr"
    Add-Content -Path "C:\Users\mario\.gemini\antigravity\tools\execution\cron_logs\batch2_pipeline.log" -Value "---"
    return $rc
}

# CLIENT 1: spi_fun_rentals
Run-Step "spi_fun_rentals/rank-check" @("keyword_rank_tracker.py", "--business", "spi_fun_rentals")
Run-Step "spi_fun_rentals/push-rankings" @("push_rankings_to_supabase.py", "--business", "spi_fun_rentals")
Run-Step "spi_fun_rentals/seo-optimize" @("seo_optimizer\nightly_seo_optimizer.py", "--phase", "morning", "--client", "spi_fun_rentals")

# CLIENT 2: sugar_shack
Run-Step "sugar_shack/rank-check" @("keyword_rank_tracker.py", "--business", "sugar_shack")
Run-Step "sugar_shack/push-rankings" @("push_rankings_to_supabase.py", "--business", "sugar_shack")
Run-Step "sugar_shack/seo-optimize" @("seo_optimizer\nightly_seo_optimizer.py", "--phase", "morning", "--client", "sugar_shack")

Add-Content -Path "C:\Users\mario\.gemini\antigravity\tools\execution\cron_logs\batch2_pipeline.log" -Value "[$(Get-Date -Format 'HH:mm:ss')] ALL DONE"
