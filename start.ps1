$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
$pythonArgs = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8010")

if (-not $pythonCmd) {
  $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
  $pythonArgs = @("-3") + $pythonArgs
}

if (-not $pythonCmd) {
  Write-Host "Python was not found. Please install Python 3.11+ and add it to PATH."
  exit 1
}

Write-Host "Starting Crypto Options Strategy Assistant: http://127.0.0.1:8010"
& $pythonCmd.Source @pythonArgs
