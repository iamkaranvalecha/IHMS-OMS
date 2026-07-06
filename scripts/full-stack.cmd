@echo off
REM Wrapper for full-stack.ps1 (Windows cmd.exe / double-click)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0full-stack.ps1" %*
exit /b %ERRORLEVEL%
