$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$runScript = Join-Path $here "run_server.py"

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
$pythonArgs = "`"$runScript`""

if (-not $pythonCmd) {
  $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
  $pythonArgs = "-3 `"$runScript`""
}

if (-not $pythonCmd) {
  Write-Host "Python was not found. Please install Python 3.11+ and add it to PATH."
  exit 1
}

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $pythonCmd.Source
$psi.Arguments = $pythonArgs
$psi.WorkingDirectory = $here
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
[System.Diagnostics.Process]::Start($psi) | Out-Null

Write-Host "Assistant started in background: http://127.0.0.1:8010"
