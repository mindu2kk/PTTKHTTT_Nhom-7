$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (Test-Path artifacts/web.pid) {
    $taskServerId=[int](Get-Content artifacts/web.pid)
    $taskProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$taskServerId" -ErrorAction SilentlyContinue
    if ($taskProcess) {
        if ($taskProcess.CommandLine -notlike '*node_modules/next/dist/bin/next*start*3000*') { throw 'PID no longer belongs to this task web server.' }
        Stop-Process -Id $taskServerId
    }
}
