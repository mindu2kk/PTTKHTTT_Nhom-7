$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$taskPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
function Invoke-TaskCheck([string[]]$TaskArguments) {
    & $taskPython @TaskArguments
    if ($LASTEXITCODE -ne 0) { throw ('Check failed: ' + ($TaskArguments -join ' ')) }
}
Invoke-TaskCheck @('-m', 'ruff', 'check', 'apps/api', 'apps/inference', 'scripts', 'data_pipeline', 'benchmarks/scripts')
Invoke-TaskCheck @('-m', 'ruff', 'format', '--check', 'apps/api', 'apps/inference', 'scripts', 'data_pipeline', 'benchmarks/scripts')
Invoke-TaskCheck @('-m', 'mypy', '--config-file', 'apps/api/pyproject.toml', 'apps/api/app')
Invoke-TaskCheck @('-m', 'pytest', 'apps/api/unit_tests', '-q')
Invoke-TaskCheck @('-m', 'alembic', '-c', 'apps/api/alembic.ini', 'check')
Invoke-TaskCheck @('scripts/create_test_db.py')
Invoke-TaskCheck @('-m', 'pytest', 'apps/api/tests', '-q', '--junitxml=docs/evidence/pytest.xml')
