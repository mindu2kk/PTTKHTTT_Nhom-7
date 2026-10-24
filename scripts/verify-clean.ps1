# A fresh isolated Compose project. It never deletes the normal hoodoomart volume.
param([string]$ReportPath = 'docs/evidence/clean-start.json')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$taskProject = 'hoodoomart-clean'
$taskExisting = docker compose -p $taskProject --env-file .env -f infra/docker-compose.yml ps -aq
if ($taskExisting) { throw 'Isolated verification project already exists. Inspect it before reusing.' }
$taskSavedPorts = @{}
$taskSavedProfile = $env:DATA_PROFILE
$taskUsedPorts = [System.Collections.Generic.HashSet[int]]::new()
function Get-TaskFreePort {
    do {
        $taskListener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
        $taskListener.Start()
        $taskPort = $taskListener.LocalEndpoint.Port
        $taskListener.Stop()
    } until ($taskUsedPorts.Add($taskPort))
    return [string]$taskPort
}
foreach ($taskPortName in @('POSTGRES_PORT','API_PORT','INFERENCE_PORT','WEB_PORT')) {
    $taskSavedPorts[$taskPortName] = [Environment]::GetEnvironmentVariable($taskPortName,'Process')
    [Environment]::SetEnvironmentVariable($taskPortName, (Get-TaskFreePort), 'Process')
}
try {
    # This harness checks the original course seed even when the main M8 catalog is real_demo.
    $env:DATA_PROFILE = 'demo_seed'
    docker compose -p $taskProject --env-file .env -f infra/docker-compose.yml up -d --build --wait
    if ($LASTEXITCODE -ne 0) { throw 'Clean startup failed.' }
    1..2 | ForEach-Object {
        docker compose -p $taskProject --env-file .env -f infra/docker-compose.yml exec -T api python -m app.infrastructure.seed
        if ($LASTEXITCODE -ne 0) { throw 'Seed failed.' }
    }
    1..2 | ForEach-Object {
        docker compose -p $taskProject --env-file .env -f infra/docker-compose.yml exec -T api python -m app.infrastructure.course_fixture
        if ($LASTEXITCODE -ne 0) { throw 'Course revision import failed.' }
    }
    $taskReady = Invoke-RestMethod "http://localhost:$env:API_PORT/health/ready"
    $taskProducts = Invoke-RestMethod "http://localhost:$env:API_PORT/api/v1/products"
    $taskCategories = Invoke-RestMethod "http://localhost:$env:API_PORT/api/v1/categories"
    if ($taskReady.status -ne 'ready' -or $taskProducts.total -ne 50 -or $taskCategories.Count -ne 49) {
        throw 'Clean startup catalog assertions failed.'
    }
    $taskOrigin="http://localhost:$env:WEB_PORT"
    $taskCsrf=Invoke-RestMethod "$taskOrigin/api/v1/auth/csrf" -SessionVariable taskCookies
    $taskHeaders=@{Origin=$taskOrigin;'X-CSRF-Token'=$taskCsrf.token}
    $taskRegistration=@{email=('clean-'+[guid]::NewGuid().ToString('N')+'@example.invalid');password=([guid]::NewGuid().ToString('N'))} | ConvertTo-Json
    $null=Invoke-RestMethod "$taskOrigin/api/v1/auth/register" -Method Post -WebSession $taskCookies -Headers $taskHeaders -ContentType 'application/json; charset=utf-8' -Body $taskRegistration
    $taskHeaders['X-CSRF-Token']=($taskCookies.Cookies.GetCookies([uri]$taskOrigin) | Where-Object Name -eq 'hm_csrf').Value
    $taskHeaders['Idempotency-Key']=[guid]::NewGuid().ToString('N')
    $taskCheckout=@{items=@(@{product_id='sweater-01';quantity=1;expected_price_vnd=264000});method='mock';address=@{recipient='Khách mô phỏng';phone='0900000000';address_line='Địa chỉ mô phỏng kiểm thử'}} | ConvertTo-Json -Depth 6
    $taskOrder=Invoke-RestMethod "$taskOrigin/api/v1/checkout" -Method Post -WebSession $taskCookies -Headers $taskHeaders -ContentType 'application/json; charset=utf-8' -Body $taskCheckout
    if ($taskOrder.total_vnd -ne 264000 -or $taskOrder.status -ne 'CONFIRMED') { throw 'Clean mock checkout failed.' }
    $null=Invoke-RestMethod "$taskOrigin/api/v1/orders/$($taskOrder.code)" -Method Patch -WebSession $taskCookies -Headers $taskHeaders -ContentType 'application/json; charset=utf-8' -Body '{"status":"CANCELLED"}'
    $taskReport = [ordered]@{
        measured_at = [DateTimeOffset]::UtcNow.ToString('o')
        project = $taskProject
        ready = $taskReady.status
        public_products = $taskProducts.total
        categories = $taskCategories.Count
        seed_runs = 2
        result = 'passed'
        profile = 'demo_seed'
        ports = @{postgres=$env:POSTGRES_PORT;api=$env:API_PORT;web=$env:WEB_PORT;inference=$env:INFERENCE_PORT}
        scope = 'Fresh isolated DB/API/web/inference, migrations, repeat seed/revision, real BFF CSRF registration/checkout/cancel'
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $ReportPath) -Force | Out-Null
    $taskReport | ConvertTo-Json | Set-Content -LiteralPath $ReportPath -Encoding utf8
    $taskReport | ConvertTo-Json
}
finally {
    # This project and its fresh volume were created only for the verification above.
    docker compose -p $taskProject --env-file .env -f infra/docker-compose.yml down --volumes
    foreach ($taskPortName in $taskSavedPorts.Keys) {
        [Environment]::SetEnvironmentVariable($taskPortName, $taskSavedPorts[$taskPortName], 'Process')
    }
    $env:DATA_PROFILE = $taskSavedProfile
}
