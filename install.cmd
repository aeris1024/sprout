@echo off
rem Double-click to install Sprout. Runs scripts\install.ps1 regardless of the
rem PowerShell execution policy and passes options through (install.cmd -CliOnly).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install.ps1" %*
set code=%ERRORLEVEL%
pause
exit /b %code%
