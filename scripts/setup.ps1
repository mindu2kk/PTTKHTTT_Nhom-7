$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
if (-not (Test-Path -LiteralPath '.env')) {
    $taskBytes = [byte[]]::new(24)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($taskBytes)
    $taskPassword = [Convert]::ToHexString($taskBytes).ToLowerInvariant()
    $taskEnv = (Get-Content -LiteralPath '.env.example' -Raw).Replace('replace_with_generated_local_password', $taskPassword)
    [System.IO.File]::WriteAllText((Join-Path $taskRoot '.env'), $taskEnv)
    Write-Output 'Created local .env with generated database password (not displayed).'
}
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { python -m venv .venv }
& '.\.venv\Scripts\python.exe' -m pip install -c apps/api/constraints.txt -e './apps/api[dev]' --quiet --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
Write-Output 'Local environment ready. See docs/RUNBOOK.md for start and test commands.'
