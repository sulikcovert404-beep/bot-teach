[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:8000",
    [int]$Attempts = 30,
    [int]$DelaySeconds = 2
)

$ErrorActionPreference = "Stop"

Write-Host "Applying database migrations..."
docker compose run --rm api alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    throw "Migration command failed with exit code $LASTEXITCODE"
}

Write-Host "Starting staging services..."
docker compose up -d db api
if ($LASTEXITCODE -ne 0) {
    throw "Compose startup failed with exit code $LASTEXITCODE"
}

$readyUrl = "$BaseUrl/health/ready"
for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
    try {
        $response = Invoke-RestMethod -Uri $readyUrl -Method Get
        if ($response.status -eq "ready") {
            Write-Host "Readiness passed at migration head $($response.migration_head)."
            exit 0
        }
    } catch {
        if ($attempt -eq $Attempts) {
            throw "Readiness check failed after $Attempts attempts: $($_.Exception.Message)"
        }
    }
    Start-Sleep -Seconds $DelaySeconds
}

throw "Readiness check did not pass."
