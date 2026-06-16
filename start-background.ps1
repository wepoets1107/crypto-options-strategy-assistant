$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$runScript = Join-Path $here "run_server.py"

$preferredPython = @(
  (Join-Path $here ".venv\Scripts\python.exe"),
  "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
)

$pythonPath = $preferredPython | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$pythonArgs = "`"$runScript`""

if (-not $pythonPath) {
  $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
  if ($pythonCmd) { $pythonPath = $pythonCmd.Source }
}

if (-not $pythonPath) {
  $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
  if ($pythonCmd) { $pythonPath = $pythonCmd.Source }
  $pythonArgs = "-3 `"$runScript`""
}

if (-not $pythonPath) {
  Write-Host "Python was not found. Please install Python 3.11+ and add it to PATH."
  exit 1
}

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $pythonPath
$psi.Arguments = $pythonArgs
$psi.WorkingDirectory = $here
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
[System.Diagnostics.Process]::Start($psi) | Out-Null

Write-Host "Assistant started in background: http://127.0.0.1:8010"
