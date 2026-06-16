$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

$preferredPython = @(
  (Join-Path $here ".venv\Scripts\python.exe"),
  "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
)

$pythonPath = $preferredPython | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$pythonArgs = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8010")

if (-not $pythonPath) {
  $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
  if ($pythonCmd) { $pythonPath = $pythonCmd.Source }
}

if (-not $pythonPath) {
  $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
  if ($pythonCmd) { $pythonPath = $pythonCmd.Source }
  $pythonArgs = @("-3") + $pythonArgs
}

if (-not $pythonPath) {
  Write-Host "Python was not found. Please install Python 3.11+ and add it to PATH."
  exit 1
}

Write-Host "Starting Crypto Options Strategy Assistant: http://127.0.0.1:8010"
& $pythonPath @pythonArgs
