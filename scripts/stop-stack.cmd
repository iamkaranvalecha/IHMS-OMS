@echo off
REM Wrapper for stop-stack.ps1 (Windows cmd.exe / double-click)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-stack.ps1" %*
exit /b %ERRORLEVEL%
