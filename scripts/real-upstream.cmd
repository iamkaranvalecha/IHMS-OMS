@echo off
REM Wrapper for real-upstream.ps1 (Windows cmd.exe / double-click)
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0real-upstream.ps1" %*
exit /b %ERRORLEVEL%
