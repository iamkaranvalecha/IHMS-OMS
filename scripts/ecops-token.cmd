@echo off
REM Wrapper for ecops-token.ps1 (Windows cmd.exe / double-click)
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0ecops-token.ps1" %*
exit /b %ERRORLEVEL%
