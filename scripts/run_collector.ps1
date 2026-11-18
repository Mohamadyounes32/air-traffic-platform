Set-Location (Split-Path $PSScriptRoot -Parent)
. .\.venv\Scripts\Activate.ps1

while ($true) {
    python -m src.ingest.collect_opensky --interval 120
    if ($LASTEXITCODE -eq 2) {
        Start-Sleep -Seconds 3600    # credits exhausted or long rate limit: wait an hour
    } else {
        Start-Sleep -Seconds 60      # network or database problem: retry soon
    }
}