@echo off
setlocal
cd /d "%~dp0"
echo Starting Crypto Options Strategy Assistant...
echo Open http://127.0.0.1:8010 in your browser.
powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1"
