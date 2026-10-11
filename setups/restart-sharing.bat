@echo off
rem Restart Windows connection sharing for the Pi (needs admin; asks for it).
net session >nul 2>&1
if errorlevel 1 (
    powershell -NoProfile -Command "Start-Process -Verb RunAs -FilePath '%~f0'"
    exit /b
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0restart-sharing.ps1" %*
echo.
pause
