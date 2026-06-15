@echo off
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8010') do taskkill /PID %%a /F
