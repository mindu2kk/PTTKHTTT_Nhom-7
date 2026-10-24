$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$taskNode='C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
if (-not(Test-Path $taskNode)) { $taskNode=(Get-Command node).Source }
$taskServer=Start-Process -FilePath $taskNode -ArgumentList @('node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3000') -WorkingDirectory (Join-Path $taskRoot 'apps/web') -RedirectStandardOutput (Join-Path $taskRoot 'artifacts/web.stdout.log') -RedirectStandardError (Join-Path $taskRoot 'artifacts/web.stderr.log') -WindowStyle Hidden -PassThru
$taskServer.Id | Set-Content artifacts/web.pid
Write-Output 'HoodooMart frontend starting at http://localhost:3000'
