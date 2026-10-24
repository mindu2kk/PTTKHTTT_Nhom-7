# Run the existing guarded 3k corpus benchmark against actual Docker HTTP, not ASGI.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$taskExisting = docker ps -aq --filter 'name=^/hoodoomart-benchmark-api$'
if ($taskExisting) { throw 'Benchmark container already exists; inspect it before reuse.' }
$taskOldDb = $env:POSTGRES_DB
$taskOldTarget = $env:BENCHMARK_API_URL
$taskOldProfile = $env:DATA_PROFILE
$taskCreated = $false
try {
    $taskDb = & .\.venv\Scripts\python.exe -c "from dotenv import dotenv_values; from sqlalchemy.engine import make_url; print(make_url(dotenv_values('.env')['TEST_DATABASE_URL']).database)"
    if ($LASTEXITCODE -ne 0 -or $taskDb -ne 'hoodoomart_test') { throw 'Requires the separate hoodoomart_test database.' }
    $env:POSTGRES_DB = $taskDb
    $env:DATA_PROFILE = 'demo_seed'
    $env:BENCHMARK_API_URL = 'http://127.0.0.1:8002'
    $null = docker compose --env-file .env -f infra/docker-compose.yml run --rm -d --no-deps --name hoodoomart-benchmark-api -p 127.0.0.1:8002:8000 api
    if ($LASTEXITCODE -ne 0) { throw 'Isolated API start failed.' }
    $taskCreated = $true
    $taskReady = $false
    foreach ($taskAttempt in 1..30) {
        try {
            $taskHealth = Invoke-RestMethod 'http://127.0.0.1:8002/health/ready' -TimeoutSec 2
            if ($taskHealth.status -eq 'ready') { $taskReady = $true; break }
        } catch { }
        Start-Sleep -Seconds 1
    }
    if (-not $taskReady) { throw 'Benchmark API did not become ready.' }
    & .\.venv\Scripts\python.exe benchmarks/scripts/scale_eval.py
    if ($LASTEXITCODE -ne 0) { throw 'Real HTTP scale benchmark failed.' }
}
finally {
    if ($taskCreated) { $null = docker stop hoodoomart-benchmark-api }
    $env:POSTGRES_DB = $taskOldDb
    $env:BENCHMARK_API_URL = $taskOldTarget
    $env:DATA_PROFILE = $taskOldProfile
}
