[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:8000",
    [int]$Attempts = 30,
    [int]$DelaySeconds = 2,
    [string]$ExpectedMigrationHead = $(if ($env:EXPECTED_MIGRATION_HEAD) { $env:EXPECTED_MIGRATION_HEAD } else { "20260909_0015" })
)

$ErrorActionPreference = "Stop"

Write-Host "Starting staging services..."
docker compose up -d db migrate api
if ($LASTEXITCODE -ne 0) {
    throw "Compose startup failed with exit code $LASTEXITCODE"
}

$readyUrl = "$BaseUrl/health/ready"
for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
    try {
        # Use curl.exe for the local readiness probe because Windows PowerShell's
        # HttpClient can inherit a proxy and hang on localhost even when the API
        # is healthy. Keep the request bounded and parse only the JSON contract.
        $rawResponse = curl.exe --silent --show-error --max-time 10 $readyUrl
        if ($LASTEXITCODE -ne 0) {
            throw "Readiness request failed with curl exit code $LASTEXITCODE"
        }
        $response = $rawResponse | ConvertFrom-Json
        if ($response.status -eq "ready" -and $response.migration_head -eq $ExpectedMigrationHead) {
            Write-Host "Readiness passed at migration head $($response.migration_head)."
            exit 0
        }
        if ($response.status -eq "ready") {
            throw "Unexpected migration head: $($response.migration_head); expected $ExpectedMigrationHead"
        }
    } catch {
        if ($attempt -eq $Attempts) {
            throw "Readiness check failed after $Attempts attempts: $($_.Exception.Message)"
        }
    }
    Start-Sleep -Seconds $DelaySeconds
}

throw "Readiness check did not pass."
