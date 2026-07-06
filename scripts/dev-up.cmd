@echo off
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev-up.ps1" %*
exit /b %ERRORLEVEL%
